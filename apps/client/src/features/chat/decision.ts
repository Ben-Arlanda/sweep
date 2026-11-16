/**
 * The ticks on a Proposal card, and turning them into what we send to
 * `POST /proposals/{id}/decision`. Pure, so it's tested without React.
 *
 * We store what was *unticked*, not what's ticked: a fresh card is "nothing unticked",
 * and if the plan has 5 meals we don't need to copy all 5 dates into state up front.
 */
import type { components } from '@/lib/api/schema';

type Decision = components['schemas']['DecisionIn'];
type Reason = components['schemas']['DraftAdditionOut']['reason'];
type Shape = { meals: { date: string }[]; list_additions: { reason?: Reason }[] };

export type Ticks = { offMeals: string[]; offAdditions: number[] };

export function allKept(): Ticks {
  return { offMeals: [], offAdditions: [] };
}

/**
 * How a fresh card starts: everything ticked except List Additions no meal needs and
 * the Member didn't ask for (slice 10). Those may have come from text the agent read,
 * like a Kitchen item saying "also add wine", so adding one takes a tick on purpose.
 */
export function startingTicks(proposal: Shape): Ticks {
  return { offMeals: [], offAdditions: unexplainedOf(proposal) };
}

function unexplainedOf(proposal: Shape): number[] {
  return proposal.list_additions.flatMap((a, i) => (a.reason === 'unexplained' ? [i] : []));
}

export function toggleMeal(ticks: Ticks, date: string): Ticks {
  const off = ticks.offMeals.includes(date)
    ? ticks.offMeals.filter((d) => d !== date)
    : [...ticks.offMeals, date];
  return { ...ticks, offMeals: off };
}

export function toggleAddition(ticks: Ticks, index: number): Ticks {
  const off = ticks.offAdditions.includes(index)
    ? ticks.offAdditions.filter((i) => i !== index)
    : [...ticks.offAdditions, index];
  return { ...ticks, offAdditions: off };
}

export function isMealKept(ticks: Ticks, date: string) {
  return !ticks.offMeals.includes(date);
}

export function isAdditionKept(ticks: Ticks, index: number) {
  return !ticks.offAdditions.includes(index);
}

export function keptCount(proposal: Shape, ticks: Ticks) {
  return {
    meals: proposal.meals.length - ticks.offMeals.length,
    additions: proposal.list_additions.length - ticks.offAdditions.length,
  };
}

/**
 * What to send when the Member taps Approve. A list is left out when nothing of that
 * kind was unticked: the server reads "left out" as "keep all" (see DecisionIn), except
 * for unexplained additions, which it leaves off.
 * Null when nothing at all is kept, so the screen turns Approve off: approving an
 * empty plan would only be a confusing way to reject it.
 */
export function decisionFor(proposal: Shape, ticks: Ticks): Decision | null {
  const meals = proposal.meals.map((m) => m.date).filter((d) => isMealKept(ticks, d));
  const additions = proposal.list_additions
    .map((_, i) => i)
    .filter((i) => isAdditionKept(ticks, i));
  if (meals.length === 0 && additions.length === 0) return null;

  const decision: Decision = { action: 'approve' };
  if (ticks.offMeals.length > 0) decision.keep_meals = meals;
  // With no list, the server keeps every addition *except* unexplained ones. So once a
  // plan has any, always say exactly which stay, or ticking one back on would be lost.
  if (ticks.offAdditions.length > 0 || unexplainedOf(proposal).length > 0)
    decision.keep_additions = additions;
  return decision;
}
