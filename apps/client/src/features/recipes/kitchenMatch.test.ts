/// <reference types="jest" />
import type { components } from '@/lib/api/schema';

import { addText, cuisineName, haveSummary, matchLine, minutesText } from './kitchenMatch';

type Line = components['schemas']['RecipeIngredientOut'];
type Kitchen = components['schemas']['KitchenOut'];

const ingredient = (id: string, name: string, unit = 'g') => ({
  id,
  name,
  category: 'pantry',
  default_unit: unit,
  is_default_staple: false,
  is_household_ingredient: false,
});

const line = (over: Partial<Line> = {}): Line => ({
  raw_text: '500 g pasta',
  ingredient: ingredient('pasta', 'pasta'),
  quantity: '500',
  unit: 'g',
  base_quantity: '500',
  note: null,
  optional: false,
  needs_review: false,
  parse_method: 'rule',
  ...over,
});

const kitchen: Kitchen = {
  version: 1,
  tracked: [
    {
      ingredient: ingredient('pasta', 'pasta'),
      quantity: '200',
      unit: 'g',
      status: 'confirmed',
      last_change_source: 'purchase',
      last_confirmed_at: '2026-11-14T00:00:00Z',
      place: 'fridge',
      stock: 'in_stock' as const,
    },
    {
      ingredient: ingredient('rice', 'rice'),
      quantity: null,
      unit: 'g',
      status: 'estimated',
      last_change_source: 'manual',
      last_confirmed_at: '2026-11-01T00:00:00Z',
      place: 'fridge',
      stock: 'in_stock' as const,
    },
    {
      ingredient: ingredient('milk', 'milk', 'ml'),
      quantity: '1000',
      unit: 'ml',
      status: 'unknown',
      last_change_source: 'purchase',
      last_confirmed_at: '2026-09-01T00:00:00Z',
      place: 'fridge',
      stock: 'in_stock' as const,
    },
  ],
  staples: [
    {
      ingredient: ingredient('salt', 'salt'),
      have: true,
      place: 'cupboard',
      stock: 'in_stock',
    },
    {
      ingredient: ingredient('flour', 'plain flour'),
      have: false,
      place: 'cupboard',
      stock: 'out',
    },
  ],
};

test('enough in the Kitchen: have', () => {
  expect(matchLine(line({ base_quantity: '150' }), kitchen)).toEqual({ kind: 'have' });
});

test('some, but less than the recipe needs: says how much there is', () => {
  expect(matchLine(line(), kitchen)).toEqual({ kind: 'low', have: '200 g' });
});

test('in the Kitchen with no amount recorded: have', () => {
  const rice = line({ ingredient: ingredient('rice', 'rice'), base_quantity: '300' });
  expect(matchLine(rice, kitchen)).toEqual({ kind: 'have' });
});

test('an amount we no longer trust: check', () => {
  const milk = line({ ingredient: ingredient('milk', 'milk', 'ml'), base_quantity: '250' });
  expect(matchLine(milk, kitchen)).toEqual({ kind: 'check' });
});

test('Staples: have unless run out', () => {
  expect(matchLine(line({ ingredient: ingredient('salt', 'salt') }), kitchen)).toEqual({
    kind: 'have',
  });
  expect(matchLine(line({ ingredient: ingredient('flour', 'plain flour') }), kitchen)).toEqual({
    kind: 'need',
  });
});

test('a Non-staple marked Out: need, though it is still listed in the Kitchen', () => {
  const out: Kitchen = {
    ...kitchen,
    tracked: kitchen.tracked.map((i) => ({ ...i, stock: 'out' as const })),
  };
  expect(matchLine(line({ base_quantity: '150' }), out)).toEqual({ kind: 'need' });
});

test('not in the Kitchen: need', () => {
  expect(matchLine(line({ ingredient: ingredient('eggs', 'eggs') }), kitchen)).toEqual({
    kind: 'need',
  });
});

test('a recipe amount we cannot compare (3 cloves) counts as have', () => {
  expect(matchLine(line({ base_quantity: null }), kitchen)).toEqual({ kind: 'have' });
});

test('lines without an Ingredient get no indicator', () => {
  expect(matchLine(line({ ingredient: null }), kitchen)).toBeNull();
});

test('summary counts only lines with an Ingredient, and skips optional ones', () => {
  const lines = [
    line({ base_quantity: '100' }), // have
    line({ ingredient: ingredient('eggs', 'eggs') }), // need
    line({ ingredient: ingredient('eggs', 'eggs'), optional: true }), // skipped
    line({ ingredient: null }), // water: skipped
  ];
  expect(haveSummary(lines, kitchen)).toEqual({ have: 1, total: 2 });
});

test.each([
  [20, '20 min'],
  [60, '1 h'],
  [75, '1 h 15 min'],
  [null, null],
])('shows %s minutes as %s', (minutes, expected) => {
  expect(minutesText(minutes)).toBe(expected);
});

test.each([
  ['indian', 'Indian'],
  ['middle-eastern', 'Middle Eastern'],
  [null, null],
])('shows cuisine %j as %j', (cuisine, expected) => {
  expect(cuisineName(cuisine)).toBe(expected);
});

describe('the Shopping List', () => {
  type Item = components['schemas']['ItemOut'];
  const item = (over: Partial<Item> = {}): Item => ({
    id: 'i1',
    text: 'tomatoes',
    quantity: '3',
    unit: null,
    added_by: 'agent',
    added_by_member_id: null,
    created_at: '2026-11-15T00:00:00Z',
    checked_at: null,
    checked_by: null,
    ingredient: ingredient('tomatoes', 'tomatoes', 'count'),
    shop_id: null,
    checked: false,
    ...over,
  });
  const tomatoes = line({
    raw_text: '2 tomatoes, sliced',
    ingredient: ingredient('tomatoes', 'tomatoes', 'count'),
    quantity: '2',
    unit: null,
    base_quantity: '2',
  });

  it('says "on list" for a needed line already on the list, not "need"', () => {
    expect(matchLine(tomatoes, kitchen, [item()])).toEqual({ kind: 'onList' });
    expect(matchLine(tomatoes, kitchen)).toEqual({ kind: 'need' }); // no list loaded
  });

  it('a ticked item is bought, so it no longer counts as on the list', () => {
    expect(
      matchLine(tomatoes, kitchen, [item({ checked_at: '2026-11-15T01:00:00Z', checked: true })]),
    ).toEqual({
      kind: 'need',
    });
  });

  it('what you have still wins over the list', () => {
    const pasta = item({ ingredient: ingredient('pasta', 'pasta') });
    expect(matchLine(line({ base_quantity: '100' }), kitchen, [pasta])).toEqual({ kind: 'have' });
  });
});

describe('addText', () => {
  it('is the amount and the Ingredient name, which the list reads back', () => {
    expect(
      addText(
        line({
          raw_text: '30 g butter, softened',
          ingredient: ingredient('b', 'butter'),
          base_quantity: '30',
        }),
      ),
    ).toBe('30 g butter');
    expect(
      addText(line({ ingredient: ingredient('t', 'tomatoes', 'count'), base_quantity: '2' })),
    ).toBe('2 tomatoes');
    expect(addText(line({ ingredient: ingredient('f', 'flour'), base_quantity: '1500' }))).toBe(
      '1.5 kg flour',
    );
  });

  it('leaves the amount out when the recipe has none that converts ("1 pinch salt")', () => {
    expect(addText(line({ ingredient: ingredient('s', 'salt'), base_quantity: null }))).toBe(
      'salt',
    );
  });
});
