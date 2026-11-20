"""Helpers shared by route modules."""

from collections.abc import Awaitable, Callable, Sequence

from fastapi import Request, Response, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import errors, idempotency
from app.services.households import MemberContext
from app.services.recipe_import import MAX_PHOTO_BYTES, MAX_PHOTOS, Photo, photo_type


async def idempotent(
    request: Request,
    session: AsyncSession,
    ctx: MemberContext,
    key: str,
    work: Callable[[], Awaitable[BaseModel | None]],
    status_code: int = status.HTTP_200_OK,
    body: bytes | None = None,
) -> Response:
    """Do `work` once per key: claim the key, run, store the response, commit together.
    An upload passes its file as `body`: FastAPI has already read the raw request."""
    raw = body if body is not None else await request.body()
    print_ = idempotency.fingerprint(request, raw)
    replay = await idempotency.claim(session, ctx.member.id, key, print_)
    if replay is not None:
        return _response(replay.status_code, replay.response)

    result = await work()  # a DomainError here rolls back the claim too: nothing is stored
    content = result.model_dump(mode="json") if result is not None else None
    await idempotency.record(session, ctx.member.id, key, status_code, content)
    await session.commit()  # the change, the stored response and the NOTIFY, all at once
    return _response(status_code, content)


async def checked_photos(uploads: Sequence[UploadFile], what: str) -> list[Photo]:
    """Uploaded photos, checked: 1 to 3, 5 MB each, and the type from the first bytes."""
    if not 1 <= len(uploads) <= MAX_PHOTOS:
        raise errors.InvalidInput(f"Add 1 to {MAX_PHOTOS} photos{what}.")
    read: list[Photo] = []
    for upload in uploads:
        data = await upload.read(MAX_PHOTO_BYTES + 1)  # one byte over is enough to tell
        if len(data) > MAX_PHOTO_BYTES:
            raise errors.InvalidInput("Each photo can be up to 5 MB.")
        kind = photo_type(data)
        if kind is None:
            raise errors.InvalidInput("Photos must be JPEG, PNG or WebP.")
        read.append(Photo(media_type=kind, data=data))
    return read


def _response(status_code: int, content: object) -> Response:
    if content is None:
        return Response(status_code=status_code)
    return JSONResponse(status_code=status_code, content=content)
