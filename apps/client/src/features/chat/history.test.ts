import { keptOf, placeProposals, statusLine } from './history';

const line = (role: 'user' | 'assistant', text: string) => ({ role, text });
const plan = (id: string, after_line: number | null) => ({ id, after_line });

describe('placeProposals', () => {
  const messages = [
    line('user', 'plan my week'),
    line('assistant', 'Here is a plan'),
    line('user', 'swap Tuesday'),
    line('assistant', 'Swapped'),
  ];

  it('puts each Proposal after the lines that came before it', () => {
    const items = placeProposals(messages, [plan('a', 2), plan('b', 4)]);
    expect(items.map((i) => (i.kind === 'line' ? i.line.text : `[${i.proposal.id}]`))).toEqual([
      'plan my week',
      'Here is a plan',
      '[a]',
      'swap Tuesday',
      'Swapped',
      '[b]',
    ]);
  });

  it('puts Proposals with no known place at the end, in the order given', () => {
    const items = placeProposals(messages.slice(0, 2), [plan('x', null), plan('y', 0)]);
    expect(items.map((i) => (i.kind === 'line' ? i.line.text : `[${i.proposal.id}]`))).toEqual([
      '[y]',
      'plan my week',
      'Here is a plan',
      '[x]',
    ]);
  });

  it('keeps a place past the end of the transcript at the end', () => {
    const items = placeProposals(messages.slice(0, 1), [plan('z', 9)]);
    expect(items.at(-1)).toMatchObject({ kind: 'proposal', proposal: { id: 'z' } });
  });
});

describe('statusLine', () => {
  it('says what happened to an earlier plan, in plain words', () => {
    const outcome = { message: '', saved_meals: 3, added_items: 5, skipped: [] };
    expect(statusLine({ status: 'approved', outcome })).toBe(
      'Approved · 3 meals saved, 5 items added',
    );
    expect(
      statusLine({ status: 'approved', outcome: { ...outcome, saved_meals: 1, added_items: 0 } }),
    ).toBe('Approved · 1 meal saved');
    expect(statusLine({ status: 'rejected', outcome: null })).toBe('Rejected');
    expect(statusLine({ status: 'superseded', outcome: null })).toBe('Replaced by a newer plan');
    expect(statusLine({ status: 'expired', outcome: null })).toBe('Expired');
    expect(statusLine({ status: 'pending', outcome: null })).toBe('Waiting for you');
  });
});

describe('keptOf', () => {
  const proposal = {
    status: 'approved' as const,
    meals: [{ date: '2026-11-16' }, { date: '2026-11-17' }],
    list_additions: [{ name: 'eggs' }, { name: 'limes' }],
    outcome: {
      message: '',
      saved_meals: 1,
      added_items: 1,
      skipped: [],
      kept_meals: ['2026-11-17'],
      kept_additions: [1],
    },
  };

  it('shows only what the Member kept on an approved plan', () => {
    const kept = keptOf(proposal);
    expect(kept.meals.map((m) => m.date)).toEqual(['2026-11-17']);
    expect(kept.additions).toEqual([{ item: { name: 'limes' }, index: 1 }]);
  });

  it('shows everything when nothing was recorded or the plan was not approved', () => {
    const old = {
      ...proposal,
      outcome: { ...proposal.outcome, kept_meals: null, kept_additions: undefined },
    };
    expect(keptOf(old).meals).toHaveLength(2);
    expect(keptOf(old).additions).toHaveLength(2);
    expect(keptOf({ ...proposal, status: 'rejected' as const, outcome: null }).meals).toHaveLength(
      2,
    );
  });
});
