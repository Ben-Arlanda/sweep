"""Langfuse tracing (slice 8b): the real SDK, exporting to memory instead of the network.

What a good trace looks like (https://langfuse.com/docs/observability/best-practices):
one trace per chat turn, one session per Conversation, a generation per model call
(not one around the whole loop), tools as siblings of the generation that asked for
them, verb-first names that never contain ids or model names.
"""

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from langfuse import Langfuse
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from pydantic import SecretStr
from sqlalchemy import Engine

from app import tracing
from app.config import Settings
from tests.conftest import ClientFor, FakeIssuer, Loader
from tests.fake_model import ScriptedModel, tool
from tests.fake_model import text as say_text
from tests.helpers import create_household
from tests.test_agent import MON, rid_in_db, say, start
from tests.test_approvals import decide, two_dinners
from tests.test_recipes import CURRY, PASTA

pytestmark = pytest.mark.anyio


@pytest.fixture
def spans() -> Iterator[InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    client = Langfuse(
        # Unique per test: Langfuse reuses one client per public key and ignores new
        # arguments, so a shared key would send every test's spans to the first exporter.
        public_key=f"pk-lf-test-{uuid.uuid4().hex}",
        secret_key="sk-lf-test",
        base_url="http://langfuse.invalid",
        tracing_enabled=True,
        span_exporter=exporter,
        tracer_provider=TracerProvider(),
        environment="test",
    )
    tracing.install(client)
    yield exporter
    tracing.install(None)
    client.shutdown()


def finished(exporter: InMemorySpanExporter) -> list[ReadableSpan]:
    tracing.flush()
    return list(exporter.get_finished_spans())


def attr(span: ReadableSpan, key: str) -> Any:
    return (span.attributes or {}).get(key)


def kind(span: ReadableSpan) -> Any:
    return attr(span, "langfuse.observation.type")


def children(all_spans: list[ReadableSpan], parent: ReadableSpan) -> list[ReadableSpan]:
    pid = parent.context.span_id if parent.context else None
    found = [s for s in all_spans if s.parent is not None and s.parent.span_id == pid]
    return sorted(found, key=lambda s: s.start_time or 0)


# --- configuration -------------------------------------------------------------------


def test_tests_never_send_traces_even_with_keys_in_env() -> None:
    # conftest sets LANGFUSE_TRACING=false, which wins over a local .env.
    assert Settings().langfuse_tracing is False
    assert tracing.client_settings(Settings()) is None


def test_tracing_needs_both_keys_and_the_switch() -> None:
    def with_keys(on: bool) -> Settings:
        return Settings(
            langfuse_tracing=on,
            langfuse_public_key=SecretStr("pk-lf-x"),
            langfuse_secret_key=SecretStr("sk-lf-x"),
        )

    no_keys = Settings(langfuse_tracing=True, langfuse_public_key=None, langfuse_secret_key=None)
    assert tracing.client_settings(no_keys) is None
    on = tracing.client_settings(with_keys(True))
    assert on is not None
    assert on["base_url"] == "https://cloud.langfuse.com"
    assert on["environment"] == "development"
    assert tracing.client_settings(with_keys(False)) is None


def test_without_a_client_everything_is_a_cheap_no_op() -> None:
    tracing.install(None)
    with tracing.turn("plan-meals", session_id="s", user_id="u", input="hi") as obs:
        with tracing.observe("run-tool", as_type="tool") as child:
            child.update(output="ok")
        obs.update(output="done")
    tracing.flush()


# --- the agent's trace shape ------------------------------------------------------------


async def test_a_chat_turn_is_one_trace_in_the_conversation_session(
    client_for: ClientFor,
    fake_issuer: FakeIssuer,
    load: Loader,
    db: Engine,
    spans: InMemorySpanExporter,
) -> None:
    await load([CURRY, PASTA])
    curry, pasta = await rid_in_db(db, "chicken-curry"), await rid_in_db(db, "tomato-pasta")
    model = ScriptedModel(two_dinners(curry, pasta, "Rice"))
    async with client_for(model) as client:
        await create_household(client, fake_issuer, "ana")
        cid = await start(client, fake_issuer)
        await say(client, fake_issuer, cid, "plan two dinners")

    all_spans = finished(spans)
    [root] = [s for s in all_spans if s.parent is None]
    assert root.name == "plan-meals-turn" and kind(root) == "agent"
    assert attr(root, "langfuse.observation.input") == "plan two dinners"
    assert attr(root, "session.id") == cid  # one session per Conversation
    assert attr(root, "user.id")  # the Member's id, never a name or email

    steps = children(all_spans, root)
    names = [s.name for s in steps]
    # A generation per model call, interleaved with the tools it asked for.
    assert names == [
        "load-household-context",
        "choose-next-step",
        "set_planned_meal",
        "set_planned_meal",
        "set_list_additions",
        "choose-next-step",
        "propose_plan",
        "validate-plan",
    ]
    generations = [s for s in steps if kind(s) == "generation"]
    assert len(generations) == 2
    gen = generations[0]
    assert attr(gen, "langfuse.observation.model.name") == "scripted"
    usage = attr(gen, "langfuse.observation.usage_details")
    assert '"input": 1000' in usage and '"output": 100' in usage
    assert kind(steps[2]) == "tool"
    assert kind(steps[0]) == "retriever"
    assert kind(steps[-1]) == "guardrail"
    # Every span is tagged with the same session, so the session view joins turns.
    assert {attr(s, "session.id") for s in all_spans} == {cid}


async def test_reads_are_retrievers_and_tool_errors_are_marked(
    client_for: ClientFor,
    fake_issuer: FakeIssuer,
    load: Loader,
    spans: InMemorySpanExporter,
) -> None:
    await load([CURRY])
    model = ScriptedModel(
        [
            [tool("search_recipes", query="curry"), tool("get_recipe", recipe_id="not-a-uuid")],
            [say_text("Here you go.")],
        ]
    )
    async with client_for(model) as client:
        await create_household(client, fake_issuer, "ana")
        cid = await start(client, fake_issuer)
        await say(client, fake_issuer, cid, "find a curry")

    by_name = {s.name: s for s in finished(spans)}
    assert kind(by_name["search_recipes"]) == "retriever"
    bad = by_name["get_recipe"]
    assert attr(bad, "langfuse.observation.level") == "ERROR"
    assert "Invalid arguments" in attr(bad, "langfuse.observation.status_message")


async def test_approving_is_its_own_trace_in_the_same_session(
    client_for: ClientFor,
    fake_issuer: FakeIssuer,
    load: Loader,
    db: Engine,
    spans: InMemorySpanExporter,
) -> None:
    await load([CURRY, PASTA])
    curry, pasta = await rid_in_db(db, "chicken-curry"), await rid_in_db(db, "tomato-pasta")
    async with client_for(ScriptedModel(two_dinners(curry, pasta))) as client:
        await create_household(client, fake_issuer, "ana")
        cid = await start(client, fake_issuer)
        events = await say(client, fake_issuer, cid, "plan")
        pid = next(e for e in events if e["type"] == "proposal")["proposal"]["id"]
        finished(spans)  # send the turn's spans, then forget them
        spans.clear()
        response = await decide(client, fake_issuer, pid, {"action": "approve"})
        assert response.status_code == 200

    all_spans = finished(spans)
    [root] = [s for s in all_spans if s.parent is None]
    assert root.name == "decide-on-plan"
    assert attr(root, "session.id") == cid
    assert [s.name for s in children(all_spans, root)] == ["save-approved-plan"]


def test_names_never_carry_ids_or_models() -> None:
    # Names are an API for dashboards and evaluators: low cardinality, stable.
    assert tracing.TURN == "plan-meals-turn"
    assert "sonnet" not in tracing.GENERATION and MON not in tracing.GENERATION


def test_only_our_own_spans_are_sent() -> None:
    # Found auditing the first live trace: the Anthropic SDK emits its own generation
    # span for each call, which Langfuse exports by default. That counted every call's
    # cost twice (and priced it without the thinking tokens). Ours stays; theirs goes.
    anthropic_span = ReadableSpan(
        name="anthropic.messages.create",
        instrumentation_scope=InstrumentationScope("com.anthropic.sdk.python", "2.8.0"),
    )
    assert tracing.export_span(anthropic_span) is False
    with_keys = Settings(
        langfuse_tracing=True,
        langfuse_public_key=SecretStr("pk-lf-x"),
        langfuse_secret_key=SecretStr("sk-lf-x"),
    )
    config = tracing.client_settings(with_keys)
    assert config is not None and config["should_export_span"] is tracing.export_span


async def test_a_generation_records_the_request_parameters(
    client_for: ClientFor, fake_issuer: FakeIssuer, spans: InMemorySpanExporter
) -> None:
    model = ScriptedModel([[say_text("Hi!")]])
    model.parameters = {"max_tokens": 16000, "effort": "medium"}
    async with client_for(model) as client:
        await create_household(client, fake_issuer, "ana")
        cid = await start(client, fake_issuer)
        await say(client, fake_issuer, cid, "hello")
    [gen] = [s for s in finished(spans) if kind(s) == "generation"]
    params = attr(gen, "langfuse.observation.model.parameters")
    assert '"effort": "medium"' in params and '"max_tokens": 16000' in params
