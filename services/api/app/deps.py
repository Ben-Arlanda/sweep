"""FastAPI dependencies: the request-level wiring between HTTP and the services.

A typical route gets: database session → verified Identity → MemberContext.
"""

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import Identity, InvalidToken, TokenVerifier
from app.services import households
from app.services.households import MemberContext

bearer = HTTPBearer(auto_error=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One session per request. Routes commit explicitly; anything uncommitted rolls back."""
    sessionmaker = cast(async_sessionmaker[AsyncSession], request.app.state.sessionmaker)
    async with sessionmaker() as session:
        yield session


async def get_identity(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Identity:
    unauthorised = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid login token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorised

    verifier = cast(TokenVerifier, request.app.state.token_verifier)
    try:
        # Fetching the issuer's keys is blocking network I/O (cached after the first call),
        # so run it in a worker thread instead of stalling the event loop.
        return await run_in_threadpool(verifier.verify, credentials.credentials)
    except InvalidToken as error:
        raise unauthorised from error


SessionDep = Annotated[AsyncSession, Depends(get_session)]
IdentityDep = Annotated[Identity, Depends(get_identity)]


async def get_member_context(session: SessionDep, identity: IdentityDep) -> MemberContext:
    return await households.get_member_context(session, identity)


MemberDep = Annotated[MemberContext, Depends(get_member_context)]
