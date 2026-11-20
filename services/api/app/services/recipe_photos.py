"""A Member's own photo on their Imported Recipes (ADR 0031).

Cleaned (upright, 4:3, two fresh WebP files, no metadata), kept behind `PhotoStore` (a
folder in development, S3 in slice 11), and shown through short-lived signed links, so
the photo route needs no sign-in header and works in a plain <img>.
"""

import hashlib
import hmac
import io
import secrets
import time
import uuid
from pathlib import Path
from typing import Protocol

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings
from app.errors import InvalidInput

SIZES = {"hero": 960, "thumb": 360}
QUALITY = 70
MAX_PIXELS = 40_000_000  # a 5 MB file that decodes to more is a trick, not a photo
LINK_HOURS = 1


def clean(data: bytes) -> dict[str, bytes]:
    """The photo as new 4:3 WebP files, one per size. Only pixels are copied, so GPS and
    camera details don't survive."""
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > MAX_PIXELS:
                raise InvalidInput("That photo is too large. Try a smaller copy.")
            upright = ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise InvalidInput("That file couldn't be read as a photo.") from error
    files = {}
    for size, width in SIZES.items():
        out = io.BytesIO()
        cropped = ImageOps.fit(upright, (width, width * 3 // 4), Image.Resampling.LANCZOS)
        cropped.save(out, "WEBP", quality=QUALITY)
        files[size] = out.getvalue()
    return files


# --- storage -----------------------------------------------------------------------------


class PhotoStore(Protocol):
    def put(self, key: str, data: bytes) -> None: ...
    def get(self, key: str) -> bytes | None: ...
    def delete_prefix(self, prefix: str) -> None: ...


class FolderStore:
    """Development: files under one folder. A hosted server's disk isn't kept, so
    production needs S3 (slice 11) behind the same three methods."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError(f"bad photo key {key!r}")
        return path

    def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes | None:
        path = self._path(key)
        return path.read_bytes() if path.is_file() else None

    def delete_prefix(self, prefix: str) -> None:
        folder = self._path(prefix)
        if folder.is_dir():
            for path in sorted(folder.rglob("*"), reverse=True):  # files, then folders
                path.unlink() if path.is_file() else path.rmdir()
            folder.rmdir()


def folder(household_id: uuid.UUID, recipe_id: uuid.UUID | None = None) -> str:
    return f"{household_id}/{recipe_id}" if recipe_id else str(household_id)


def key(household_id: uuid.UUID, recipe_id: uuid.UUID, photo_id: str, size: str) -> str:
    return f"{folder(household_id, recipe_id)}/{photo_id}/{size}.webp"


def save(
    store: PhotoStore, household_id: uuid.UUID, recipe_id: uuid.UUID, data: bytes
) -> dict[str, str]:
    """Clean and store a photo; returns what `recipes.image` holds."""
    files = clean(data)
    photo_id = secrets.token_hex(8)
    for size, webp in files.items():
        store.put(key(household_id, recipe_id, photo_id, size), webp)
    return {
        "source": "member",
        "household_id": str(household_id),
        "recipe_id": str(recipe_id),
        "photo_id": photo_id,
    }


def forget(store: PhotoStore, stored: dict[str, str] | None) -> None:
    """Delete a stored Member photo's files (nothing for a stock photo or none)."""
    if stored and stored.get("source") == "member":
        store.delete_prefix(
            f"{folder(uuid.UUID(stored['household_id']), uuid.UUID(stored['recipe_id']))}"
            f"/{stored['photo_id']}"
        )


# --- signed links ------------------------------------------------------------------------

_KEY = (
    settings.photo_signing_key.get_secret_value().encode()
    if settings.photo_signing_key
    else secrets.token_bytes(32)
)


def _signature(path: str, expires: int) -> str:
    return hmac.new(_KEY, f"{path}:{expires}".encode(), hashlib.sha256).hexdigest()


def sign(path: str, now: float | None = None) -> tuple[int, str]:
    """An expiry one to two hours away, the same all hour (so caches keep the link)."""
    hour = int(now if now is not None else time.time()) // 3600
    expires = (hour + LINK_HOURS + 1) * 3600
    return expires, _signature(path, expires)


def valid(path: str, expires: int, sig: str, now: float | None = None) -> bool:
    current = now if now is not None else time.time()
    return current <= expires and hmac.compare_digest(sig, _signature(path, expires))


def links(stored: dict[str, str]) -> dict[str, str]:
    """The thumb and hero links for a stored Member photo, relative to the API."""
    out = {}
    for size in SIZES:
        path = f"{stored['household_id']}/{stored['recipe_id']}/{stored['photo_id']}/{size}"
        expires, sig = sign(path)
        out[f"{size}_url"] = f"/recipe-photos/{path}.webp?expires={expires}&sig={sig}"
    return out
