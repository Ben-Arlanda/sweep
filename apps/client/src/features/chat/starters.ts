/**
 * How a plan starts (ADR 0013). Home's "Plan my week" and "Just tonight" open the chat
 * with `?start=week` or `?start=tonight`; the chat sends the matching message in a new
 * plan, shown like one the Member typed. Plans start from the Kitchen, so the words do.
 */

const STARTERS: Record<string, string> = {
  week: "Plan dinners for this week from what's in my Kitchen.",
  tonight: "What can I cook tonight with what's in my Kitchen?",
};

/** The first message for a `start` route param, or null if it isn't one we know. */
export function starterMessage(start: string | string[] | undefined): string | null {
  if (typeof start !== 'string') return null;
  return Object.hasOwn(STARTERS, start) ? STARTERS[start] : null;
}

/** Tap-to-send ideas on an empty chat. */
export const SUGGESTIONS = [
  "What can I cook tonight with what's in my Kitchen?",
  "Plan 5 dinners from what's in my Kitchen",
  'Three quick vegetarian dinners',
];
