/**
 * Shops are labels on Shopping List items: where the Household plans to buy them
 * (ADR 0009). No Shop means "any shop".
 *
 * Plain functions, like listCache.ts, so the rules are easy to test and match the server.
 */
import type { Item, ListDetail } from '@/lib/api/client';

export type Shop = ListDetail['shops'][number];
/** What the list is showing: everything, or what to pick up at one Shop. */
export type ShopFilter = 'all' | string;

/**
 * A Shop filter shows only that Shop's items; untagged ("any shop") items are on All.
 * Mixing them in made the filter look broken (user decision 2026-11-18, ADR 0009 note).
 */
export function filterByShop<T extends Pick<Item, 'shop_id'>>(
  items: readonly T[],
  filter: ShopFilter,
): T[] {
  if (filter === 'all') return [...items];
  return items.filter((item) => item.shop_id === filter);
}

export function withItemShop(list: ListDetail, itemId: string, shopId: string | null): ListDetail {
  return {
    ...list,
    items: list.items.map((item) => (item.id === itemId ? { ...item, shop_id: shopId } : item)),
  };
}

/** The Shop's name, or null for "any shop" (including a Shop deleted on another phone). */
export function shopName(shops: readonly Shop[], shopId: string | null): string | null {
  if (shopId === null) return null;
  return shops.find((shop) => shop.id === shopId)?.name ?? null;
}

/** A remembered Shop id, if that Shop still exists; otherwise null. */
export function knownShop(shopId: string | null, shops: readonly Shop[]): string | null {
  return shopId !== null && shops.some((shop) => shop.id === shopId) ? shopId : null;
}
