/**
 * The Kitchen screen's view of the data (ADR 0024): one row type for Staples and
 * Non-staples, the summary counts, and the tab / Place / stock filters grouped into
 * category sections. Plain functions, so the rules are tested without rendering.
 */
import type { components } from '@/lib/api/schema';

import { displayName, formatAmount } from './format';
import type { Place, PlaceFilter } from './places';

export type Stock = components['schemas']['KitchenItemOut']['stock'];
type Tracked = components['schemas']['KitchenItemOut'];
type Staple = components['schemas']['StapleOut'];
type Ingredient = components['schemas']['IngredientOut'];

export type KitchenRow = {
  id: string; // the Ingredient's id: one row per Ingredient
  name: string; // as shown: "Celery salt"
  ingredient: Ingredient;
  staple: boolean;
  stock: Stock;
  place: Place;
  /** "500 g", "1.5 kg" or "Some" for a Non-staple; always null for a Staple. */
  amount: string | null;
  quantity: string | null; // in the Ingredient's own unit (g, ml or count)
  unit: string;
};

export type Tab = 'staples' | 'non-staples';

export const STOCK_ORDER: readonly Stock[] = ['in_stock', 'low', 'out'];

export const STOCK_LABEL: Record<Stock, string> = {
  in_stock: 'In stock',
  low: 'Running low',
  out: 'Out',
};

/**
 * What changing the status does next (ADR 0024): a Staple that runs out is already on
 * the list (the server added it; offer Undo), a Non-staple only gets asked.
 */
export function afterStockChange(row: { staple: boolean; stock: Stock }, next: Stock) {
  if (next !== 'out' || row.stock === 'out') return 'none' as const;
  return row.staple ? ('addedToList' as const) : ('askToAdd' as const);
}

/**
 * What removing an item does (••• Remove item, or a swipe). Removing means "it's gone",
 * so it follows the Out rule: a Staple is marked Out, which puts it on the list and keeps
 * it a Staple (buying it sets it back In stock). A Non-staple leaves the Kitchen and the
 * toast offers to add it, unless it's already on the list.
 */
export function afterRemove(row: { staple: boolean; stock: Stock }, onList: boolean) {
  if (row.staple) return row.stock === 'out' ? ('addToList' as const) : ('markOut' as const);
  return onList ? ('remove' as const) : ('removeAndAsk' as const);
}

export function toRows(kitchen: { tracked: readonly Tracked[]; staples: readonly Staple[] }) {
  const rows: KitchenRow[] = [
    ...kitchen.staples.map((s) => ({
      id: s.ingredient.id,
      name: displayName(s.ingredient.name),
      ingredient: s.ingredient,
      staple: true,
      stock: s.stock,
      place: s.place,
      amount: null, // Staples have no amount (ADR 0024)
      quantity: null,
      unit: s.ingredient.default_unit,
    })),
    ...kitchen.tracked.map((t) => ({
      id: t.ingredient.id,
      name: displayName(t.ingredient.name),
      ingredient: t.ingredient,
      staple: false,
      stock: t.stock,
      place: t.place,
      amount: formatAmount(t.quantity, t.unit),
      quantity: t.quantity,
      unit: t.unit,
    })),
  ];
  return rows;
}

export function summary(rows: readonly KitchenRow[]) {
  const count = (stock: Stock) => rows.filter((r) => r.stock === stock).length;
  return { total: rows.length, in_stock: count('in_stock'), low: count('low'), out: count('out') };
}

/** Ingredient categories as section headings, in the order you'd cook with them. */
export const CATEGORIES: readonly { category: string; label: string }[] = [
  { category: 'spices', label: 'Spices & Seasoning' },
  { category: 'pantry', label: 'Pantry' },
  { category: 'bakery', label: 'Bakery' },
  { category: 'produce', label: 'Fruit & Veg' },
  { category: 'dairy', label: 'Dairy & Eggs' },
  { category: 'chilled', label: 'Chilled' },
  { category: 'meat', label: 'Meat' },
  { category: 'seafood', label: 'Seafood' },
  { category: 'frozen', label: 'Frozen' },
  { category: 'drinks', label: 'Drinks' },
];

export type Section = { category: string; label: string; rows: KitchenRow[] };

/**
 * What's on screen: the chosen tab, Place and (optionally) stock tile, grouped by
 * category. Inside a section: In stock, then Running low, then Out, then A to Z.
 */
export function sections(
  rows: readonly KitchenRow[],
  filter: { tab: Tab; place: PlaceFilter; stock: Stock | null },
): Section[] {
  const shown = rows.filter(
    (r) =>
      r.staple === (filter.tab === 'staples') &&
      (filter.place === 'all' || r.place === filter.place) &&
      (filter.stock === null || r.stock === filter.stock),
  );
  const known = new Set(CATEGORIES.map((c) => c.category));
  const all = [...CATEGORIES, { category: 'other', label: 'Other' }];
  return all
    .map(({ category, label }) => ({
      category,
      label,
      rows: shown
        .filter((r) =>
          category === 'other'
            ? !known.has(r.ingredient.category)
            : r.ingredient.category === category,
        )
        .sort(
          (a, b) =>
            STOCK_ORDER.indexOf(a.stock) - STOCK_ORDER.indexOf(b.stock) ||
            a.name.localeCompare(b.name),
        ),
    }))
    .filter((s) => s.rows.length > 0);
}
