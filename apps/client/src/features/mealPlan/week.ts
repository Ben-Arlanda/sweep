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
