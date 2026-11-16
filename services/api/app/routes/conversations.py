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
from pydantic import RootModel

from app import errors
from app.agent.prompt import transcript
from app.deps import MemberDep, SessionDep
from app.routes.proposals import proposal_fields, proposal_out
from app.schemas import (
    ChatLine,
    ChatProposalOut,
    ConversationDetailOut,
    ConversationIn,
    ConversationOut,
    DraftOut,
    SendMessageIn,
    TurnEvent,
)
from app.services import conversations, turn_limits
from app.services.conversations import Agent

router = APIRouter(prefix="/conversations", tags=["agent"])


def _agent(request: Request) -> Agent:
    agent = cast(Agent | None, request.app.state.agent)
    if agent is None:
        raise errors.Unavailable("The assistant isn't configured on this server")
    return agent


@router.post("", status_code=status.HTTP_201_CREATED)
async def create(
    ctx: MemberDep, session: SessionDep, body: ConversationIn | None = None
) -> ConversationOut:
    plan = body or ConversationIn()
    conversation = await conversations.create(session, ctx, plan.mode, plan.days)
    await session.commit()
    return ConversationOut.model_validate(conversation)


@router.get("")
async def list_mine(ctx: MemberDep, session: SessionDep) -> list[ConversationOut]:
    found = await conversations.list_mine(session, ctx)
    return [ConversationOut.model_validate(c) for c in found]


@router.get("/{conversation_id}")
async def get(
    conversation_id: uuid.UUID, request: Request, ctx: MemberDep, session: SessionDep
) -> ConversationDetailOut:
    conversation = await conversations.get(session, ctx, conversation_id)
    state = await _agent(request).state(conversation.id)
    saved = await conversations.proposals_of(session, conversation.id)
    positions = conversations.proposal_positions(state)
    waiting = (state.get("proposal") or {}).get("id")
    current = next((p for p in saved if str(p.id) == waiting), None)
    return ConversationDetailOut(
        id=conversation.id,
        created_at=conversation.created_at,
        plan_mode=conversation.plan_mode,
        plan_days=conversation.plan_days,
        messages=[ChatLine.model_validate(line) for line in transcript(state)],
        draft=DraftOut.model_validate(d) if (d := state.get("draft")) else None,
        proposal=proposal_out(current) if current is not None else None,
        proposals=[
            ChatProposalOut.model_validate(
                {**proposal_fields(p), "after_line": positions.get(str(p.id))}
            )
            for p in saved
        ],
    )


class EventStreamResponse(StreamingResponse):
    media_type = "text/event-stream"


class TurnEvents(RootModel[TurnEvent]):
    """OpenAPI can't describe a stream, so the docs describe one event. That's enough
    for the generated TypeScript to include every event type."""


@router.post(
    "/{conversation_id}/messages",
    response_class=EventStreamResponse,
    responses={200: {"model": TurnEvents, "description": "Server-Sent Events, one per `data:`"}},
)
async def send(
    conversation_id: uuid.UUID,
    body: SendMessageIn,
    request: Request,
    ctx: MemberDep,
    session: SessionDep,
) -> EventStreamResponse:
    # Check access, configuration and the rate limits before the stream starts, so
    # they're normal errors (403/404, 503, 409 or 429), not events inside a 200.
    conversation = await conversations.get(session, ctx, conversation_id)
    agent = _agent(request)
    turn_id = await turn_limits.start(session, ctx.member.id, conversation.id)

    async def events() -> AsyncIterator[str]:
        try:
            async for event in agent.run_turn(conversation, body.text):
                yield f"event: {event['type']}\ndata: {json.dumps(event, default=str)}\n\n"
        finally:  # also when the Member closes the app mid-reply
            await turn_limits.finish(agent.sessionmaker, turn_id)

    return EventStreamResponse(
        events(),
        # Stop proxies holding the stream back to send it all at once.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
