import {
  allKept,
  decisionFor,
  isAdditionKept,
  keptCount,
  startingTicks,
  toggleAddition,
  toggleMeal,
} from './decision';

const proposal = {
  meals: [{ date: '2026-11-16' }, { date: '2026-11-17' }],
  // reason null: how the API returns Proposals saved before slice 10.
  list_additions: [
    { name: 'eggs', reason: null },
    { name: 'coriander', reason: null },
    { name: 'limes', reason: null },
  ],
};

describe('ticks on a Proposal', () => {
  it('start with everything kept, and approving sends no lists', () => {
    const ticks = allKept();
    expect(keptCount(proposal, ticks)).toEqual({ meals: 2, additions: 3 });
    // Leaving both lists out means "keep all" on the server, so a plan the Member
    // didn't touch can't be misread as "keep none".
    expect(decisionFor(proposal, ticks)).toEqual({ action: 'approve' });
  });

  it('send only what stays ticked: meal dates and addition positions', () => {
    let ticks = allKept();
    ticks = toggleMeal(ticks, '2026-11-17');
    ticks = toggleAddition(ticks, 1);
    expect(keptCount(proposal, ticks)).toEqual({ meals: 1, additions: 2 });
    expect(decisionFor(proposal, ticks)).toEqual({
      action: 'approve',
      keep_meals: ['2026-11-16'],
      keep_additions: [0, 2],
    });
  });

  it('send just the kind that changed', () => {
    const ticks = toggleAddition(allKept(), 0);
    expect(decisionFor(proposal, ticks)).toEqual({ action: 'approve', keep_additions: [1, 2] });
  });

  it('can be ticked again', () => {
    const ticks = toggleMeal(toggleMeal(allKept(), '2026-11-16'), '2026-11-16');
    expect(decisionFor(proposal, ticks)).toEqual({ action: 'approve' });
  });

  it('give null when nothing is kept, so Approve can be turned off', () => {
    let ticks = allKept();
    for (const m of proposal.meals) ticks = toggleMeal(ticks, m.date);
    for (const i of [0, 1, 2]) ticks = toggleAddition(ticks, i);
    expect(decisionFor(proposal, ticks)).toBeNull();
  });

  it('keep the order the plan shows, whatever order they were ticked in', () => {
    let ticks = allKept();
    for (const i of [2, 1, 0]) ticks = toggleAddition(ticks, i);
    ticks = toggleAddition(ticks, 2);
    ticks = toggleAddition(ticks, 0);
    expect(decisionFor(proposal, ticks)?.keep_additions).toEqual([0, 2]);
  });
});

describe('unexplained List Additions (slice 10)', () => {
  // "wine" came from text the agent read (say, a Kitchen item), not from a meal or
  // from the Member: it starts unticked, so approving without looking leaves it off.
  const flagged = {
    meals: [{ date: '2026-11-16' }],
    list_additions: [
      { name: 'eggs', reason: 'meal' as const },
      { name: 'wine', reason: 'unexplained' as const },
      { name: 'limes', reason: 'asked' as const },
    ],
  };

  it('start unticked, and approving names exactly what stays ticked', () => {
    const ticks = startingTicks(flagged);
    expect(isAdditionKept(ticks, 1)).toBe(false);
    expect(keptCount(flagged, ticks)).toEqual({ meals: 1, additions: 2 });
    expect(decisionFor(flagged, ticks)).toEqual({ action: 'approve', keep_additions: [0, 2] });
  });

  it('are added when the Member ticks one on purpose', () => {
    const ticks = toggleAddition(startingTicks(flagged), 1);
    expect(isAdditionKept(ticks, 1)).toBe(true);
    // Nothing unticked now, so no list is sent: the server's "keep all" default would
    // skip "wine" again, so the decision must name it.
    expect(decisionFor(flagged, ticks)).toEqual({
      action: 'approve',
      keep_additions: [0, 1, 2],
    });
  });

  it('leave a plan with no reasons (saved before slice 10) fully ticked', () => {
    expect(startingTicks(proposal)).toEqual(allKept());
    expect(decisionFor(proposal, startingTicks(proposal))).toEqual({ action: 'approve' });
  });
});
