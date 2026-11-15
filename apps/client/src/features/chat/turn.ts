/**
 * One turn of the chat while it streams: what the Member sent, and what has come back.
 *
 * `turnReducer` is a pure function from (turn so far, next event) to the new turn, so
 * the screen just feeds it events and the logic is tested without React or a network.
 *
 * Narration vs reply: Claude sometimes writes a short note right before calling a tool
 * ("Pick dhal (quick)."). We can't tell it's a note until the tool event arrives, so
 * text collects in `reply`, and a tool event moves it to `narration`, shown as a
 * passing status. The server uses the same rule when it rebuilds the transcript.
 */
import type { components } from '@/lib/api/schema';

import type { TurnEvent } from './sse';

export type Draft = components['schemas']['DraftOut'];
export type Proposal = components['schemas']['ProposalOut'];

export type Turn = {
  userText: string;
  reply: string;
  narration: string | null;
  /** What the agent is doing right now, in plain words. Null when it's not using a tool. */
  activity: string | null;
  draft: Draft | null;
  proposal: Proposal | null;
  status: 'streaming' | 'done' | 'error';
  error: string | null;
};

export function startTurn(userText: string): Turn {
  return {
    userText,
    reply: '',
    narration: null,
    activity: 'Thinking',
    draft: null,
    proposal: null,
    status: 'streaming',
    error: null,
  };
}

const ACTIVITY: Record<string, string> = {
  search_recipes: 'Searching recipes',
  get_recipe: 'Reading a recipe',
  get_kitchen: 'Checking your Kitchen',
  get_household_preferences: 'Checking your Preferences',
  get_shopping_list: 'Checking your Shopping List',
  check_kitchen_coverage: "Working out what you'd need to buy",
  set_planned_meal: 'Adding a meal',
  remove_planned_meal: 'Removing a meal',
  set_list_additions: 'Updating the Shopping List additions',
  propose_plan: 'Checking the plan against your Dietary Rules',
};

export function turnReducer(turn: Turn, event: TurnEvent): Turn {
  switch (event.type) {
    case 'text':
      return { ...turn, reply: turn.reply + event.text, activity: null };
    case 'tool':
      return {
        ...turn,
        narration: turn.reply.trim() || turn.narration,
        reply: '',
        activity: ACTIVITY[event.name] ?? 'Working',
      };
    case 'draft':
      return { ...turn, draft: event.draft };
    case 'replan':
      return { ...turn, activity: 'Fixing a problem with the plan' };
    case 'proposal':
      return { ...turn, proposal: event.proposal };
    case 'done':
      return { ...turn, status: 'done', activity: null };
    case 'error':
      return { ...turn, status: 'error', activity: null, error: event.message };
  }
}
