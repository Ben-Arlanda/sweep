"""HTTP routes for chatting with the agent.

`POST /conversations/{id}/messages` answers with Server-Sent Events (SSE): one HTTP
response that stays open and sends events as they happen (`event: text`, `event: tool`,
`event: proposal`...), ending with `event: done` or `event: error`. The browser and the
app read it as a stream, so the reply appears while it's being written.
"""

import json
import uuid
from collections.abc import AsyncIterator
from typing import cast

from fastapi import APIRouter, Request, status
from fastapi.responses import StreamingResponse

from app import errors
from app.deps import MemberDep, SessionDep
from app.schemas import ChatLine, ConversationDetailOut, ConversationOut, SendMessageIn
from app.services import conversations
from app.services.conversations import Agent

router = APIRouter(prefix="/conversations", tags=["agent"])


def _agent(request: Request) -> Agent:
    agent = cast(Agent | None, request.app.state.agent)
    if agent is None:
        raise errors.Unavailable("The assistant isn't configured on this server")
    return agent


@router.post("", status_code=status.HTTP_201_CREATED)
async def create(ctx: MemberDep, session: SessionDep) -> ConversationOut:
    conversation = await conversations.create(session, ctx)
    await session.commit()
    return ConversationOut.model_validate(conversation)


@router.get("/{conversation_id}")
async def get(
    conversation_id: uuid.UUID, request: Request, ctx: MemberDep, session: SessionDep
) -> ConversationDetailOut:
    conversation = await conversations.get(session, ctx, conversation_id)
    state = await _agent(request).state(conversation.id)
    return ConversationDetailOut(
        id=conversation.id,
        created_at=conversation.created_at,
        messages=[ChatLine.model_validate(line) for line in conversations.transcript(state)],
        draft=state.get("draft"),
        proposal=state.get("proposal"),
    )


@router.post("/{conversation_id}/messages")
async def send(
    conversation_id: uuid.UUID,
    body: SendMessageIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
) -> StreamingResponse:
    # Check access and configuration before the stream starts, so they're normal errors.
    conversation = await conversations.get(session, ctx, conversation_id)
    agent = _agent(request)

    async def events() -> AsyncIterator[str]:
        async for event in agent.run_turn(conversation, body.text):
            yield f"event: {event['type']}\ndata: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        # Stop proxies holding the stream back to send it all at once.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
