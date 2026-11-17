import type { components } from '@/lib/api/schema';

import {
  amountProblem,
  formRows,
  groups,
  hasChanges,
  inKitchenText,
  tickedCount,
  toApply,
} from './photoReview';

type Row = components['schemas']['PhotoRowOut'];

const ing = (name: string, unit = 'count') => ({
  id: `i-${name}`,
  name,
  category: 'dairy',
  default_unit: unit,
  is_household_ingredient: false,
});

const ROWS: Row[] = [
  { name: 'eggs', ingredient: ing('eggs'), quantity: '6', ticked: true, in_kitchen: null },
  {
    name: 'milk',
    ingredient: ing('milk', 'ml'),
    quantity: null,
    ticked: true,
    in_kitchen: { quantity: '1000', unit: 'ml', status: 'unknown' },
  },
  {
    name: 'salt',
    ingredient: ing('salt', 'g'),
    quantity: null,
    ticked: true,
    in_kitchen: { staple: true, have: false },
  },
  { name: 'yuzu kosho', ingredient: null, quantity: null, ticked: true, in_kitchen: null },
];

describe('formRows and groups', () => {
  it('splits new things from what the Kitchen already has', () => {
    const { fresh, existing } = groups(formRows(ROWS));
    expect(fresh.map((r) => r.name)).toEqual(['eggs', 'yuzu kosho']);
    expect(existing.map((r) => r.name)).toEqual(['milk', 'salt']);
  });

  it('starts each row as Sweep sent it: ticked, with its suggested amount', () => {
    const [eggs, milk] = formRows(ROWS);
    expect([eggs.ticked, eggs.amount, eggs.unit]).toEqual([true, '6', '']);
    expect([milk.amount, milk.unit]).toEqual(['', 'ml']);
  });

  it('a Staple has no amount to edit', () => {
    expect(formRows(ROWS)[2].canHaveAmount).toBe(false);
  });
});

describe('inKitchenText', () => {
  it.each([
    [ROWS[1], '1 L in Kitchen, not sure it’s still there'],
    [ROWS[2], 'Staple, marked run out'],
    [ROWS[0], null],
    [
      { ...ROWS[0], in_kitchen: { quantity: '4', unit: 'count', status: 'confirmed' } } as Row,
      '4 in Kitchen',
    ],
    [
      { ...ROWS[0], in_kitchen: { quantity: null, unit: 'count', status: 'estimated' } } as Row,
      'Some in Kitchen',
    ],
  ])('%#', (row, text) => {
    expect(inKitchenText(formRows([row])[0])).toBe(text);
  });
});

describe('amountProblem', () => {
  it.each([
    ['', null],
    ['6', null],
    ['1.5', null],
    ['0', 'An amount above 0, or leave it empty.'],
    ['lots', 'An amount above 0, or leave it empty.'],
  ])('%j', (amount, problem) => {
    expect(amountProblem({ ...formRows(ROWS)[0], amount })).toBe(problem);
  });
});

describe('toApply', () => {
  it('sends ticked rows only: an id when linked, the name when not', () => {
    const rows = formRows(ROWS);
    rows[2] = { ...rows[2], ticked: false };
    expect(toApply('fridge', rows)).toEqual({
      place: 'fridge',
      items: [
        { ingredient_id: 'i-eggs', quantity: '6' },
        { ingredient_id: 'i-milk', quantity: null }, // kept as it is (or "have some")
        { name: 'yuzu kosho', quantity: null },
      ],
    });
  });

  it('a photo amount replaces, so what the Member typed is what is sent', () => {
    const rows = formRows(ROWS).map((r) => (r.name === 'eggs' ? { ...r, amount: ' 5 ' } : r));
    expect(toApply('fridge', rows).items[0]).toEqual({ ingredient_id: 'i-eggs', quantity: '5' });
  });

  it('tickedCount counts what "Add N to Kitchen" will add', () => {
    const rows = formRows(ROWS);
    expect(tickedCount(rows)).toBe(4);
    expect(tickedCount([{ ...rows[0], ticked: false }, rows[1]])).toBe(1);
  });
});

describe('hasChanges', () => {
  it('an untouched review has none; a tick or an amount is one', () => {
    const start = formRows(ROWS);
    expect(hasChanges(start, formRows(ROWS))).toBe(false);
    expect(hasChanges(start, [{ ...start[0], ticked: false }, ...start.slice(1)])).toBe(true);
    expect(hasChanges(start, [{ ...start[0], amount: '7' }, ...start.slice(1)])).toBe(true);
  });
});
