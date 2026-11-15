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
