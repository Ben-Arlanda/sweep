/**
 * How a plan starts (ADR 0013). Home's "Plan my week" and "Just tonight" leave a one-off
 * request here, then open the chat; the chat takes it (read and clear in one step) and
 * sends the message in a new plan, shown like one the Member typed.
 *
 * In memory, not in the URL, on purpose: a URL can be reloaded or shared, and each send
 * is a paid model call. A reload starts with nothing pending, so nothing is re-sent.
 */

export type Start = 'week' | 'tonight';

const MESSAGES: Record<Start, string> = {
  week: "Plan this week's dinners, using what's in my Kitchen first.",
  tonight: "What can I cook tonight with what's in my Kitchen?",
};

let pending: string | null = null;

/** Called by a Home button just before it opens the chat. */
export function requestStart(start: Start): void {
  pending = MESSAGES[start];
}

/** The requested first message, once. Later calls return null until another request. */
export function takeStart(): string | null {
  const message = pending;
  pending = null;
  return message;
}

/** Tap-to-send ideas on an empty chat. */
export const SUGGESTIONS = [
  "What can I cook tonight with what's in my Kitchen?",
  "Plan 5 dinners from what's in my Kitchen",
  'Three quick vegetarian dinners',
];
