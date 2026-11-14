/// <reference types="jest" />
import type { components } from '@/lib/api/schema';

import { cuisineName, haveSummary, matchLine, minutesText } from './cabinetMatch';

type Line = components['schemas']['RecipeIngredientOut'];
type Cabinet = components['schemas']['CabinetOut'];

const ingredient = (id: string, name: string, unit = 'g') => ({
  id,
  name,
  category: 'pantry',
  default_unit: unit,
  is_default_staple: false,
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
  ...over,
});

const cabinet: Cabinet = {
  version: 1,
  tracked: [
    {
      ingredient: ingredient('pasta', 'pasta'),
      quantity: '200',
      unit: 'g',
      status: 'confirmed',
      last_change_source: 'purchase',
      last_confirmed_at: '2026-11-14T00:00:00Z',
    },
    {
      ingredient: ingredient('rice', 'rice'),
      quantity: null,
      unit: 'g',
      status: 'estimated',
      last_change_source: 'manual',
      last_confirmed_at: '2026-11-01T00:00:00Z',
    },
    {
      ingredient: ingredient('milk', 'milk', 'ml'),
      quantity: '1000',
      unit: 'ml',
      status: 'unknown',
      last_change_source: 'purchase',
      last_confirmed_at: '2026-09-01T00:00:00Z',
    },
  ],
  staples: [
    { ingredient: ingredient('salt', 'salt'), have: true },
    { ingredient: ingredient('flour', 'plain flour'), have: false },
  ],
};

test('enough in the Cabinet: have', () => {
  expect(matchLine(line({ base_quantity: '150' }), cabinet)).toEqual({ kind: 'have' });
});

test('some, but less than the recipe needs: says how much there is', () => {
  expect(matchLine(line(), cabinet)).toEqual({ kind: 'low', have: '200 g' });
});

test('in the Cabinet with no amount recorded: have', () => {
  const rice = line({ ingredient: ingredient('rice', 'rice'), base_quantity: '300' });
  expect(matchLine(rice, cabinet)).toEqual({ kind: 'have' });
});

test('an amount we no longer trust: check', () => {
  const milk = line({ ingredient: ingredient('milk', 'milk', 'ml'), base_quantity: '250' });
  expect(matchLine(milk, cabinet)).toEqual({ kind: 'check' });
});

test('Staples: have unless run out', () => {
  expect(matchLine(line({ ingredient: ingredient('salt', 'salt') }), cabinet)).toEqual({
    kind: 'have',
  });
  expect(matchLine(line({ ingredient: ingredient('flour', 'plain flour') }), cabinet)).toEqual({
    kind: 'need',
  });
});

test('not in the Cabinet: need', () => {
  expect(matchLine(line({ ingredient: ingredient('eggs', 'eggs') }), cabinet)).toEqual({
    kind: 'need',
  });
});

test('a recipe amount we cannot compare (3 cloves) counts as have', () => {
  expect(matchLine(line({ base_quantity: null }), cabinet)).toEqual({ kind: 'have' });
});

test('lines without an Ingredient get no indicator', () => {
  expect(matchLine(line({ ingredient: null }), cabinet)).toBeNull();
});

test('summary counts only lines with an Ingredient, and skips optional ones', () => {
  const lines = [
    line({ base_quantity: '100' }), // have
    line({ ingredient: ingredient('eggs', 'eggs') }), // need
    line({ ingredient: ingredient('eggs', 'eggs'), optional: true }), // skipped
    line({ ingredient: null }), // water: skipped
  ];
  expect(haveSummary(lines, cabinet)).toEqual({ have: 1, total: 2 });
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
