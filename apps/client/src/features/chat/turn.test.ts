import type { TurnEvent } from './sse';
import { startTurn, turnReducer, type Turn } from './turn';

const play = (events: TurnEvent[]): Turn => events.reduce(turnReducer, startTurn('plan dinners'));

const draft = {
  meals: { '2026-11-16': { recipe_id: 'r1', servings: 2, title: 'Dhal' } },
  list_additions: [],
};

describe('turnReducer', () => {
  it('builds the reply from text pieces', () => {
    const turn = play([
      { type: 'text', text: 'Hi ' },
      { type: 'text', text: 'there' },
      { type: 'done' },
    ]);
    expect(turn.reply).toBe('Hi there');
    expect(turn.status).toBe('done');
    expect(turn.activity).toBeNull();
  });

  it('turns text written before a tool call into narration, not reply', () => {
    const turn = play([
      { type: 'text', text: 'Checking your Cabinet.' },
      { type: 'tool', name: 'get_cabinet' },
    ]);
    expect(turn.reply).toBe('');
    expect(turn.narration).toBe('Checking your Cabinet.');
    expect(turn.activity).toBe('Checking your Cabinet');
  });

  it('keeps only the text after the last tool call as the reply', () => {
    const turn = play([
      { type: 'text', text: 'Pick dhal.' },
      { type: 'tool', name: 'set_planned_meal' },
      { type: 'draft', draft },
      { type: 'text', text: 'Dhal on Monday. Anything else?' },
      { type: 'done' },
    ]);
    expect(turn.reply).toBe('Dhal on Monday. Anything else?');
    expect(turn.draft).toEqual(draft);
  });

  it('labels unknown tools generically', () => {
    expect(play([{ type: 'tool', name: 'something_new' }]).activity).toBe('Working');
  });

  it('notes a replan', () => {
    const turn = play([{ type: 'replan', problems: ['Monday breaks a Dietary Rule'] }]);
    expect(turn.activity).toBe('Fixing a problem with the plan');
  });

  it('keeps the Proposal and the error message', () => {
    const proposal = {
      summary: 'Dhal for Monday.',
      meals: [{ date: '2026-11-16', recipe_id: 'r1', title: 'Dhal', servings: 2 }],
      list_additions: [],
      check_label: [],
      dropped: [],
    };
    expect(play([{ type: 'proposal', proposal }, { type: 'done' }]).proposal).toEqual(proposal);

    const failed = play([{ type: 'error', message: 'Still answering your last message.' }]);
    expect(failed.status).toBe('error');
    expect(failed.error).toBe('Still answering your last message.');
  });
});
