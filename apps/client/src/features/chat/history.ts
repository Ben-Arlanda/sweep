/**
 * The saved chat, with every Proposal back where it happened (6a returns each one with
 * `after_line`: how many transcript lines came before it). Pure, so it's tested alone.
 */
import type { components } from '@/lib/api/schema';

type Line = { role: 'user' | 'assistant'; text: string };
type Placed = { after_line: number | null };
type Status = components['schemas']['ProposalStatus'];
type Outcome = components['schemas']['ProposalOutcomeOut'];

export type HistoryItem<P> =
  { kind: 'line'; line: Line; index: number } | { kind: 'proposal'; proposal: P };

export function placeProposals<P extends Placed>(lines: Line[], proposals: P[]): HistoryItem<P>[] {
  // A place we can't show (unknown, or past the end of the transcript) goes last.
  const slot = (p: P) =>
    p.after_line !== null && p.after_line <= lines.length ? p.after_line : lines.length;
  const out: HistoryItem<P>[] = [];
  for (let i = 0; i <= lines.length; i++) {
    for (const proposal of proposals)
      if (slot(proposal) === i) out.push({ kind: 'proposal', proposal });
    if (i < lines.length) out.push({ kind: 'line', line: lines[i], index: i });
  }
  return out;
}

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/** One line for a plan that's no longer waiting: "Approved · 3 meals saved". */
export function statusLine(p: { status: Status; outcome?: Outcome | null }): string {
  switch (p.status) {
    case 'approved': {
      const o = p.outcome;
      if (!o) return 'Approved';
      const parts = [
        o.saved_meals > 0 ? `${plural(o.saved_meals, 'meal', 'meals')} saved` : null,
        o.added_items > 0 ? `${plural(o.added_items, 'item', 'items')} added` : null,
      ].filter(Boolean);
      return parts.length ? `Approved · ${parts.join(', ')}` : 'Approved';
    }
    case 'rejected':
      return 'Rejected';
    case 'superseded':
      return 'Replaced by a newer plan';
    case 'expired':
      return 'Expired';
    case 'pending':
      return 'Waiting for you';
  }
}

/**
 * What a plan kept. Once approved, only what the Member left ticked (6b records it on
 * the outcome); otherwise, or on outcomes from before that, everything it proposed.
 * Additions keep their position, since that's what the server counts by.
 */
export function keptOf<M extends { date: string }, A>(p: {
  status: Status;
  meals: M[];
  list_additions: A[];
  outcome?: Outcome | null;
}): { meals: M[]; additions: { item: A; index: number }[] } {
  const keptMeals = p.status === 'approved' ? p.outcome?.kept_meals : null;
  const keptAdditions = p.status === 'approved' ? p.outcome?.kept_additions : null;
  return {
    meals: keptMeals ? p.meals.filter((m) => keptMeals.includes(m.date)) : p.meals,
    additions: p.list_additions
      .map((item, index) => ({ item, index }))
      .filter(({ index }) => !keptAdditions || keptAdditions.includes(index)),
  };
}
