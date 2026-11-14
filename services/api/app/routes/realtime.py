"""WebSocket for change notices.

Browsers can't put an Authorization header on a WebSocket, and tokens in the URL end up
in access logs. So the device connects, then sends `{"type": "auth", "token": "..."}` as
its first message. The server verifies the token and finds the Member's Household,
subscribes the socket, and replies `{"type": "subscribed"}`.

**The device should refetch after "subscribed"**: anything that changed between its
last fetch and the subscription starting would otherwise be missed.

Close codes (4000–4999 are free for apps to use): 4401 = bad or missing token,
4403 = signed in but not in a Household.
"""

import asyncio
import contextlib
from typing import cast

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import InvalidToken, TokenVerifier
from app.errors import NotInHousehold
from app.realtime import Hub
from app.services import households

router = APIRouter()

AUTH_TIMEOUT_SECONDS = 10
CLOSE_UNAUTHORISED = 4401
CLOSE_NO_HOUSEHOLD = 4403


@router.websocket("/ws")
async def changes(ws: WebSocket) -> None:
    await ws.accept()
    try:
        first = await asyncio.wait_for(ws.receive_json(), AUTH_TIMEOUT_SECONDS)
    except (TimeoutError, ValueError, WebSocketDisconnect):
        await _close(ws, CLOSE_UNAUTHORISED)
        return
    token = first.get("token") if isinstance(first, dict) else None
    if not isinstance(first, dict) or first.get("type") != "auth" or not isinstance(token, str):
        await _close(ws, CLOSE_UNAUTHORISED)
        return

    verifier = cast(TokenVerifier, ws.app.state.token_verifier)
    try:
        identity = await run_in_threadpool(verifier.verify, token)
    except InvalidToken:
        await _close(ws, CLOSE_UNAUTHORISED)
        return

    sessionmaker = cast(async_sessionmaker[AsyncSession], ws.app.state.sessionmaker)
    async with sessionmaker() as session:
        try:
            ctx = await households.get_member_context(session, identity)
        except NotInHousehold:
            await _close(ws, CLOSE_NO_HOUSEHOLD)
            return
    household_id = ctx.household.id

    hub = cast(Hub, ws.app.state.hub)
    queue = hub.subscribe(household_id)
    try:
        # Don't say "subscribed" until Postgres is actually listening, or a change made
        # right after it would be lost.
        await hub.ready.wait()
        await ws.send_json({"type": "subscribed"})
        sender = asyncio.create_task(_forward(ws, queue))
        receiver = asyncio.create_task(_drain(ws))  # notices when the device hangs up
        _, pending = await asyncio.wait({sender, receiver}, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, WebSocketDisconnect):
                await task
    finally:
        hub.unsubscribe(household_id, queue)


async def _forward(ws: WebSocket, queue: asyncio.Queue[dict[str, object]]) -> None:
    while True:
        await ws.send_json(await queue.get())


async def _drain(ws: WebSocket) -> None:
    with contextlib.suppress(WebSocketDisconnect):
        while True:
            await ws.receive_text()  # devices don't send anything after auth; ignore it


async def _close(ws: WebSocket, code: int) -> None:
    with contextlib.suppress(RuntimeError):
        await ws.close(code=code)
