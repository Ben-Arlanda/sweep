/// <reference types="jest" />
import type { ListDetail } from '@/lib/api/client';

import { newItem } from './listCache';
import { filterByShop, knownShop, shopName, withItemShop } from './shops';

const coles = { id: 'coles', name: 'Coles' };
const aldi = { id: 'aldi', name: 'Aldi' };

function list(): ListDetail {
  const at = (n: number) => `2026-11-15T09:0${n}:00Z`;
  return {
    id: 'list-1',
    name: 'Shopping List',
    version: 1,
    shops: [aldi, coles],
    items: [
      newItem({
        id: 'bread',
        text: 'Bread',
        memberId: 'a',
        now: at(1),
        shopId: 'aldi',
      }),
      newItem({
        id: 'milk',
        text: 'Milk',
        memberId: 'a',
        now: at(2),
        shopId: 'coles',
      }),
      newItem({ id: 'eggs', text: 'Eggs', memberId: 'a', now: at(3) }),
    ],
  };
}

test('"All" shows every item', () => {
  expect(filterByShop(list().items, 'all').map((i) => i.id)).toEqual(['bread', 'milk', 'eggs']);
});

test("a Shop filter shows only that Shop's items (any-shop items are on All)", () => {
  expect(filterByShop(list().items, 'aldi').map((i) => i.id)).toEqual(['bread']);
  expect(filterByShop(list().items, 'coles').map((i) => i.id)).toEqual(['milk']);
});

test('new items carry the Shop chosen when adding, or none', () => {
  const [bread, , eggs] = list().items;
  expect([bread.shop_id, eggs.shop_id]).toEqual(['aldi', null]);
});

test('tagging an item changes only that item', () => {
  const after = withItemShop(list(), 'eggs', 'coles');

  expect(after.items.map((i) => [i.id, i.shop_id])).toEqual([
    ['bread', 'aldi'],
    ['milk', 'coles'],
    ['eggs', 'coles'],
  ]);
});

test('an item whose Shop was deleted reads as any shop', () => {
  expect(shopName(list().shops, 'coles')).toBe('Coles');
  expect(shopName(list().shops, 'gone')).toBeNull();
  expect(shopName(list().shops, null)).toBeNull();
});

test('a remembered Shop or filter that no longer exists falls back', () => {
  const { shops } = list();
  expect(knownShop('aldi', shops)).toBe('aldi');
  expect(knownShop('deleted-on-another-phone', shops)).toBeNull();
  expect(knownShop(null, shops)).toBeNull();
});
