/**
 * The ticks on a Proposal card, and turning them into what we send to
 * `POST /proposals/{id}/decision`. Pure, so it's tested without React.
 *
 * We store only what the Member *changed*, never the ticks themselves. Each row's
 * starting tick comes from the plan the card has right now: meals and additions start
 * ticked, except unexplained additions (slice 10). So if a fresh copy of the plan
 * arrives after the card first drew from a cached one, the ticks follow it, and a
 * "Not for any meal" row can never show a tick the Member didn't give it.
 */
import type { components } from '@/lib/api/schema';

type Decision = components['schemas']['DecisionIn'];
type Reason = components['schemas']['DraftAdditionOut']['reason'];
type Shape = { meals: { date: string }[]; list_additions: { reason?: Reason }[] };

export type Ticks = { offMeals: string[]; changedAdditions: number[] };

export function allKept(): Ticks {
  return { offMeals: [], changedAdditions: [] };
}

/**
 * Additions start ticked unless no meal needs them and the Member didn't ask for them.
 * Those may have come from text the agent read (a Kitchen item saying "also add
 * wine"), so adding one takes a tick on purpose.
 */
function startsTicked(proposal: Shape, index: number) {
  return proposal.list_additions[index]?.reason !== 'unexplained';
}

function hasUnexplained(proposal: Shape) {
  return proposal.list_additions.some((a) => a.reason === 'unexplained');
}

const flip = <T>(list: T[], value: T) =>
  list.includes(value) ? list.filter((v) => v !== value) : [...list, value];

export function toggleMeal(ticks: Ticks, date: string): Ticks {
  return { ...ticks, offMeals: flip(ticks.offMeals, date) };
}

export function toggleAddition(ticks: Ticks, index: number): Ticks {
  return { ...ticks, changedAdditions: flip(ticks.changedAdditions, index) };
}

export function isMealKept(ticks: Ticks, date: string) {
  return !ticks.offMeals.includes(date);
}

export function isAdditionKept(proposal: Shape, ticks: Ticks, index: number) {
  return startsTicked(proposal, index) !== ticks.changedAdditions.includes(index);
}

function keptAdditions(proposal: Shape, ticks: Ticks) {
  return proposal.list_additions.map((_, i) => i).filter((i) => isAdditionKept(proposal, ticks, i));
}

export function keptCount(proposal: Shape, ticks: Ticks) {
  return {
    meals: proposal.meals.length - ticks.offMeals.length,
    additions: keptAdditions(proposal, ticks).length,
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
  const additions = keptAdditions(proposal, ticks);
  if (meals.length === 0 && additions.length === 0) return null;

  const decision: Decision = { action: 'approve' };
  if (ticks.offMeals.length > 0) decision.keep_meals = meals;
  // With no list, the server keeps every addition *except* unexplained ones. So once a
  // plan has any, always say exactly which stay, or ticking one back on would be lost.
  if (additions.length < proposal.list_additions.length || hasUnexplained(proposal))
    decision.keep_additions = additions;
  return decision;
}
