/// <reference types="jest" />
import { afterStockChange, sections, summary, toRows } from './kitchenView';

const ing = (name: string, category: string) => ({
  id: name,
  name,
  category,
  default_unit: 'g',
  is_household_ingredient: false,
});
const tracked = (name: string, category: string, stock: 'in_stock' | 'low' | 'out') => ({
  ingredient: ing(name, category),
  quantity: '500',
  unit: 'g',
  status: 'confirmed' as const,
  last_change_source: 'manual' as const,
  last_confirmed_at: '2026-11-15T00:00:00Z',
  place: 'cupboard' as const,
  stock,
});
const staple = (
  name: string,
  category: string,
  stock: 'in_stock' | 'low' | 'out',
  place: 'fridge' | 'cupboard' = 'cupboard',
) => ({
  ingredient: ing(name, category),
  have: stock !== 'out',
  place,
  stock,
});

const rows = toRows({
  tracked: [tracked('plain flour', 'pantry', 'low'), tracked('avocado', 'produce', 'out')],
  staples: [
    staple('chilli flakes', 'spices', 'out'),
    staple('celery salt', 'spices', 'in_stock'),
    staple('ground nutmeg', 'spices', 'low'),
    staple('milk', 'dairy', 'in_stock', 'fridge'),
    staple('finger lime', 'mystery', 'in_stock'),
  ],
});

test('Ran out: a Staple goes on the list, a Non-staple asks, anything else does nothing', () => {
  expect(afterStockChange({ staple: true, stock: 'in_stock' }, 'out')).toBe('addedToList');
  expect(afterStockChange({ staple: false, stock: 'low' }, 'out')).toBe('askToAdd');
  expect(afterStockChange({ staple: true, stock: 'out' }, 'out')).toBe('none');
  expect(afterStockChange({ staple: true, stock: 'in_stock' }, 'low')).toBe('none');
});

test('Staples have no amount; Non-staples show theirs in real units', () => {
  const amount = Object.fromEntries(rows.map((r) => [r.name, r.amount]));
  expect(amount['Celery salt']).toBeNull();
  expect(amount['Plain flour']).toBe('500 g');
});

test('summary counts every item across both tabs', () => {
  expect(summary(rows)).toEqual({ total: 7, in_stock: 3, low: 2, out: 2 });
});

test('Staples tab groups by category, In stock → Low → Out inside each', () => {
  const shown = sections(rows, { tab: 'staples', place: 'all', stock: null });

  expect(shown.map((s) => [s.label, s.rows.map((r) => r.name)])).toEqual([
    ['Spices & Seasoning', ['Celery salt', 'Ground nutmeg', 'Chilli flakes']],
    ['Dairy & Eggs', ['Milk']],
    ['Other', ['Finger lime']],
  ]);
});

test('Non-staples tab, a Place and a stock tile all narrow the list', () => {
  expect(
    sections(rows, { tab: 'non-staples', place: 'all', stock: null }).map((s) => s.label),
  ).toEqual(['Pantry', 'Fruit & Veg']);
  expect(
    sections(rows, { tab: 'staples', place: 'fridge', stock: null }).flatMap((s) =>
      s.rows.map((r) => r.name),
    ),
  ).toEqual(['Milk']);
  expect(
    sections(rows, { tab: 'staples', place: 'all', stock: 'low' }).flatMap((s) =>
      s.rows.map((r) => r.name),
    ),
  ).toEqual(['Ground nutmeg']);
});
