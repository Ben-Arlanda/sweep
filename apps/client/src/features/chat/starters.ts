/**
 * How a plan starts. "Just tonight" (ADR 0013), the "Plan my week" sheet (ADR 0015) and
 * the "Ask Sweep" box on Home leave a one-off request here, then open the chat; the chat takes it (read and clear in
 * one step) and sends the message in a new plan, shown like one the Member typed.
 *
 * From the sheet the request also carries the kind of plan and the days. The chat
 * creates the Conversation with them, so the agent gets them on every turn, not only in
 * this first message.
 *
 * In memory, not in the URL, on purpose: a URL can be reloaded or shared, and each send
 * is a paid model call. A reload starts with nothing pending, so nothing is re-sent.
 */
import type { components } from '@/lib/api/schema';

export type PlanMode = components['schemas']['PlanMode'];
/** What the sheet picked: the kind of plan and the days. */
export type Plan = { mode: PlanMode; days: string[] };
export type Start = { text: string; plan: Plan | null };

let pending: Start | null = null;

/** The "Ask Sweep" box on Home. False when there's nothing to send. */
export function requestAsk(text: string): boolean {
  const words = text.trim();
  if (!words) return false;
  pending = { text: words, plan: null };
  return true;
}

/** "Just tonight" on Home: always Kitchen-first, no sheet. */
export function requestStart(_start: 'tonight'): void {
  pending = { text: "What can I cook tonight with what's in my Kitchen?", plan: null };
}

/** The "Plan my week" sheet, once the Member has picked the days and the kind of plan. */
export function requestPlan(mode: PlanMode, days: string[]): void {
  const sorted = [...days].sort();
  pending = {
    text: planMessage(mode, sorted),
    plan: { mode, days: sorted },
  };
}

/** The requested start, without taking it: for a screen to know on its first render. */
export function peekStart(): Start | null {
  return pending;
}

/** The requested start, once. Later calls return null until another request. */
export function takeStart(): Start | null {
  const start = pending;
  pending = null;
  return start;
}

/** "Plan dinners from what's in my Kitchen, for Mon 16, Tue 17 and Wed 18 Nov." */
export function planMessage(mode: PlanMode, days: string[]): string {
  const what =
    mode === 'kitchen'
      ? `Plan ${days.length === 1 ? 'dinner' : 'dinners'} from what's in my Kitchen`
      : 'Plan new recipes to shop for';
  return `${what}, for ${listDays([...days].sort())}.`;
}

const WEEKDAY = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTH = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "Mon 16, Tue 17 and Wed 18 Nov"; the month is said once per run of days in it. */
function listDays(days: string[]): string {
  const parts = days.map((iso, i) => {
    const [y, m, d] = iso.split('-').map(Number);
    const weekday = WEEKDAY[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
    const next = days[i + 1];
    const monthEnds = !next || next.slice(5, 7) !== iso.slice(5, 7);
    return `${weekday} ${d}${monthEnds ? ` ${MONTH[m - 1]}` : ''}`;
  });
  if (parts.length === 1) return parts[0];
  return `${parts.slice(0, -1).join(', ')} and ${parts.at(-1)}`;
}

/** Tap-to-send ideas on an empty chat. */
export const SUGGESTIONS = [
  "What can I cook tonight with what's in my Kitchen?",
  "Plan 5 dinners from what's in my Kitchen",
  'Three quick vegetarian dinners',
];
