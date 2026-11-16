"""The agent's view of an LLM: send the conversation, get the next assistant turn.

A small interface, so the graph doesn't know or care which provider answers. The real
one is ClaudeAgentModel in app/llm.py; tests use a scripted fake.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.llm_costs import Usage


@dataclass(frozen=True)
class ModelTurn:
    # Content blocks exactly as the API returned them (text, tool_use, thinking...).
    # They go back into the history unchanged.
    content: list[dict[str, Any]]
    stop_reason: str  # "end_turn", "tool_use", "refusal", "max_tokens"...
    usage: Usage  # tokens by kind, so the call can be priced (app/llm_costs.py)


class AgentModel(Protocol):
    name: str

    @property
    def parameters(self) -> Mapping[str, Any]:
        """Request settings worth recording in traces (effort, max tokens). Read-only."""
        ...

    async def respond(
        self,
        system: str,
        tools: Sequence[dict[str, Any]],
        messages: Sequence[dict[str, Any]],
        on_text: Callable[[str], None],
    ) -> ModelTurn:
        """One model call. `on_text` receives reply text as it's written (for streaming)."""
        ...


class ModelUnavailable(Exception):
    """The provider couldn't answer (outage, rate limit after retries, bad key)."""
