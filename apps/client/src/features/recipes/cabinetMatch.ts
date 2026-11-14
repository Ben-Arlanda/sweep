/**
 * Does the Cabinet have what a recipe needs? Plain functions, so they're easy to test.
 *
 * Both sides use the same Ingredient ids and the same base units (g / ml / count), which
 * is the whole reason recipes, lists and the Cabinet share one Ingredient list. The
 * server sends recipe amounts already converted (`base_quantity`), so comparing is just
 * comparing numbers. No unit maths happens in the app.
 */
import { formatAmount } from '@/features/cabinet/format';
import type { components } from '@/lib/api/schema';

type Line = components['schemas']['RecipeIngredientOut'];
type Cabinet = components['schemas']['CabinetOut'];

export type Have =
  | { kind: 'have' }
  | { kind: 'low'; have: string } // there's some, less than the recipe needs
  | { kind: 'check' } // in the Cabinet, but the amount is too old to trust
  | { kind: 'need' };

/** null: the line has no Ingredient (water, or not recognised), so we can't say. */
export function matchLine(line: Line, cabinet: Cabinet): Have | null {
  const id = line.ingredient?.id;
  if (!id) return null;

  const staple = cabinet.staples.find((s) => s.ingredient.id === id);
  if (staple) return staple.have ? { kind: 'have' } : { kind: 'need' };

  const item = cabinet.tracked.find((i) => i.ingredient.id === id);
  if (!item) return { kind: 'need' };
  if (item.status === 'unknown') return { kind: 'check' };
  // "Some" (no amount recorded), or a recipe amount that doesn't convert ("3 cloves"):
  // we can't compare, and having it at all is the useful answer.
  if (item.quantity === null || line.base_quantity === null) return { kind: 'have' };
  if (Number(item.quantity) >= Number(line.base_quantity)) return { kind: 'have' };
  return { kind: 'low', have: formatAmount(item.quantity, item.unit) };
}

/** "You have 6 of 9": counts lines with an Ingredient, leaving out optional ones. */
export function haveSummary(lines: Line[], cabinet: Cabinet) {
  const counted = lines.filter((l) => l.ingredient && !l.optional);
  const have = counted.filter((l) => matchLine(l, cabinet)?.kind === 'have').length;
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
