"""The LangGraph agent (plan §7).

    START → load_context → agent ⇄ tools
                             │ (agent called propose_plan)
                             ▼
                          validate ─ problems, replans left ─→ agent
                             │ ok, or out of replans (bad meals dropped): Proposal saved
                             ▼
                          approve  ← interrupt(): the graph pauses, saved in Postgres
                             │ resumed by POST /proposals/{id}/decision, or a chat message
                ┌────────────┼──────────────┐
             approve       reject         message (Proposal superseded)
                ▼            ▼              ▼
             commit         END         load_context → agent ... (a normal turn)
                ▼
               END

The LLM chooses which tools to call and in what order: that's the "agent" part, and
why "plan 5 dinners" and "we already have pasta" take different paths. Everything that
must be right (which Household, Dietary Rules, recipe ids, limits) is plain code around
it.
"""

import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Checkpointer, interrupt
from pydantic import ValidationError

from app import tracing
from app.agent import prompt, tools
from app.agent.state import AgentState, Draft, empty_draft
from app.agent.tools import AgentContext, Call, ToolError
from app.agent.validate import Problem, build_proposal, explain_additions, validate_draft
from app.llm_costs import cost_usd
from app.models import Conversation, ProposalStatus, Recipe
from app.services import (
    adaptations,
    diet,
    ingredients,
    meal_plan,
    proposals,
    recipes,
    shopping_lists,
    token_budget,
)
from app.services.diet import DietaryRules

MAX_TOOL_CALLS = 15  # per turn: the agent should be done well before this
MAX_REPLANS = 2  # times validate sends a plan back before showing the best attempt
RECURSION_LIMIT = 2 * (MAX_TOOL_CALLS + MAX_REPLANS) + 10  # graph steps, a backstop

Runtime_ = Runtime[AgentContext]


def _write(runtime: Runtime_, event: dict[str, Any]) -> None:
    """Send an event to whoever is streaming this run (the SSE route)."""
    runtime.stream_writer(event)


# --- load_context ------------------------------------------------------------------


def _dangling_results(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """If the last turn was cut off after Claude asked for tools (a timeout, a crash),
    answer those calls now. The API rejects a history with unanswered tool calls."""
    if not messages or messages[-1]["role"] != "assistant":
        return []
    return [
        {
            "type": "tool_result",
            "tool_use_id": block["id"],
            "content": "Not run: the previous turn was interrupted.",
            "is_error": True,
        }
        for block in messages[-1]["content"]
        if block.get("type") == "tool_use"
    ]


async def load_context(state: AgentState, runtime: Runtime_) -> dict[str, Any]:
    agent = runtime.context
    reset: dict[str, Any] = {
        # Straight from approve with a chat message: this turn revises that Proposal.
        "revising": (state.get("decision") or {}).get("action") == "message",
        "tool_calls": 0,
        "replan_count": 0,
        "proposal": None,
        "decision": None,
        "pending_proposal": None,
        "pending_results": [],
        "stop": None,
    }
    async with agent.sessionmaker() as session:
        used = await token_budget.tokens_used_today(session, agent.household_id, agent.today)
        if used >= agent.daily_token_budget:
            _write(
                runtime,
                {
                    "type": "text",
                    "text": "You've reached today's planning limit. It resets tomorrow.",
                },
            )
            return {**reset, "stop": "budget"}
        draft = state.get("draft") or empty_draft()
        with tracing.observe("load-household-context", as_type="retriever") as obs:
            context = await prompt.household_context(session, agent, draft)
            obs.update(output=context)

    messages = []
    dangling = _dangling_results(state.get("messages", []))
    if dangling:
        messages.append({"role": "user", "content": dangling})
    messages.append(prompt.user_message(context, state.get("user_text", "")))
    return {**reset, "messages": messages, "draft": draft}


# --- agent -------------------------------------------------------------------------


async def agent(state: AgentState, runtime: Runtime_) -> dict[str, Any]:
    ctx = runtime.context
    with tracing.observe(
        tracing.GENERATION,
        as_type="generation",
        # What the model saw, in order: the fixed system prompt, then the history.
        input=[{"role": "system", "content": prompt.SYSTEM}, *state["messages"]],
        metadata={"tools": [t["name"] for t in tools.specs()]},
        model=ctx.model.name,
        model_parameters=dict(ctx.model.parameters),
    ) as generation:
        turn = await ctx.model.respond(
            prompt.SYSTEM,
            tools.specs(),
            state["messages"],
            on_text=lambda text: _write(runtime, {"type": "text", "text": text}),
        )
        usage, cost = turn.usage, cost_usd(turn.usage)
        generation.update(
            output=turn.content,  # text, tool calls and thinking blocks, as returned
            model=usage.model,  # who actually answered (a fallback can differ)
            usage_details={
                "input": usage.input_tokens,
                "output": usage.output_tokens,
                "cache_read_input_tokens": usage.cache_read_tokens,
                "cache_creation_input_tokens": usage.cache_write_tokens,
            },
            # Our own price table (app/llm_costs.py), so Langfuse and the evals agree.
            cost_details={"total": float(cost)} if cost is not None else None,
            metadata={"stop_reason": turn.stop_reason},
            level="WARNING" if turn.stop_reason in ("refusal", "max_tokens") else None,
        )
    async with ctx.sessionmaker() as session:
        await token_budget.add_usage(session, ctx.household_id, ctx.today, turn.usage)
        await session.commit()

    update: dict[str, Any] = {"messages": [{"role": "assistant", "content": turn.content}]}
    if turn.stop_reason == "refusal":
        _write(runtime, {"type": "text", "text": "Sorry, I can't help with that one."})
        update["stop"] = "refusal"
    elif turn.stop_reason == "max_tokens":
        update["stop"] = "max_tokens"
    return update


def _tool_uses(state: AgentState) -> list[dict[str, Any]]:
    last = state["messages"][-1]
    if last["role"] != "assistant":
        return []
    return [b for b in last["content"] if b.get("type") == "tool_use"]


def after_agent(state: AgentState) -> str:
    if state.get("stop"):
        return END
    if not _tool_uses(state):
        draft = state.get("draft") or empty_draft()
        has_plan = bool(draft["meals"] or draft["list_additions"])
        return "reshow" if state.get("revising") and has_plan else END
    return "tools"


# --- tools -------------------------------------------------------------------------


def _result(tool_use_id: str, content: Any, *, error: bool = False) -> dict[str, Any]:
    text = content if isinstance(content, str) else json.dumps(content, default=str)
    block: dict[str, Any] = {"type": "tool_result", "tool_use_id": tool_use_id, "content": text}
    if error:
        block["is_error"] = True
    return block


# Tools that only look something up: traced as `retriever`, the rest as `tool`.
LOOKUPS = frozenset(
    {
        "recipes_from_kitchen",
        "search_recipes",
        "get_recipe",
        "get_kitchen",
        "get_household_preferences",
        "get_shopping_list",
    }
)


@dataclass(frozen=True)
class ToolCall:
    """What one tool call produced: a result for the model, or (propose_plan) a
    hand-off to validate, and maybe a new Draft."""

    result: dict[str, Any] | None = None
    pending: dict[str, str] | None = None
    draft: Draft | None = None


async def _call_tool(ctx: AgentContext, draft: Draft, use: dict[str, Any], count: int) -> ToolCall:
    name, use_id = use["name"], use["id"]
    if count > MAX_TOOL_CALLS:
        message = "Tool limit reached for this turn. Propose or reply now."
        return ToolCall(_result(use_id, message, error=True))
    tool = tools.BY_NAME.get(name)
    if tool is None:
        return ToolCall(_result(use_id, f"Unknown tool {name!r}", error=True))
    try:
        args = tool.args.model_validate(use.get("input", {}))
    except ValidationError as error:
        # Tell the agent exactly what was wrong, so it can fix its call.
        problems = "; ".join(
            f"{'.'.join(map(str, e['loc'])) or 'input'}: {e['msg']}" for e in error.errors()
        )
        return ToolCall(_result(use_id, f"Invalid arguments: {problems}", error=True))
    if tool.run is None:  # propose_plan: validate answers it
        return ToolCall(pending={"tool_use_id": use_id, "summary": args.summary})  # type: ignore[attr-defined]
    async with ctx.sessionmaker() as session:
        call = Call(session, await tools.member_context(session, ctx), ctx, draft)
        try:
            outcome = await tool.run(call, args)
        except ToolError as error:
            return ToolCall(_result(use_id, str(error), error=True))
    return ToolCall(_result(use_id, outcome.result), draft=outcome.draft)


async def run_tools(state: AgentState, runtime: Runtime_) -> dict[str, Any]:
    ctx = runtime.context
    draft: Draft = state["draft"]
    count = state.get("tool_calls", 0)
    results: list[dict[str, Any]] = []
    pending: dict[str, str] | None = None

    for use in _tool_uses(state):
        count += 1
        name = use["name"]
        _write(runtime, {"type": "tool", "name": name})
        # One observation per call, a sibling of the generation that asked for it.
        with tracing.observe(
            name,
            as_type="retriever" if name in LOOKUPS else "tool",
            input=use.get("input", {}),
            metadata={"tool_use_id": use["id"]},
        ) as obs:
            done = await _call_tool(ctx, draft, use, count)
            if done.pending is not None:
                pending = done.pending
                obs.update(output="handed to validate-plan")
            elif done.result is not None and done.result.get("is_error"):
                obs.update(level="ERROR", status_message=str(done.result["content"])[:500])
            elif done.result is not None:
                obs.update(output=done.result["content"])
        if done.result is not None:
            results.append(done.result)
        if done.draft is not None:
            draft = done.draft
            _write(runtime, {"type": "draft", "draft": draft})

    update: dict[str, Any] = {"tool_calls": count, "draft": draft}
    if pending is not None:
        update["pending_proposal"] = pending
        update["pending_results"] = results
    else:
        update["messages"] = [{"role": "user", "content": results}]
    # Well past the limit and still calling tools: stop the turn.
    if count > MAX_TOOL_CALLS + 5:
        update["stop"] = "tool_limit"
    return update


def after_tools(state: AgentState) -> str:
    if state.get("pending_proposal"):
        return "validate"
    if state.get("stop"):
        return END
    return "agent"


# --- validate ----------------------------------------------------------------------


async def validate(state: AgentState, runtime: Runtime_) -> dict[str, Any]:
    ctx = runtime.context
    pending = state.get("pending_proposal")
    assert pending is not None
    draft = state["draft"]
    async with ctx.sessionmaker() as session:
        ids = [m["recipe_id"] for m in draft["meals"].values()]
        found = await recipes.get_many(session, ctx.household_id, ids)
        rules = await diet.get_rules(session, ctx.household_id)
        conversation = await session.get_one(Conversation, ctx.conversation_id)
        adapted, refused = await adaptations.for_draft(session, ctx.household_id, draft["meals"])
    with tracing.observe("validate-plan", as_type="guardrail", input=draft) as obs:
        problems = validate_draft(
            draft, found, rules, ctx.today, conversation.plan_days, adapted, refused
        )
        obs.update(
            output=[p.message for p in problems] or "passed",
            metadata={"replans_so_far": state.get("replan_count", 0)},
            level="WARNING" if problems else None,
        )
    replans = state.get("replan_count", 0)
    results = list(state.get("pending_results", []))
    update: dict[str, Any] = {"pending_proposal": None, "pending_results": []}

    if problems and replans < MAX_REPLANS:
        # Send it back with a precise list, like a code review.
        listed = "\n".join(f"- {p.message}" for p in problems)
        results.append(
            _result(
                pending["tool_use_id"], f"Not shown yet. Fix these first:\n{listed}", error=True
            )
        )
        _write(runtime, {"type": "replan", "problems": [p.message for p in problems]})
        return {
            **update,
            "messages": [{"role": "user", "content": results}],
            "replan_count": replans + 1,
        }

    if problems and all(p.kind == "empty" for p in problems):
        results.append(
            _result(pending["tool_use_id"], "Nothing to show: the plan is empty.", error=True)
        )
        return {**update, "messages": [{"role": "user", "content": results}], "stop": "empty"}

    proposal = await _show(
        state, runtime, draft, found, rules, problems, pending["summary"], adapted
    )
    results.append(_result(pending["tool_use_id"], "Shown to the Member. Wait for their reply."))
    return {
        **update,
        "messages": [{"role": "user", "content": results}],
        "proposal": proposal,
        "proposal_marks": [{"id": proposal["id"], "at": len(state["messages"])}],
        "revising": False,
    }


async def _show(
    state: AgentState,
    runtime: Runtime_,
    draft: Draft,
    found: Mapping[str, Recipe],
    rules: DietaryRules,
    problems: list[Problem],
    summary: str,
    adapted: Mapping[str, Recipe],
) -> dict[str, Any]:
    """Save the Draft as a Proposal and show it. Shared by validate and reshow."""
    ctx = runtime.context
    proposal = build_proposal(draft, found, rules, problems, summary, adapted)
    async with ctx.sessionmaker() as session:
        # Say on the card which days already have a dinner that this would replace.
        days = [date.fromisoformat(m["date"]) for m in proposal["meals"]]
        planned = (
            {
                pm.date.isoformat(): pm.recipe.title
                for pm in await meal_plan.between(session, ctx.household_id, min(days), max(days))
            }
            if days
            else {}
        )
        for meal in proposal["meals"]:
            meal["replaces"] = planned.get(meal["date"])
        # Say on the card how much of each addition is already on the list (ADR 0016).
        view = await shopping_lists.get_household_list(
            session, await tools.member_context(session, ctx)
        )
        proposal["list_additions"] = [
            {**a, "on_list": _on_list(view.items, a)}
            for a in explain_additions(
                proposal["list_additions"],
                # What each meal would cook: an adapted meal's lentils explain lentils.
                [
                    (m["date"], adapted.get(m["date"]) or found[m["recipe_id"]])
                    for m in proposal["meals"]
                ],
                # Only what the Member typed: the context and tool results may hold
                # planted text, so they can never explain an addition (slice 10).
                [line["text"] for line in prompt.transcript(state) if line["role"] == "user"],
                await ingredients.names(
                    session, [a["ingredient_id"] for a in proposal["list_additions"]]
                ),
            )
        ]
        row = await proposals.create(
            session, ctx.conversation_id, ctx.household_id, ctx.member_id, proposal
        )
        await session.commit()
    proposal = {**proposal, "id": str(row.id), "status": row.status.value}
    _write(runtime, {"type": "proposal", "proposal": proposal})
    return proposal


RESHOW_SUMMARY = "Here's the plan again, unchanged."


async def reshow(state: AgentState, runtime: Runtime_) -> dict[str, Any]:
    """The Member chatted about a Proposal (superseding it) and the agent answered
    without proposing again, e.g. "Wednesday is already vegetarian". Show the Draft
    again so there's always a plan to approve. Plain code, no model call, and the same
    checks as validate: anything that now breaks a Rule is left out and listed."""
    ctx = runtime.context
    draft = state["draft"]
    async with ctx.sessionmaker() as session:
        ids = [m["recipe_id"] for m in draft["meals"].values()]
        found = await recipes.get_many(session, ctx.household_id, ids)
        rules = await diet.get_rules(session, ctx.household_id)
        conversation = await session.get_one(Conversation, ctx.conversation_id)
        adapted, refused = await adaptations.for_draft(session, ctx.household_id, draft["meals"])
    with tracing.observe("reshow-plan", as_type="guardrail", input=draft) as obs:
        problems = validate_draft(
            draft, found, rules, ctx.today, conversation.plan_days, adapted, refused
        )
        obs.update(output=[p.message for p in problems] or "passed")
    proposal = await _show(state, runtime, draft, found, rules, problems, RESHOW_SUMMARY, adapted)
    return {
        "proposal": proposal,
        "proposal_marks": [{"id": proposal["id"], "at": len(state["messages"])}],
        "revising": False,
    }


def after_reshow(state: AgentState) -> str:
    return "approve" if state.get("proposal") is not None else END


def _on_list(items: Any, addition: dict[str, Any]) -> str | None:
    iid = addition.get("ingredient_id")
    found = shopping_lists.unticked_match(items, uuid.UUID(iid) if iid else None, addition["name"])
    return shopping_lists.amount_text(found.quantity, found.unit) if found else None


def after_validate(state: AgentState) -> str:
    if state.get("proposal") is not None:
        return "approve"
    if state.get("stop"):
        return END
    return "agent"


# --- approve and commit ----------------------------------------------------------------


async def approve(state: AgentState, runtime: Runtime_) -> dict[str, Any]:
    """Pause until the Member answers. `interrupt()` saves the graph and stops the run;
    resuming with `Command(resume=answer)` runs this node again from the top, and this
    time `interrupt()` returns the answer. So nothing before it may have side effects."""
    proposal = state.get("proposal")
    assert proposal is not None
    decision: dict[str, Any] = interrupt({"proposal_id": proposal["id"]})

    ctx = runtime.context
    action = decision["action"]
    if action == "approve":
        return {"decision": decision}  # commit does the work
    status = ProposalStatus.REJECTED if action == "reject" else ProposalStatus.SUPERSEDED
    async with ctx.sessionmaker() as session:
        await proposals.close_pending(
            session, ctx.conversation_id, status, ctx.member_id, uuid.UUID(proposal["id"])
        )
        await session.commit()
    update: dict[str, Any] = {"decision": decision, "proposal": None}
    if action == "message":
        update["user_text"] = decision["text"]  # carry on with what they typed
    return update


def after_approve(state: AgentState) -> str:
    action = (state.get("decision") or {}).get("action")
    if action == "approve":
        return "commit"
    if action == "message":
        return "load_context"
    return END


async def commit(state: AgentState, runtime: Runtime_) -> dict[str, Any]:
    """Plain code from here on (ADR 0005): the same services the REST API uses, under the
    approving Member's permissions, in one transaction. Safe to run twice: the second
    time `proposals.commit` sees it's already approved and returns the stored outcome."""
    ctx = runtime.context
    decision = state.get("decision") or {}
    proposal = state.get("proposal")
    assert proposal is not None
    with tracing.observe(
        "save-approved-plan",
        input={k: decision.get(k) for k in ("keep_meals", "keep_additions")},
        metadata={"proposal_id": proposal["id"]},
    ) as obs:
        async with ctx.sessionmaker() as session:
            member = await tools.member_context(session, ctx)
            outcome = await proposals.commit(
                session,
                member,
                uuid.UUID(proposal["id"]),
                decision.get("keep_meals"),
                decision.get("keep_additions"),
                ctx.today,
            )
            await session.commit()
        # Stored on the Proposal; the decision route reads it from there.
        obs.update(output=outcome)
    # The plan is Household data now; the next request starts a fresh Draft.
    return {"draft": empty_draft(), "proposal": None, "decision": None}


def after_load(state: AgentState) -> str:
    return END if state.get("stop") else "agent"


def build(checkpointer: Checkpointer) -> CompiledStateGraph[AgentState, AgentContext, Any, Any]:
    graph = StateGraph(AgentState, context_schema=AgentContext)
    graph.add_node("load_context", load_context)
    graph.add_node("agent", agent)
    graph.add_node("tools", run_tools)
    graph.add_node("validate", validate)
    graph.add_node("reshow", reshow)
    graph.add_node("approve", approve)
    graph.add_node("commit", commit)
    graph.add_edge(START, "load_context")
    graph.add_conditional_edges("load_context", after_load)
    graph.add_conditional_edges("agent", after_agent)
    graph.add_conditional_edges("tools", after_tools)
    graph.add_conditional_edges("validate", after_validate)
    graph.add_conditional_edges("reshow", after_reshow)
    graph.add_conditional_edges("approve", after_approve)
    graph.add_edge("commit", END)
    return graph.compile(checkpointer=checkpointer)
