"""Find, check and write Recipe Images for the Seed Recipes (slice 4f, ADR 0027).

    uv run python -m scripts.recipe_images search            # free; resumable
    uv run python -m scripts.recipe_images check --max-spend 6   # COSTS MONEY (Haiku)
    uv run python -m scripts.recipe_images write             # free: WebP files + credits

search: Wikimedia Commons, then Openverse (200 searches a day without a key, so a
second day's run carries on), keeping only open licences and photos big enough for a
4:3 hero. check: Haiku looks at each recipe's candidates in order until one passes,
skipping any photo another recipe already has. write: crops, resizes and saves the
chosen photos, minus any the product owner rejected on the contact sheet.
"""

import argparse
import asyncio
import html
import io
import json
import re
import sys
import time
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from PIL import Image
from pydantic import BaseModel

from app.config import settings
from app.data.recipe_images import FILES, RECORDS, SIZES, RecipeImage, file_name
from app.data.recipes import SeedRecipe, load_seed_recipes
from app.llm_costs import cost_usd
from app.services.recipe_image_check import ClaudeImageChecker, passes, title_clash
from app.services.recipe_import import Photo, photo_type

WORK = Path(__file__).parents[1] / "data" / "recipe-images"
CANDIDATES = WORK / "candidates.json"
CHECKS = WORK / "checks.json"
REJECTED = WORK / "rejected.json"  # source URLs the product owner turned down
CACHE = WORK / "cache"  # downloads, git-ignored
# Wikimedia wants a link in the User-Agent; a generic one, with no personal details.
AGENT = {"User-Agent": "SweepRecipeImages/0.1 (+https://www.mediawiki.org/wiki/API:Etiquette)"}
MOST = 8  # candidates per recipe
HERO_W, HERO_H = 960, 720
KEEP = 0.6  # a 4:3 crop must keep this much of the photo


class Candidate(BaseModel):
    source: str  # "wikimedia" or "openverse"
    download_url: str
    source_url: str
    title: str
    author: str
    licence: str
    licence_url: str | None
    width: int
    height: int


# --- Rules (tested) -------------------------------------------------------------------

_CC = re.compile(r"^cc (by|by sa) (\d\.\d)(?: ([a-z]{2}))?$")
LICENCE_URLS = {
    "CC0 1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "Public Domain": "https://creativecommons.org/publicdomain/mark/1.0/",
}


def licence_name(given: str) -> str | None:
    """CC0, Public Domain, CC BY or CC BY-SA with a version, in one spelling; else None."""
    s = " ".join(given.lower().replace("-", " ").replace("_", " ").split())
    if s in ("cc0", "cc0 1.0", "cc zero"):
        return "CC0 1.0"
    if s in ("public domain", "pd", "pdm", "public domain mark", "no restrictions"):
        return "Public Domain"
    if match := _CC.match(s):
        kind = "CC BY-SA" if match[1] == "by sa" else "CC BY"
        return " ".join(filter(None, [kind, match[2], (match[3] or "").upper()]))
    return None


def fits(width: int, height: int) -> bool:
    crop_w = min(width, height * 4 / 3)
    kept = (crop_w * crop_w * 3 / 4) / (width * height)
    return crop_w >= HERO_W and kept >= KEEP


def crop_box(width: int, height: int) -> tuple[int, int, int, int]:
    if width * 3 > height * 4:
        crop_w = round(height * 4 / 3)
        left = (width - crop_w) // 2
        return (left, 0, left + crop_w, height)
    crop_h = round(width * 3 / 4)
    top = (height - crop_h) // 2
    return (0, top, width, top + crop_h)


FILLER = {
    "classic",
    "fluffy",
    "creamy",
    "crispy",
    "easy",
    "quick",
    "simple",
    "homemade",
    "hearty",
    "sticky",
    "golden",
    "best",
    "perfect",
    "rustic",
    "healthy",
}


def queries(title: str) -> list[str]:
    """The title, then shorter forms: a long title finds nothing, since every word must match."""
    plain = re.sub(r"\s*\(.*?\)", "", title).strip()
    words = [w for w in plain.split() if w.lower() not in FILLER]
    core = re.split(r"\s+(?:with|in|on)\s+", " ".join(words), maxsplit=1)[0]
    tries = [plain, " ".join(words), core, " ".join(core.split()[-2:])]
    return list(dict.fromkeys(q for q in tries if q))


def plain_text(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def _credit(author: str, licence: str) -> str | None:
    if author:
        return author[:200]
    return "Unknown" if licence in LICENCE_URLS else None  # BY and BY-SA must name someone


def commons_candidate(page: dict[str, Any]) -> Candidate | None:
    info = page.get("imageinfo", [{}])[0]
    meta = info.get("extmetadata", {})
    licence = licence_name(meta.get("LicenseShortName", {}).get("value", ""))
    if licence is None or info.get("mime") not in ("image/jpeg", "image/png"):
        return None
    if not fits(info.get("width", 0), info.get("height", 0)):
        return None
    author = _credit(plain_text(meta.get("Artist", {}).get("value", "")), licence)
    if author is None:
        return None
    return Candidate(
        source="wikimedia",
        download_url=info["thumburl"],
        source_url=info["descriptionurl"],
        title=page["title"].removeprefix("File:"),
        author=author,
        licence=licence,
        licence_url=meta.get("LicenseUrl", {}).get("value") or LICENCE_URLS.get(licence),
        width=info["width"],
        height=info["height"],
    )


def openverse_candidate(result: dict[str, Any]) -> Candidate | None:
    if result.get("source") == "wikimedia":
        return None  # searched directly, with fuller credits
    code, version = result.get("license", ""), result.get("license_version") or ""
    licence = licence_name(code if code in ("cc0", "pdm") else f"cc {code} {version}")
    width, height = result.get("width"), result.get("height")
    if licence is None or not width or not height or not fits(width, height):
        return None
    author = _credit(plain_text(result.get("creator") or ""), licence)
    if author is None:
        return None
    return Candidate(
        source="openverse",
        download_url=result["url"],
        source_url=result["foreign_landing_url"],
        title=plain_text(result.get("title") or ""),
        author=author,
        licence=licence,
        licence_url=result.get("license_url") or LICENCE_URLS.get(licence),
        width=width,
        height=height,
    )


# --- search ---------------------------------------------------------------------------


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text()) if path.exists() else {}


def _save(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + "\n")


def polite_get(client: httpx.Client, url: str, params: dict[str, str]) -> httpx.Response:
    """GET, waiting as long as the server asks whenever it says "too many requests"."""
    for _ in range(6):
        response = client.get(url, params=params)
        if response.status_code != 429:
            response.raise_for_status()
            return response
        wait = int(response.headers.get("retry-after", "30"))
        print(f"  429: waiting {wait}s")
        time.sleep(wait)
    response.raise_for_status()
    return response


def search_commons(client: httpx.Client, title: str) -> list[dict[str, Any]]:
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrnamespace": "6",
        "gsrsearch": f"{title} filetype:bitmap",
        "gsrlimit": "20",
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": "1600",
        "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist",
    }
    response = polite_get(client, "https://commons.wikimedia.org/w/api.php", params)
    pages = response.json().get("query", {}).get("pages", {}).values()
    found = (commons_candidate(p) for p in sorted(pages, key=lambda p: p.get("index", 0)))
    return [c.model_dump() for c in found if c]


def search_openverse(client: httpx.Client, title: str) -> tuple[list[dict[str, Any]], int]:
    params = {"q": title, "license": "cc0,pdm,by,by-sa", "page_size": "20", "mature": "false"}
    response = client.get("https://api.openverse.org/v1/images/", params=params)
    left = int(response.headers.get("x-ratelimit-available-anon_sustained", "1"))
    response.raise_for_status()
    found = (openverse_candidate(r) for r in response.json().get("results", []))
    return [c.model_dump() for c in found if c], left


def search(recipes: Sequence[SeedRecipe]) -> None:
    found = _load(CANDIDATES)
    openverse_open = True
    with httpx.Client(headers=AGENT, timeout=30, follow_redirects=True) as client:
        for n, recipe in enumerate(recipes, 1):
            row = found.setdefault(recipe.slug, {})
            if "wikimedia" not in row:
                row["wikimedia"] = []
                for query in queries(recipe.title):
                    urls = {c["source_url"] for c in row["wikimedia"]}
                    more = search_commons(client, query)
                    row["wikimedia"] += [c for c in more if c["source_url"] not in urls]
                    time.sleep(1.5)
                    if len(row["wikimedia"]) >= MOST:
                        break
            if "openverse" not in row and openverse_open:
                try:  # one search each (200 a day): the shortened title finds most
                    query = queries(recipe.title)[min(2, len(queries(recipe.title)) - 1)]
                    row["openverse"], left = search_openverse(client, query)
                    openverse_open = left > 1
                except httpx.HTTPStatusError as error:
                    print(f"  Openverse stopped: {error.response.status_code}")
                    openverse_open = False
                time.sleep(3.2)  # 20 a minute
            _save(CANDIDATES, found)
            print(
                f"{n:3} {recipe.slug:40} {len(row['wikimedia']):2} commons "
                f"{len(row.get('openverse') or []):2} openverse"
            )
    waiting = sum("openverse" not in row for row in found.values())
    print(f"{len(found)} searched; {waiting} still to search on Openverse (re-run tomorrow)")


def candidates_for(slug: str, found: dict[str, Any]) -> list[Candidate]:
    row = found.get(slug, {})
    seen: set[str] = set()
    out: list[Candidate] = []
    for raw in [*row.get("wikimedia", []), *(row.get("openverse") or [])]:
        c = Candidate.model_validate(raw)
        if c.source_url not in seen:
            seen.add(c.source_url)
            out.append(c)
    return out[:MOST]


# --- check ----------------------------------------------------------------------------


def cache_path(candidate: Candidate) -> Path:
    name = re.sub(r"[^A-Za-z0-9]+", "-", candidate.source_url.split("//", 1)[-1])[-120:]
    return CACHE / f"{name}.img"


async def download(client: httpx.AsyncClient, candidate: Candidate) -> bytes | None:
    path = cache_path(candidate)
    if path.exists():
        return path.read_bytes()
    try:
        response = await client.get(candidate.download_url)
        response.raise_for_status()
    except httpx.HTTPError:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)
    return response.content


def for_checking(data: bytes) -> Photo | None:
    """A 1024px JPEG copy of the 4:3 crop: what will be shown, at fewer tokens."""
    try:
        image = Image.open(io.BytesIO(data)).convert("RGB")
    except OSError:
        return None
    image = image.crop(crop_box(*image.size))
    image.thumbnail((1024, 768))
    out = io.BytesIO()
    image.save(out, "JPEG", quality=85)
    kind = photo_type(out.getvalue())
    return Photo(kind, out.getvalue()) if kind else None


def chosen(checks: dict[str, Any], rejected: set[str]) -> dict[str, dict[str, Any]]:
    """Each recipe's first passing candidate that no earlier recipe took."""
    taken: set[str] = set()
    out: dict[str, dict[str, Any]] = {}
    for slug in sorted(checks):
        for entry in checks[slug]:
            url = entry["candidate"]["source_url"]
            if entry["passes"] and url not in taken and url not in rejected:
                taken.add(url)
                out[slug] = entry
                break
    return out


async def check(recipes: Sequence[SeedRecipe], max_spend: Decimal, workers: int) -> None:
    if settings.anthropic_api_key is None:
        sys.exit("ANTHROPIC_API_KEY is not set")
    found, checks = _load(CANDIDATES), _load(CHECKS)
    rejected = set(json.loads(REJECTED.read_text())) if REJECTED.exists() else set()
    checker = ClaudeImageChecker(settings.anthropic_api_key.get_secret_value(), "claude-haiku-5-5")
    spent = Decimal(0)
    lock = asyncio.Lock()
    queue = list(recipes)

    async def one(client: httpx.AsyncClient, recipe: SeedRecipe) -> None:
        nonlocal spent
        done = checks.setdefault(recipe.slug, [])
        for candidate in candidates_for(recipe.slug, found):
            async with lock:
                taken = {e["candidate"]["source_url"] for e in chosen(checks, rejected).values()}
            entry = next((e for e in done if e["candidate"] == candidate.model_dump()), None)
            if entry and entry["passes"] and candidate.source_url not in taken | rejected:
                return
            if entry or candidate.source_url in taken | rejected:
                continue
            if spent >= max_spend:
                return
            if why := title_clash(recipe, candidate.title):
                done.append(
                    {
                        "candidate": candidate.model_dump(),
                        "passes": False,
                        "check": None,
                        "error": why,
                    }
                )
                continue
            data = await download(client, candidate)
            photo = for_checking(data) if data else None
            if photo is None:
                done.append(
                    {
                        "candidate": candidate.model_dump(),
                        "passes": False,
                        "check": None,
                        "error": "couldn't download or open",
                    }
                )
                continue
            result, usage = await checker.check(recipe, photo)
            async with lock:
                spent += cost_usd(usage) or Decimal(0)
                done.append(
                    {
                        "candidate": candidate.model_dump(),
                        "passes": bool(result and passes(result)),
                        "check": result.model_dump() if result else None,
                    }
                )
                _save(CHECKS, checks)
            if result and passes(result):
                return

    async def worker(client: httpx.AsyncClient) -> None:
        while queue:
            recipe = queue.pop(0)
            await one(client, recipe)

    async with httpx.AsyncClient(headers=AGENT, timeout=60, follow_redirects=True) as client:
        await asyncio.gather(*(worker(client) for _ in range(workers)))
    _save(CHECKS, checks)
    picked = chosen(checks, rejected)
    print(f"spent ${spent:.4f}; {len(picked)}/{len(recipes)} recipes have a passing photo")


# --- write ----------------------------------------------------------------------------


def webp(image: Image.Image, width: int, most: int) -> bytes:
    sized = image.resize((width, width * 3 // 4), Image.Resampling.LANCZOS)
    for quality in range(80, 29, -5):
        out = io.BytesIO()
        sized.save(out, "WEBP", quality=quality, method=6)
        if out.tell() <= most:
            return out.getvalue()
    raise ValueError(f"can't fit {width}px under {most} bytes")


def write(recipes: Sequence[SeedRecipe]) -> None:
    checks = _load(CHECKS)
    rejected = set(json.loads(REJECTED.read_text())) if REJECTED.exists() else set()
    slugs = {r.slug for r in recipes}
    records: list[RecipeImage] = []
    FILES.mkdir(parents=True, exist_ok=True)
    for old in FILES.glob("*.webp"):
        old.unlink()
    for slug, entry in sorted(chosen(checks, rejected).items()):
        if slug not in slugs:
            continue
        candidate, result = Candidate.model_validate(entry["candidate"]), entry["check"]
        image = Image.open(cache_path(candidate)).convert("RGB")
        image = image.crop(crop_box(*image.size))
        for size, (width, most) in SIZES.items():
            (FILES / file_name(slug, size)).write_bytes(webp(image, width, most))
        records.append(
            RecipeImage(
                slug=slug,
                author=candidate.author,
                licence=candidate.licence,
                licence_url=candidate.licence_url,
                source_url=candidate.source_url,
                seen=result["seen"],
                dish=result["dish"],
            )
        )
    RECORDS.write_text(
        json.dumps([r.model_dump() for r in records], indent=1, ensure_ascii=False) + "\n"
    )
    print(f"{len(records)} images written to {FILES}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["search", "check", "write"])
    parser.add_argument("--only", nargs="*", help="these slugs only")
    parser.add_argument("--max-spend", type=Decimal, default=Decimal("6"))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    recipes = [r for r in load_seed_recipes() if not args.only or r.slug in args.only]
    if args.step == "search":
        search(recipes)
    elif args.step == "check":
        asyncio.run(check(recipes, args.max_spend, args.workers))
    else:
        write(recipes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
