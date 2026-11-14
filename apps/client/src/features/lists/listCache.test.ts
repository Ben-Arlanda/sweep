/// <reference types="jest" />
import type { ListDetail } from '@/lib/api/client';

import {
  isNewer,
  newItem,
  shoppingOrder,
  withItemAdded,
  withItemChecked,
  withItemRemoved,
} from './listCache';

const T1 = '2026-11-14T10:00:00Z';
const T2 = '2026-11-14T10:05:00Z';

function list(...texts: string[]): ListDetail {
  return {
    id: 'list-1',
    name: 'Shopping List',
    version: 3,
    items: texts.map((text, n) =>
      newItem({
        id: `item-${n}`,
        text,
        memberId: 'alice',
        now: `2026-11-14T09:0${n}:00Z`,
      }),
    ),
  };
}

test('adding shows the item at once and trims the text', () => {
  const after = withItemAdded(list(), newItem({ id: 'x', text: ' Milk ', memberId: 'a', now: T1 }));

  expect(after.items.map((i) => [i.id, i.text, i.checked])).toEqual([['x', 'Milk', false]]);
});

test('a retried add does not duplicate the item', () => {
  const item = newItem({ id: 'x', text: 'Milk', memberId: 'a', now: T1 });

  const after = withItemAdded(withItemAdded(list(), item), item);

  expect(after.items).toHaveLength(1);
});

test('checking twice keeps the first tick, like the server', () => {
  const once = withItemChecked(list('Milk'), 'item-0', true, 'alice', T1);
  const twice = withItemChecked(once, 'item-0', true, 'bob', T2);

  expect(twice.items[0]).toMatchObject({
    checked: true,
    checked_at: T1,
    checked_by: 'alice',
  });
});

test('unchecking clears who ticked it', () => {
  const checked = withItemChecked(list('Milk'), 'item-0', true, 'alice', T1);

  const after = withItemChecked(checked, 'item-0', false, 'bob', T2);

  expect(after.items[0]).toMatchObject({
    checked: false,
    checked_at: null,
    checked_by: null,
  });
});

test('updates never change the list they were given', () => {
  const before = list('Milk');
  const snapshot = JSON.stringify(before);

  withItemChecked(before, 'item-0', true, 'alice', T1);
  withItemRemoved(before, 'item-0');

  expect(JSON.stringify(before)).toBe(snapshot);
});

test('removing an item that is already gone is fine', () => {
  expect(withItemRemoved(list('Milk'), 'nope').items).toHaveLength(1);
});

test('shopping order puts what is left to buy first, in the order added', () => {
  const l = withItemChecked(list('Milk', 'Eggs', 'Bread'), 'item-0', true, 'alice', T1);

  const { toBuy, inTrolley } = shoppingOrder(l.items);

  expect(toBuy.map((i) => i.text)).toEqual(['Eggs', 'Bread']);
  expect(inTrolley.map((i) => i.text)).toEqual(['Milk']);
});

test('a notice only triggers a refetch when it is newer than what we have', () => {
  expect(isNewer(4, list())).toBe(true);
  expect(isNewer(3, list())).toBe(false);
  expect(isNewer(1, undefined)).toBe(true);
});
