/**
 * The Generating screen's checklist (slice 6e): the agent's tool calls, as it streams,
 * turned into a few friendly steps. Pure, so it's tested without React or a network.
 *
 * Each step is done once the agent has moved past it: a later step's tool was called,
 * or the plan arrived. The step it's on now is "active"; the rest "waiting".
 */

export type StepState = 'done' | 'active' | 'waiting';
export type Step = { label: string; state: StepState };

/** Week plans: Kitchen, recipes for the days, then the Shopping List. */
export const WEEK_STEPS = [
  'Checking your Kitchen',
  'Matching recipes to your days',
  'Building your Shopping List',
] as const;

/** A tweak to tonight's ideas: Kitchen, then recipes, then the plan's checks. */
export const TONIGHT_STEPS = [
  'Checking your Kitchen',
  'Applying your Dietary Rules',
  'Finding recipe matches',
] as const;

// Which step each tool belongs to. Anything unknown counts as the first.
const STEP_OF: Record<string, number> = {
  get_kitchen: 0,
  get_household_preferences: 0,
  get_shopping_list: 0,
  recipes_from_kitchen: 1,
  search_recipes: 1,
  get_recipe: 1,
  set_planned_meal: 1,
  remove_planned_meal: 1,
  adapt_recipe: 1,
  check_kitchen_coverage: 2,
  set_list_additions: 2,
  propose_plan: 2,
};

/** `tools`: the tool names called so far this turn. `finished`: the plan has arrived. */
export function stepsFor(labels: readonly string[], tools: string[], finished: boolean): Step[] {
  const reached = finished
    ? labels.length
    : Math.min(labels.length - 1, Math.max(0, ...tools.map((name) => STEP_OF[name] ?? 0)));
  return labels.map((label, i) => ({
    label,
    state: i < reached ? 'done' : i === reached ? 'active' : 'waiting',
  }));
}
