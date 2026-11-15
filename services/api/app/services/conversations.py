"""Conversations with the agent: who can see them, and running one turn.

A turn streams events as they happen: text as Claude writes it, each tool call, draft
changes, and the Proposal. The route turns them into Server-Sent Events.
"""

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphRecursionError
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app import errors
from app.agent import graph
from app.agent.checkpoints import Checkpoints
from app.agent.model import AgentModel, ModelUnavailable
from app.agent.prompt import CONTEXT_TAG, today_in_sydney
from app.agent.state import AgentState
from app.agent.tools import AgentContext
from app.embeddings import Embedder
from app.models import Conversation
from app.services.households import MemberContext

log = logging.getLogger(__name__)

TURN_TIMEOUT_SECONDS = 60
Graph = CompiledStateGraph[AgentState, AgentContext, Any, Any]


async def create(session: AsyncSession, ctx: MemberContext) -> Conversation:
    conversation = Conversation(household_id=ctx.household.id, member_id=ctx.member.id)
    session.add(conversation)
    await session.flush()
    return conversation


async def list_mine(
    session: AsyncSession, ctx: MemberContext, limit: int = 20
) -> list[Conversation]:
    """The Member's own Conversations in their current Household, newest first. The app
    reopens the first one, so a chat started on the phone carries on in the browser."""
    found = await session.execute(
        select(Conversation)
        .where(
            Conversation.member_id == ctx.member.id,
            Conversation.household_id == ctx.household.id,
        )
        .order_by(Conversation.created_at.desc(), Conversation.id.desc())
        .limit(limit)
    )
    return list(found.scalars())


async def get(
    session: AsyncSession, ctx: MemberContext, conversation_id: uuid.UUID
) -> Conversation:
    found = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.member_id == ctx.member.id,  # private to the Member who started it
        )
    )
    conversation = found.scalar_one_or_none()
    if conversation is None:
        raise errors.NotFound("Conversation not found")  # same answer for "not yours"
    return conversation


def _config(conversation_id: uuid.UUID) -> RunnableConfig:
    return {
        "configurable": {"thread_id": str(conversation_id)},
        "recursion_limit": graph.RECURSION_LIMIT,
    }


class Agent:
    """Everything a turn needs that lives for the whole app: the model, the compiled
    graph (built once, on first use) and the checkpoint store."""

    def __init__(
        self,
        model: AgentModel,
        checkpoints: Checkpoints,
        engine: AsyncEngine,
        sessionmaker: async_sessionmaker[AsyncSession],
        embedder: Embedder | None,
        daily_token_budget: int,
    ) -> None:
        self.model = model
        self.checkpoints = checkpoints
        self.engine = engine
        self.sessionmaker = sessionmaker
        self.embedder = embedder
        self.daily_token_budget = daily_token_budget
        self._graph: Graph | None = None

    async def graph(self) -> Graph:
        if self._graph is None:
            self._graph = graph.build(await self.checkpoints.saver())
        return self._graph

    async def state(self, conversation_id: uuid.UUID) -> dict[str, Any]:
        snapshot = await (await self.graph()).aget_state(_config(conversation_id))
        return dict(snapshot.values)

    def _context(self, conversation: Conversation) -> AgentContext:
        return AgentContext(
            sessionmaker=self.sessionmaker,
            conversation_id=conversation.id,
            household_id=conversation.household_id,
            member_id=conversation.member_id,
            model=self.model,
            embedder=self.embedder,
            today=today_in_sydney(),
            daily_token_budget=self.daily_token_budget,
        )

    @asynccontextmanager
    async def _one_at_a_time(self, conversation_id: uuid.UUID) -> AsyncIterator[bool]:
        """One turn or decision at a time per Conversation, across every API instance: a
        Postgres advisory lock, held on its own connection while the graph runs. Yields
        False if something else holds it."""
        async with self.engine.connect() as lock_conn:
            key = {"k": str(conversation_id)}
            got = bool(
                await lock_conn.scalar(
                    text("SELECT pg_try_advisory_lock(hashtextextended(:k, 0))"), key
                )
            )
            try:
                yield got
            finally:
                if got:
                    await lock_conn.execute(
                        text("SELECT pg_advisory_unlock(hashtextextended(:k, 0))"), key
                    )

    async def waiting_on(self, conversation_id: uuid.UUID) -> str | None:
        """The id of the Proposal the paused graph is waiting on, if it is paused."""
        snapshot = await (await self.graph()).aget_state(_config(conversation_id))
        if "approve" not in snapshot.next:
            return None
        proposal = snapshot.values.get("proposal") or {}
        return proposal.get("id")

    async def run_turn(
        self, conversation: Conversation, user_text: str
    ) -> AsyncIterator[dict[str, Any]]:
        compiled = await self.graph()
        async with self._one_at_a_time(conversation.id) as got:
            if not got:
                yield {"type": "error", "message": "Still answering your last message."}
                return
            # Waiting on a Proposal? Then this message is the answer: "change something"
            # instead of approving. Resuming supersedes the Proposal and carries on.
            turn_input: Any = {"user_text": user_text}
            if await self.waiting_on(conversation.id) is not None:
                turn_input = Command(resume={"action": "message", "text": user_text})
            try:
                async with asyncio.timeout(TURN_TIMEOUT_SECONDS):
                    async for chunk in compiled.astream(
                        turn_input,
                        _config(conversation.id),
                        context=self._context(conversation),
                        stream_mode="custom",
                    ):
                        yield cast(dict[str, Any], chunk)
                yield {"type": "done"}
            except TimeoutError:
                yield {"type": "error", "message": "That took too long. Please try again."}
            except GraphRecursionError:
                yield {"type": "error", "message": "I got stuck planning that. Try again?"}
            except ModelUnavailable:
                yield {"type": "error", "message": "The assistant is unavailable right now."}
            except Exception:
                log.exception("agent turn failed")
                yield {"type": "error", "message": "Something went wrong. Please try again."}

    async def decide(
        self, conversation: Conversation, proposal_id: uuid.UUID, decision: dict[str, Any]
    ) -> None:
        """Resume the paused graph with the Member's answer. No LLM call: approve goes
        straight to commit, reject ends the run."""
        compiled = await self.graph()
        async with self._one_at_a_time(conversation.id) as got:
            if not got:
                raise errors.Conflict("Still answering your last message. Try again shortly.")
            if await self.waiting_on(conversation.id) != str(proposal_id):
                raise errors.Conflict("This plan is no longer waiting for an answer")
            async with asyncio.timeout(TURN_TIMEOUT_SECONDS):
                await compiled.ainvoke(
                    Command(resume=decision),
                    _config(conversation.id),
                    context=self._context(conversation),
                )

    async def forget_member(self, session: AsyncSession, member_id: uuid.UUID) -> None:
        """Account deletion: drop the Member's conversations and their saved state.
        The checkpoint tables aren't linked by foreign key, so this must be explicit."""
        ids = list(
            (
                await session.execute(
                    select(Conversation.id).where(Conversation.member_id == member_id)
                )
            ).scalars()
        )
        saver = await self.checkpoints.saver()
        for conversation_id in ids:
            await saver.adelete_thread(str(conversation_id))
        await session.execute(delete(Conversation).where(Conversation.member_id == member_id))


def transcript(state: dict[str, Any]) -> list[dict[str, str]]:
    """The chat as the Member saw it: their words and the agent's replies, in order.
    Leaves out the Household context, tool calls and tool results, and narration: text
    the agent wrote in the same message as a tool call. The app shows narration as a
    passing status while streaming, so a reload looks the same as the live chat."""
    out: list[dict[str, str]] = []
    for message in state.get("messages", []):
        blocks = message["content"]
        if isinstance(blocks, list) and any(
            isinstance(b, dict) and b.get("type") == "tool_use" for b in blocks
        ):
            continue
        texts = [
            b["text"]
            for b in message["content"]
            if isinstance(b, dict)
            and b.get("type") == "text"
            and not b["text"].startswith(f"<{CONTEXT_TAG}>")
        ]
        if texts:
            out.append({"role": message["role"], "text": "\n".join(texts)})
    return out
