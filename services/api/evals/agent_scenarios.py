"""The agent Scenarios (slice 8): what we expect the planning agent to get right.

Each Scenario is a starting Household, what the Member says (or decides), and the
must-pass checks on top of the defaults every Scenario gets (no crash, grounded,
follows Dietary Rules, only the chosen days). Measures are taken for all of them.

Messages use the app's own words where the app writes them: "Plan my week" sends
"Plan new recipes to shop for, for {days}." and "Just tonight" sends a fixed question
(apps/client/src/features/chat/starters.ts). Days are offsets from today, from 1
(tomorrow), so a run late in the evening doesn't plan for a day that's nearly over.

Prompt injection Scenarios wait for slice 10 (AI security).
"""

from dataclasses import dataclass
from decimal import Decimal

from app.data.diet import Diet
from app.models import PlanMode
from evals.agent_graders import (
    DEFAULT_CHECKS,
    Check,
    called,
    changed_only_day,
    final_status,
    meal_count,
    nothing_dropped,
    on_today,
    on_weekdays,
    proposal_made,
    revised_after_reject,
    uses_kitchen_item,
)
from evals.agent_harness import Approve, Reject, Say, Setup, Step
from evals.kitchen_first import KITCHENS


@dataclass(frozen=True)
class Scenario:
    name: str
    about: str
    setup: Setup
    steps: tuple[Step, ...]
    checks: tuple[Check, ...] = ()

    @property
    def all_checks(self) -> tuple[Check, ...]:
        return DEFAULT_CHECKS + self.checks

    @property
    def single_message(self) -> bool:
        """One message and nothing else: the Baseline Planner can try it too (8b)."""
        return len(self.steps) == 1 and isinstance(self.steps[0], Say)


def kitchen(name: str) -> dict[str, Decimal | None]:
    """A hand-written Kitchen from the 5c eval; every item "some" (no quantity)."""
    return {item: None for item in KITCHENS[name]}


WEEK = (1, 2, 3, 4, 5)
NEW_PLAN = Say("Plan new recipes to shop for, for {days}.")
KITCHEN_PLAN = Say("Plan dinners from what's in my Kitchen, for {days}.")
TONIGHT = Say("What can I cook tonight with what's in my Kitchen?")
A_PLAN = (proposal_made, nothing_dropped)

SCENARIOS: tuple[Scenario, ...] = (
    # --- Plain planning --------------------------------------------------------------
    Scenario(
        "week-new-recipes",
        "Plan my week, New recipes, five days, a well-stocked Kitchen.",
        Setup(kitchen=kitchen("after a big shop"), mode=PlanMode.NEW, days=WEEK),
        (NEW_PLAN,),
        (*A_PLAN, meal_count(5)),
    ),
    Scenario(
        "week-from-kitchen",
        "Plan my week, Cook from my Kitchen: should rank by the Kitchen.",
        Setup(kitchen=kitchen("after a big shop"), mode=PlanMode.KITCHEN, days=WEEK),
        (KITCHEN_PLAN,),
        (*A_PLAN, meal_count(5), called("recipes_from_kitchen")),
    ),
    Scenario(
        "just-tonight",
        "Just tonight: one dinner, today, from the Kitchen.",
        Setup(kitchen=kitchen("after a big shop")),
        (TONIGHT,),
        (*A_PLAN, meal_count(1), on_today, called("recipes_from_kitchen")),
    ),
    Scenario(
        "weekend-typed",
        "A free-text request naming days, with no sheet: the agent works out the dates.",
        Setup(kitchen=kitchen("end of the week")),
        (Say("Plan dinners for this Saturday and Sunday, under 40 minutes each."),),
        (*A_PLAN, meal_count(2), on_weekdays("Saturday", "Sunday")),
    ),
    # --- Dietary Rules -----------------------------------------------------------------
    Scenario(
        "gluten-free-week",
        "Gluten free Household, four new dinners.",
        Setup(diets=frozenset({Diet.GLUTEN_FREE}), mode=PlanMode.NEW, days=(1, 2, 3, 4)),
        (NEW_PLAN,),
        (*A_PLAN, meal_count(4)),
    ),
    Scenario(
        "vegan-with-eggs-in-the-kitchen",
        "Vegan Household whose Kitchen still has eggs and feta: don't be tempted.",
        Setup(
            diets=frozenset({Diet.VEGAN}),
            kitchen=kitchen("vegetarian"),
            mode=PlanMode.KITCHEN,
            days=(1, 2, 3),
        ),
        (KITCHEN_PLAN,),
        (*A_PLAN, meal_count(3)),
    ),
    Scenario(
        "thai-without-peanuts",
        "Loves Thai (a Preference) but peanuts are excluded (a Rule): the Rule wins.",
        Setup(excluded=("peanuts",), cuisines=("thai",), mode=PlanMode.NEW, days=(1, 2, 3)),
        (NEW_PLAN,),
        (*A_PLAN, meal_count(3)),
    ),
    Scenario(
        "steak-night-for-vegetarians",
        "The Member asks for something their own Rules forbid. Only Rule-safe meals.",
        Setup(diets=frozenset({Diet.VEGETARIAN}), mode=PlanMode.NEW, days=(1, 2)),
        (Say("Plan new recipes to shop for, for {days}. We'd love a steak night on {0}."),),
        (proposal_made,),
    ),
    # --- The Kitchen -------------------------------------------------------------------
    Scenario(
        "use-up-the-chicken",
        "Cook from my Kitchen, and the Member names something to use up.",
        Setup(kitchen=kitchen("after a big shop"), mode=PlanMode.KITCHEN, days=(1, 2, 3)),
        (
            Say(
                "Plan dinners from what's in my Kitchen, for {days}. "
                "Make sure we use up the chicken thigh."
            ),
        ),
        (*A_PLAN, meal_count(3), uses_kitchen_item("chicken thigh")),
    ),
    Scenario(
        "nearly-empty-kitchen",
        "Cook from my Kitchen with almost nothing in it: still plan, and shop for the rest.",
        Setup(kitchen=kitchen("nearly empty"), mode=PlanMode.KITCHEN, days=(1, 2)),
        (KITCHEN_PLAN,),
        (*A_PLAN, meal_count(2)),
    ),
    Scenario(
        "asian-pantry",
        "Cook from my Kitchen with an Asian pantry: should rank by the Kitchen.",
        Setup(kitchen=kitchen("asian pantry"), mode=PlanMode.KITCHEN, days=(1, 2, 3)),
        (KITCHEN_PLAN,),
        (*A_PLAN, meal_count(3), called("recipes_from_kitchen")),
    ),
    # --- Follow-ups ----------------------------------------------------------------
    Scenario(
        "swap-one-day-then-approve",
        "After the Proposal, swap the second day only, then approve.",
        Setup(kitchen=kitchen("after a big shop"), mode=PlanMode.NEW, days=(1, 2, 3)),
        (NEW_PLAN, Say("Swap {1} for something vegetarian, keep the rest."), Approve()),
        (*A_PLAN, meal_count(3), changed_only_day(1), final_status("approved")),
    ),
    Scenario(
        "reject-then-quicker",
        "The Member rejects the plan, then asks for something quicker.",
        Setup(mode=PlanMode.NEW, days=(1, 2)),
        (NEW_PLAN, Reject(), Say("Can you do quicker ones? Under 30 minutes.")),
        (*A_PLAN, revised_after_reject, meal_count(2)),
    ),
    # --- Awkward -------------------------------------------------------------------
    Scenario(
        "vegan-steak",
        "Vegan Household asks for steak and nothing else: no meat, whatever happens.",
        Setup(diets=frozenset({Diet.VEGAN}), mode=PlanMode.NEW, days=(1,)),
        (Say("Plan new recipes to shop for, for {days}. Steak, please."),),
        (),
    ),
    Scenario(
        "search-outage",
        "Recipe search fails twice (a Voyage outage): recover and still plan.",
        Setup(mode=PlanMode.NEW, days=(1, 2), embedder_failures=2),
        (NEW_PLAN,),
        (*A_PLAN, meal_count(2)),
    ),
)

BY_NAME = {s.name: s for s in SCENARIOS}
