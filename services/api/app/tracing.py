"""Tracing with Langfuse (slice 8b). The only module that imports the Langfuse SDK.

A trace is a timeline of one unit of work: here, one chat turn (or one decision on a
Proposal). Inside it, each step is an *observation*: every model call is a
`generation` (model, tokens, cost, what it saw and said), each tool call a `tool`
(or a `retriever` when it only looks something up), validate a `guardrail`. All turns
of a Conversation share its id as the *session*, so Langfuse shows them in order.

Shape and names follow https://langfuse.com/docs/observability/best-practices:
- one generation per model call, never one around the whole loop
- tools as siblings of the generation that asked for them
- verb-first names that never contain ids or model names (names are an API:
  dashboards and evaluators target them)

Off unless both keys are set and LANGFUSE_TRACING isn't false. Off, every function
here is a cheap no-op, so callers never check. Langfuse is built on OpenTelemetry:
an observation opened with `observe()` becomes the parent of any opened inside it,
across awaits, through Python's context variables.

What gets sent: the Member's messages, the per-turn Household context (Dietary Rules,
which can include allergies, the Kitchen, Preferences), tool arguments and results,
the model's replies. No names or emails; the user id is the Member's UUID. Fine for
test Households; review before real users (ADR 0017).
"""

import logging
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from typing import Any, Literal, Protocol

from langfuse import Langfuse, propagate_attributes
from langfuse.span_filter import is_langfuse_span
from opentelemetry.sdk.trace import ReadableSpan

from app.config import Settings

log = logging.getLogger(__name__)

ObservationType = Literal[
    "span", "agent", "tool", "chain", "retriever", "evaluator", "guardrail", "generation"
]

# Names are kept stable: evaluators, dashboards and saved filters select by them.
TURN = "plan-meals-turn"
DECIDE = "decide-on-plan"
GENERATION = "choose-next-step"


class Observation(Protocol):
    def update(self, **fields: Any) -> None:
        """Set output, metadata, level, status_message, usage_details, cost_details..."""
        ...


class _Nothing:
    def update(self, **fields: Any) -> None:
        pass


class _Live:
    """Our small interface over a Langfuse observation, so nothing else depends on the
    SDK's types."""

    def __init__(self, observation: Any) -> None:
        self._observation = observation

    def update(self, **fields: Any) -> None:
        self._observation.update(**{k: v for k, v in fields.items() if v is not None})


_NOTHING = _Nothing()
_client: Langfuse | None = None


def export_span(span: ReadableSpan) -> bool:
    """Send only the spans this module creates. By default Langfuse also exports any
    library's GenAI spans, and the Anthropic SDK makes one per call: a second generation
    under ours, with its cost counted again (and priced without the thinking tokens).
    Found auditing the first live trace, 2026-11-16."""
    return is_langfuse_span(span)


def client_settings(settings: Settings) -> dict[str, Any] | None:
    """The Langfuse client's arguments, or None when tracing is off."""
    public, secret = settings.langfuse_public_key, settings.langfuse_secret_key
    if not settings.langfuse_tracing or public is None or secret is None:
        return None
    return {
        "public_key": public.get_secret_value(),
        "secret_key": secret.get_secret_value(),
        "base_url": settings.langfuse_base_url,
        "environment": settings.langfuse_environment,
        "tracing_enabled": True,
        "should_export_span": export_span,
    }


def configure(settings: Settings) -> bool:
    """Start tracing if it's switched on. Returns whether it is."""
    config = client_settings(settings)
    install(Langfuse(**config) if config is not None else None)
    if config is not None:
        log.info("Langfuse tracing on (%s, %s)", config["base_url"], config["environment"])
    return config is not None


def install(client: Langfuse | None) -> None:
    """Use this client (tests pass one that exports to memory). None turns tracing off."""
    global _client
    _client = client


def flush() -> None:
    """Send what's buffered. Scripts call this before exiting; the app on shutdown."""
    if _client is not None:
        _client.flush()


def shutdown() -> None:
    if _client is not None:
        _client.shutdown()


@contextmanager
def observe(
    name: str,
    *,
    as_type: ObservationType = "span",
    input: Any = None,
    metadata: dict[str, Any] | None = None,
    model: str | None = None,
    model_parameters: dict[str, Any] | None = None,
) -> Iterator[Observation]:
    """One step, nested under whatever observation is open around it."""
    if _client is None:
        yield _NOTHING
        return
    extra: dict[str, Any] = {}
    if as_type == "generation":
        extra = {"model": model, "model_parameters": model_parameters}
    with _client.start_as_current_observation(
        name=name,
        as_type=as_type,
        input=input,
        metadata=metadata,
        **extra,
    ) as observation:
        yield _Live(observation)


@contextmanager
def turn(
    name: str,
    *,
    session_id: str,
    user_id: str,
    input: Any,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[Observation]:
    """The root of a trace. session_id, user_id and tags reach every observation inside,
    so the session view and per-user filters work on each step, not just the root."""
    if _client is None:
        yield _NOTHING
        return
    with ExitStack() as stack:
        # Attributes first, so the root observation carries them too.
        stack.enter_context(
            propagate_attributes(session_id=session_id, user_id=user_id, tags=tags, trace_name=name)
        )
        root = stack.enter_context(
            _client.start_as_current_observation(
                name=name, as_type="agent", input=input, metadata=metadata
            )
        )
        yield _Live(root)
