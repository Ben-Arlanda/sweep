import type { components } from '@/lib/api/schema';

type ListItem = components['schemas']['ItemOut'];

/**
 * The Ingredients waiting on the Shopping List (unticked): the Kitchen's "+ List" shows
 * "On list" for them. Same rule as the recipe screen and the planner (ADR 0016).
 */
export function onListIds(items: ListItem[] | undefined): Set<string> {
  return new Set(
    (items ?? []).filter((i) => !i.checked && i.ingredient).map((i) => i.ingredient!.id),
  );
}
