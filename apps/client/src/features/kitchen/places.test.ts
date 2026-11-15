/// <reference types="jest" />
import { byPlace, type KitchenRows } from './places';

const ing = (name: string) => ({ id: name, name, category: 'x', default_unit: 'g' });
const tracked = (name: string, place: 'fridge' | 'freezer' | 'cupboard') => ({
  ingredient: ing(name),
  quantity: '1',
  unit: 'g',
  status: 'confirmed' as const,
  last_change_source: 'manual' as const,
  last_confirmed_at: '2026-11-15T00:00:00Z',
  place,
});
const staple = (name: string, have: boolean, place: 'fridge' | 'freezer' | 'cupboard') => ({
  ingredient: ing(name),
  have,
  place,
});

const kitchen: KitchenRows = {
  tracked: [tracked('chicken', 'fridge'), tracked('peas', 'freezer'), tracked('rice', 'cupboard')],
  staples: [staple('salt', true, 'cupboard'), staple('oil', false, 'cupboard')],
};

test('"All" shows every Place that has something, fridge first', () => {
  const sections = byPlace(kitchen, 'all');

  expect(sections.map((s) => [s.place, s.tracked.length, s.staples.length])).toEqual([
    ['fridge', 1, 0],
    ['freezer', 1, 0],
    ['cupboard', 1, 2],
  ]);
});

test('a Place filter shows only that Place, even when it is empty', () => {
  expect(byPlace(kitchen, 'freezer').map((s) => s.place)).toEqual(['freezer']);

  const empty = byPlace({ tracked: [], staples: [] }, 'fridge');
  expect(empty).toEqual([{ place: 'fridge', label: 'Fridge', tracked: [], staples: [] }]);
});

test('run-out Staples come first, since they need buying', () => {
  const [cupboard] = byPlace(kitchen, 'cupboard');

  expect(cupboard.staples.map((s) => s.ingredient.name)).toEqual(['oil', 'salt']);
});
