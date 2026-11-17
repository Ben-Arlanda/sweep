"""What the agent remembers between steps (and between turns, via the checkpointer).

Everything here is plain JSON (strings, numbers, lists, dicts) so a checkpoint saved in
Postgres today still loads after the code changes. Ids are strings for the same reason.
"""

import operator
from typing import Annotated, Any, NotRequired, TypedDict


class DraftSwap(TypedDict):
    position: int  # which of the parent's lines it replaces
    raw_text: str  # the new line, as the model wrote it


class DraftAdaptation(TypedDict):
    """A Recipe Adaptation proposed for one meal (ADR 0021). Not saved until approved:
    validate and commit rebuild it from the parent and run the Swap checks each time."""

    label: str  # "with lentils"
    swaps: list[DraftSwap]


class DraftMeal(TypedDict):
    recipe_id: str  # with `adaptation`: the parent recipe
    servings: int
    # A copy for showing the Draft as it grows. The Proposal reads titles fresh.
    title: NotRequired[str]
    adaptation: NotRequired[DraftAdaptation]


class DraftAddition(TypedDict):
    name: str
    quantity: float | None
    unit: str | None
    ingredient_id: str | None  # set when the name matched an Ingredient


class Draft(TypedDict):
    """The Draft Plan: work in progress, visible to the Member, not Household data yet."""

    meals: dict[str, DraftMeal]  # ISO date → meal
    list_additions: list[DraftAddition]


def empty_draft() -> Draft:
    return Draft(meals={}, list_additions=[])


class AgentState(TypedDict):
    # The conversation in the Claude API's own shape. Append-only: earlier messages are
    # never edited, because Claude's thinking blocks are only valid against the exact
    # history they were written after.
    messages: Annotated[list[dict[str, Any]], operator.add]
    draft: Draft
    # Set by load_context for one turn: what the Member just typed.
    user_text: NotRequired[str]
    # Tool results held back until validate adds propose_plan's result, so every result
    # for one assistant message goes back in a single user message.
    pending_results: NotRequired[list[dict[str, Any]]]
    pending_proposal: NotRequired[dict[str, str] | None]  # {tool_use_id, summary}
    # The Proposal being shown (with its id, from the proposals table), while it waits.
    proposal: NotRequired[dict[str, Any] | None]
    # What the Member answered, handed in when the paused graph is resumed:
    # {"action": "approve", "keep_meals", "keep_additions"} | {"action": "reject"}
    # | {"action": "message", "text"} (they chatted instead of deciding).
    decision: NotRequired[dict[str, Any] | None]
    # Where each Proposal sits in the chat: {"id", "at": how many messages came before}.
    # Append-only like `messages`, so the chat history can show every Proposal in place.
    proposal_marks: Annotated[list[dict[str, Any]], operator.add]
    # This turn answers a Proposal the Member chatted about instead of deciding (it was
    # superseded). Such a turn must end with a Proposal again: see graph.reshow.
    revising: NotRequired[bool]
    replan_count: NotRequired[int]
    tool_calls: NotRequired[int]
    stop: NotRequired[str | None]  # why this turn ended early, if it did
