/**
 * Changing the cached Kitchen straight away, before the server answers, so a deleted row
 * disappears the moment you let go. Plain functions, like the list's listCache.ts.
 */
type Row = { ingredient: { id: string } };

/** The Kitchen without one item (Tracked or Staple). Never changes the one passed in. */
export function withoutItem<K extends { tracked: readonly Row[]; staples: readonly Row[] }>(
  kitchen: K,
  ingredientId: string,
): K {
  return {
    ...kitchen,
    tracked: kitchen.tracked.filter((i) => i.ingredient.id !== ingredientId),
    staples: kitchen.staples.filter((i) => i.ingredient.id !== ingredientId),
  };
}
