"""Helpers shared by route modules."""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import idempotency
from app.services.households import MemberContext


async def idempotent(
    request: Request,
    session: AsyncSession,
    ctx: MemberContext,
    key: str,
    work: Callable[[], Awaitable[BaseModel | None]],
    status_code: int = status.HTTP_200_OK,
) -> Response:
    """Do `work` once per key: claim the key, run, store the response, commit together."""
    print_ = idempotency.fingerprint(request, await request.body())
    replay = await idempotency.claim(session, ctx.member.id, key, print_)
    if replay is not None:
        return _response(replay.status_code, replay.response)

    result = await work()  # a DomainError here rolls back the claim too: nothing is stored
    content = result.model_dump(mode="json") if result is not None else None
    await idempotency.record(session, ctx.member.id, key, status_code, content)
    await session.commit()  # the change, the stored response and the NOTIFY, all at once
    return _response(status_code, content)


def _response(status_code: int, content: object) -> Response:
    if content is None:
        return Response(status_code=status_code)
    return JSONResponse(status_code=status_code, content=content)
