/**
 * Used up / Ran out (pure parts): what the Kitchen says afterwards, and what Undo puts back.
 *
 * Saying something's gone takes it out of the Kitchen and puts it on the Shopping List in
 * one step (most households plan only dinners, so this is how breakfast use is caught).
 * Undo is inline and has no timer (WCAG 2.2.1), so it must be able to restore everything.
 */
import { displayName } from './format';
import type { Place } from './places';

export type Gone = {
  ingredientId: string;
  name: string;
  kind: 'tracked' | 'staple';
  quantity: string | null; // a Tracked item's amount before (null: "some")
  place: Place;
  listId: string;
  listItemId: string | null; // null: it was already on the list
};

export type UndoStep =
  | { do: 'setAmount'; ingredientId: string; quantity: string | null }
  | { do: 'setPlace'; ingredientId: string; place: Place }
  | { do: 'have'; ingredientId: string }
  | { do: 'removeFromList'; listId: string; itemId: string };

export function goneText(gone: Gone): string {
  const name = displayName(gone.name);
  if (gone.kind === 'tracked') {
    return gone.listItemId
      ? `${name} used up, and on your list`
      : `${name} used up. It was already on your list`;
  }
  return gone.listItemId
    ? `${name} ran out, and is on your list`
    : `${name} ran out. It was already on your list`;
}

export function undoSteps(gone: Gone): UndoStep[] {
  const { ingredientId } = gone;
  const steps: UndoStep[] =
    gone.kind === 'tracked'
      ? [
          { do: 'setAmount', ingredientId, quantity: gone.quantity },
          { do: 'setPlace', ingredientId, place: gone.place },
        ]
      : [{ do: 'have', ingredientId }];
  if (gone.listItemId)
    steps.push({ do: 'removeFromList', listId: gone.listId, itemId: gone.listItemId });
  return steps;
}
