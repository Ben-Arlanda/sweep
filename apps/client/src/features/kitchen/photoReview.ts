/**
 * The Kitchen Photo review's rules (slice 3e, ADR 0023), as pure functions.
 *
 * Sweep names what it saw; the Member ticks, unticks or fixes amounts, then one tap adds
 * the ticked rows. A photo shows what the Household has, so an amount replaces what the
 * Kitchen holds (never adds), and nothing missing from the photo is removed.
 */
import type { components } from '@/lib/api/schema';

import { formatAmount } from './format';

type PhotoRow = components['schemas']['PhotoRowOut'];
type Place = components['schemas']['Place'];
export type KitchenPhotoApplyIn = components['schemas']['KitchenPhotoApplyIn'];

export type ReviewRow = {
  key: string;
  name: string; // as Sweep named it
  ingredient: PhotoRow['ingredient']; // null: Not linked, added as a Household Ingredient
  amount: string; // as typed; '' = "have some" (or keep what's there)
  unit: string; // '' for counts
  canHaveAmount: boolean; // a Staple is only have / run out
  ticked: boolean;
  inKitchen: PhotoRow['in_kitchen'];
};

export function formRows(rows: PhotoRow[]): ReviewRow[] {
  return rows.map((row, i) => {
    const unit = row.ingredient?.default_unit ?? 'count';
    return {
      key: `row-${i}`,
      name: row.name,
      ingredient: row.ingredient,
      amount: row.quantity ?? '',
      unit: unit === 'count' ? '' : unit,
      canHaveAmount: !(row.in_kitchen && 'staple' in row.in_kitchen),
      ticked: row.ticked,
      inKitchen: row.in_kitchen,
    };
  });
}

export function groups(rows: ReviewRow[]) {
  return {
    fresh: rows.filter((r) => r.inKitchen === null),
    existing: rows.filter((r) => r.inKitchen !== null),
  };
}

/** What the Kitchen has now, so "4 in Kitchen" sits next to the photo's 6. */
export function inKitchenText(row: ReviewRow): string | null {
  const now = row.inKitchen;
  if (!now) return null;
  if ('staple' in now) return now.have ? 'Staple, have' : 'Staple, marked run out';
  const amount =
    now.quantity === null
      ? 'Some'
      : formatAmount(now.quantity, now.unit === 'count' ? '' : now.unit);
  const text = `${amount} in Kitchen`;
  return now.status === 'unknown' ? `${text}, not sure it’s still there` : text;
}

const AMOUNT = /^\d+(\.\d+)?$/;

export function amountProblem(row: ReviewRow): string | null {
  const amount = row.amount.trim();
  if (!amount) return null;
  return AMOUNT.test(amount) && Number(amount) > 0 ? null : 'An amount above 0, or leave it empty.';
}

export const tickedCount = (rows: ReviewRow[]) => rows.filter((r) => r.ticked).length;

/** Only call when no ticked row has an amountProblem. */
export function toApply(place: Place, rows: ReviewRow[]): KitchenPhotoApplyIn {
  return {
    place,
    items: rows
      .filter((r) => r.ticked)
      .map((r) => {
        const quantity = r.canHaveAmount && r.amount.trim() ? r.amount.trim() : null;
        return r.ingredient
          ? { ingredient_id: r.ingredient.id, quantity }
          : { name: r.name, quantity };
      }),
  };
}

/** For "leave without adding?". */
export function hasChanges(start: ReviewRow[], now: ReviewRow[]): boolean {
  const comparable = (rows: ReviewRow[]) => JSON.stringify(rows.map((r) => [r.ticked, r.amount]));
  return comparable(start) !== comparable(now);
}
