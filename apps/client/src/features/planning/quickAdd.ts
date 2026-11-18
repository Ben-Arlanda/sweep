/**
 * "Add to shopping list" on a plan's things to buy, before the plan is approved.
 * Approving also adds them, as extra on top of the list, so whatever was quick-added
 * is left out of the approval: otherwise 800 g of tomatoes would become 1.6 kg.
 */
import { allKept, isAdditionKept, type Ticks } from '@/features/chat/decision';
import { formatAmount } from '@/features/kitchen/format';

type Addition = {
  name: string;
  quantity: number | null;
  unit: string | null;
  reason?: 'meal' | 'asked' | 'unexplained' | null;
};
type Shape = { meals: { date: string }[]; list_additions: Addition[] };

/** "800 g canned tomatoes": what goes on the list, and how we remember it was added. */
export function additionText(a: Addition): string {
  if (a.quantity === null) return a.name;
  return `${formatAmount(String(a.quantity), a.unit ?? '')} ${a.name}`;
}

/** What the button would add: the plan's additions (not unexplained ones), not yet added. */
export function toAdd(plan: Shape, added: string[]): string[] {
  return plan.list_additions
    .filter((_, i) => isAdditionKept(plan, allKept(), i))
    .map(additionText)
    .filter((text) => !added.includes(text));
}

/** The ticks for Approve: every addition that was already quick-added, unticked. */
export function approveTicks(plan: Shape, added: string[]): Ticks {
  const changedAdditions = plan.list_additions
    .map((a, i) => (isAdditionKept(plan, allKept(), i) && added.includes(additionText(a)) ? i : -1))
    .filter((i) => i >= 0);
  return { ...allKept(), changedAdditions };
}
