import type { components } from '@/lib/api/schema';

export type PlannedMeal = components['schemas']['PlannedMealOut'];
export type Day = { date: string; meal: PlannedMeal | null };

/**
 * "2026-11-30" + 1 → "2026-12-01". Done in UTC on purpose: a calendar date has no time
 * zone, and local time would skip or repeat an hour on daylight-saving days, which can
 * push midnight into the wrong day.
 */
export function addDays(iso: string, days: number): string {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d + days)).toISOString().slice(0, 10);
}

/** The 7 days from `start`, each with its Planned Meal or null, so empty days show too. */
export function weekDays(start: string, meals: PlannedMeal[]): Day[] {
  const byDate = new Map(meals.map((m) => [m.date, m]));
  return Array.from({ length: 7 }, (_, i) => {
    const date = addDays(start, i);
    return { date, meal: byDate.get(date) ?? null };
  });
}

/** ISO weekday of a calendar date: Monday 1 … Sunday 7 (the server stores these). */
export function isoWeekday(iso: string): number {
  const [y, m, d] = iso.split('-').map(Number);
  const js = new Date(Date.UTC(y, m - 1, d)).getUTCDay(); // Sunday 0 … Saturday 6
  return js === 0 ? 7 : js;
}

/** The Monday of the Mon–Sun week a date is in. */
export function mondayOf(iso: string): string {
  return addDays(iso, 1 - isoWeekday(iso));
}

/**
 * The week the "Plan my week" sheet opens on: this one, or next week from Saturday,
 * when this week has at most two dinners left.
 */
export function planWeekFor(today: string): string {
  return isoWeekday(today) >= 6 ? addDays(mondayOf(today), 7) : mondayOf(today);
}

/** Days before today can't be planned (the server refuses them too). */
export function canPick(date: string, today: string): boolean {
  return date >= today; // ISO dates sort as text
}

/**
 * The days the sheet starts with ticked: the Household's usual weekdays in this week,
 * leaving out past days and days that already have a Planned Meal (tick one to replace).
 */
export function pickDays(opts: {
  monday: string;
  weekdays: number[];
  today: string;
  planned: string[];
}): string[] {
  return Array.from({ length: 7 }, (_, i) => addDays(opts.monday, i)).filter(
    (date) =>
      opts.weekdays.includes(isoWeekday(date)) &&
      canPick(date, opts.today) &&
      !opts.planned.includes(date),
  );
}

/**
 * The usual weekdays to remember after the Member picks days. Only days they could
 * actually choose change the pattern: a day left out because it had already gone, or
 * already had a dinner, keeps what was saved before (a planned Monday doesn't mean "we
 * never plan Mondays"). A planned day they ticked to replace counts as picked.
 */
export function nextWeekdays(opts: {
  monday: string;
  today: string;
  planned: string[];
  before: number[];
  picked: string[];
}): number[] {
  return Array.from({ length: 7 }, (_, i) => addDays(opts.monday, i))
    .filter((date) => {
      if (opts.picked.includes(date)) return true;
      const couldChoose = canPick(date, opts.today) && !opts.planned.includes(date);
      return couldChoose ? false : opts.before.includes(isoWeekday(date));
    })
    .map(isoWeekday);
}

const SHORT_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "Wed" and 18 for a date: the Plan tab's day badge. Plain maths, not the phone's locale. */
export function dayParts(iso: string): { weekday: string; day: number; month: string } {
  const [, m, d] = iso.split('-').map(Number);
  return { weekday: SHORT_DAYS[isoWeekday(iso) - 1], day: d, month: MONTHS[m - 1] };
}

/** "Mon 16 – Sun 22 Nov", or "Mon 30 Nov – Sun 6 Dec" across a month. */
export function weekRange(monday: string): string {
  const a = dayParts(monday);
  const b = dayParts(addDays(monday, 6));
  const end = `${b.weekday} ${b.day} ${b.month}`;
  return a.month === b.month
    ? `${a.weekday} ${a.day} – ${end}`
    : `${a.weekday} ${a.day} ${a.month} – ${end}`;
}

/** "16–22 Nov", or "30 Nov – 6 Dec" across a month: short enough for a tab. */
export function shortWeekRange(monday: string): string {
  const a = dayParts(monday);
  const b = dayParts(addDays(monday, 6));
  return a.month === b.month
    ? `${a.day}–${b.day} ${b.month}`
    : `${a.day} ${a.month} – ${b.day} ${b.month}`;
}
