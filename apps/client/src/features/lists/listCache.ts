/**
 * Optimistic updates: what the list looks like right after a tap, before the server
 * has answered.
 *
 * These are plain functions (old list in, new list out, nothing mutated), so they're
 * easy to test, and TanStack Query can tell something changed. They mirror the server's
 * rules. When the server's answer arrives, the refetch replaces the guess with the real
 * thing, so a mismatch fixes itself.
 */
import type { Ingredient, Item, ListDetail } from '@/lib/api/client';

export function newItem(fields: {
  id: string;
  text: string;
  memberId: string | null;
  now: string;
  shopId?: string | null;
}): Item {
  return {
    id: fields.id,
    text: fields.text.trim(),
    quantity: null,
    unit: null,
    added_by: 'member',
    added_by_member_id: fields.memberId,
    created_at: fields.now,
    checked_at: null,
    checked_by: null,
    checked: false,
    ingredient: null, // the server links it; the refetch fills this in
    shop_id: fields.shopId ?? null,
  };
}

export function withItemAdded(list: ListDetail, item: Item): ListDetail {
  if (list.items.some((i) => i.id === item.id)) return list; // a retry; already there
  return { ...list, items: [...list.items, item] };
}

/** Same rule as the server: checking twice keeps the first person's tick. */
export function withItemChecked(
  list: ListDetail,
  itemId: string,
  checked: boolean,
  memberId: string | null,
  now: string,
): ListDetail {
  return {
    ...list,
    items: list.items.map((item) => {
      if (item.id !== itemId) return item;
      if (checked && item.checked) return item;
      return checked
        ? { ...item, checked: true, checked_at: now, checked_by: memberId }
        : { ...item, checked: false, checked_at: null, checked_by: null };
    }),
  };
}

/**
 * "Link to…": the item now means this Ingredient (null: don't add it to the Kitchen).
 * Moving Kitchen stock and saving the Household link are the server's job.
 */
export function withItemIngredient(
  list: ListDetail,
  itemId: string,
  ingredient: Ingredient | null,
): ListDetail {
  return {
    ...list,
    items: list.items.map((item) => (item.id === itemId ? { ...item, ingredient } : item)),
  };
}

export function withItemRemoved(list: ListDetail, itemId: string): ListDetail {
  return { ...list, items: list.items.filter((i) => i.id !== itemId) };
}

/** Still to buy first (in the order added), then what's already in the trolley. */
export function shoppingOrder(items: readonly Item[]): {
  toBuy: Item[];
  inTrolley: Item[];
} {
  const byAdded = [...items].sort((a, b) => a.created_at.localeCompare(b.created_at));
  return {
    toBuy: byAdded.filter((i) => !i.checked),
    inTrolley: byAdded.filter((i) => i.checked),
  };
}

/**
 * Should a change notice trigger a refetch? Not if our cached copy is already at (or
 * past) that version, e.g. the notice for our own change arriving after our refetch.
 */
export function isNewer(noticeVersion: number, cached: ListDetail | undefined): boolean {
  return cached === undefined || noticeVersion > cached.version;
}
