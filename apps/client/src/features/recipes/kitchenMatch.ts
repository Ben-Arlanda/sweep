/**
 * Does the Kitchen have what a recipe needs? Plain functions, so they're easy to test.
 *
 * Both sides use the same Ingredient ids and the same base units (g / ml / count), which
 * is the whole reason recipes, lists and the Kitchen share one Ingredient list. The
 * server sends recipe amounts already converted (`base_quantity`), so comparing is just
 * comparing numbers. No unit maths happens in the app.
 */
import { formatAmount } from '@/features/kitchen/format';
import type { components } from '@/lib/api/schema';

type Line = components['schemas']['RecipeIngredientOut'];
type Kitchen = components['schemas']['KitchenOut'];
type ListItem = components['schemas']['ItemOut'];

export type Have =
  | { kind: 'have' }
  | { kind: 'low'; have: string } // there's some, less than the recipe needs
  | { kind: 'check' } // in the Kitchen, but the amount is too old to trust
  | { kind: 'need' }
  | { kind: 'onList' }; // not at home, but unticked on the Shopping List (will be bought)

/**
 * null: the line has no Ingredient (water, or not recognised), so we can't say.
 *
 * With the Shopping List, something you need or are low on that's already unticked on
 * the list is "on list", the same rule the planner uses (ADR 0016): it's covered, so
 * there's nothing more to buy.
 */
export function matchLine(line: Line, kitchen: Kitchen, list?: ListItem[]): Have | null {
  const id = line.ingredient?.id;
  if (!id) return null;
  const have = matchKitchen(id, line, kitchen);
  const onList = list?.some((i) => !i.checked && i.ingredient?.id === id);
  return onList && (have.kind === 'need' || have.kind === 'low') ? { kind: 'onList' } : have;
}

function matchKitchen(id: string, line: Line, kitchen: Kitchen): Have {
  const staple = kitchen.staples.find((s) => s.ingredient.id === id);
  if (staple) return staple.have ? { kind: 'have' } : { kind: 'need' };

  const item = kitchen.tracked.find((i) => i.ingredient.id === id);
  if (!item || item.stock === 'out') return { kind: 'need' }; // Out stays listed (ADR 0024)
  if (item.status === 'unknown') return { kind: 'check' };
  // "Some" (no amount recorded), or a recipe amount that doesn't convert ("3 cloves"):
  // we can't compare, and having it at all is the useful answer.
  if (item.quantity === null || line.base_quantity === null) return { kind: 'have' };
  if (Number(item.quantity) >= Number(line.base_quantity)) return { kind: 'have' };
  return { kind: 'low', have: formatAmount(item.quantity, item.unit) };
}

/**
 * What the + on a "Need" pill adds to the list: "30 g butter", "2 tomatoes", or just
 * "salt" when the amount doesn't convert. The list reads the amount back out of the
 * text, and the Ingredient's own name (not "tomatoes, sliced") links it to the Kitchen.
 */
export function addText(line: Line): string {
  const name = line.ingredient?.name ?? line.raw_text;
  if (!line.ingredient || line.base_quantity === null) return name;
  return `${formatAmount(line.base_quantity, line.ingredient.default_unit)} ${name}`;
}

/** "You have 6 of 9": counts lines with an Ingredient, leaving out optional ones. */
export function haveSummary(lines: Line[], kitchen: Kitchen) {
  const counted = lines.filter((l) => l.ingredient && !l.optional);
  const have = counted.filter((l) => matchLine(l, kitchen)?.kind === 'have').length;
  return { have, total: counted.length };
}

export function minutesText(minutes: number | null): string | null {
  if (minutes === null) return null;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m} min`;
  return m === 0 ? `${h} h` : `${h} h ${m} min`;
}

export function cuisineName(cuisine: string | null): string | null {
  if (!cuisine) return null;
  return cuisine
    .split('-')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}
