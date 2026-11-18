import { decisionFor } from '@/features/chat/decision';

import { additionText, approveTicks, toAdd } from './quickAdd';

const plan = {
  meals: [{ date: '2026-11-18' }, { date: '2026-11-19' }],
  list_additions: [
    { name: 'canned tomatoes', quantity: 800, unit: 'g', reason: 'meal' as const },
    { name: 'red onion', quantity: 2, unit: 'count', reason: 'meal' as const },
    { name: 'garlic', quantity: null, unit: 'count', reason: 'meal' as const },
    { name: 'wine', quantity: 1, unit: 'count', reason: 'unexplained' as const },
  ],
};

describe('additionText', () => {
  it('reads like something typed onto the list', () => {
    expect(plan.list_additions.slice(0, 3).map(additionText)).toEqual([
      '800 g canned tomatoes',
      '2 red onion',
      'garlic',
    ]);
  });
});

describe('toAdd', () => {
  it('leaves out unexplained additions and ones already added', () => {
    expect(toAdd(plan, [])).toEqual(['800 g canned tomatoes', '2 red onion', 'garlic']);
    expect(toAdd(plan, ['2 red onion'])).toEqual(['800 g canned tomatoes', 'garlic']);
  });
});

describe('approveTicks', () => {
  it('keeps every addition when nothing was quick-added', () => {
    expect(decisionFor(plan, approveTicks(plan, []))).toEqual({
      action: 'approve',
      keep_additions: [0, 1, 2],
    });
  });

  it("doesn't add quick-added items a second time", () => {
    const added = toAdd(plan, []);
    expect(decisionFor(plan, approveTicks(plan, added))).toEqual({
      action: 'approve',
      keep_additions: [],
    });
  });

  it('still adds what a swap brought in after the quick add', () => {
    expect(decisionFor(plan, approveTicks(plan, ['800 g canned tomatoes']))).toEqual({
      action: 'approve',
      keep_additions: [1, 2],
    });
  });
});
