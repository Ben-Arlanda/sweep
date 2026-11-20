"""Serving Members' recipe photos (ADR 0031). No sign-in header: the link's signature is
the permission, so it works in a plain <img> like an S3 presigned link will."""

from fastapi import APIRouter, Request, Response

from app import errors
from app.services import recipe_photos

router = APIRouter(prefix="/recipe-photos", tags=["recipes"])


@router.get("/{household_id}/{recipe_id}/{photo_id}/{size}.webp")
async def photo(
    household_id: str,
    recipe_id: str,
    photo_id: str,
    size: str,
    request: Request,
    expires: int = 0,  # missing: refused like a wrong one, with a plain 404
    sig: str = "",
) -> Response:
    path = f"{household_id}/{recipe_id}/{photo_id}/{size}"
    if size not in recipe_photos.SIZES or not recipe_photos.valid(path, expires, sig):
        raise errors.NotFound("Photo not found")
    data = request.app.state.photo_store.get(f"{path}.webp")
    if data is None:
        raise errors.NotFound("Photo not found")
    return Response(
        data, media_type="image/webp", headers={"Cache-Control": "private, max-age=3600"}
    )
