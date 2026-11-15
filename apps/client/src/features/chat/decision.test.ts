import { allKept, decisionFor, keptCount, toggleAddition, toggleMeal } from './decision';

const proposal = {
  meals: [{ date: '2026-11-16' }, { date: '2026-11-17' }],
  list_additions: [{ name: 'eggs' }, { name: 'coriander' }, { name: 'limes' }],
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
