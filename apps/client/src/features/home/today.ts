/**
 * What Home shows today (slice 6c). Plain functions, so every state is easy to test.
 *
 * "Today" is the server's (`GET /meal-plan` returns it), never the phone's clock: a
 * phone in another time zone, or with the wrong time, would show the wrong dinner.
 */
import { addDays, isoWeekday, type PlannedMeal } from '@/features/mealPlan/week';

export type HomeState =
  /** A dinner is planned tonight and not cooked yet. */
  | { kind: 'planned'; tonight: PlannedMeal }
  /** Tonight's dinner is cooked: show it, then tomorrow. `meal` undefined = not loaded. */
  | {
      kind: 'cooked';
      tonight: PlannedMeal;
      tomorrow: { date: string; meal: PlannedMeal | null | undefined };
    }
  /** Nothing tonight, but other days this week are planned. */
  | { kind: 'free' }
  /** Nothing planned this week at all. */
  | { kind: 'empty' };

/** Tomorrow is in next week's Meal Plan only on a Sunday. */
export function needsNextWeek(today: string): boolean {
  return isoWeekday(today) === 7;
}

export function homeState(opts: {
  today: string;
  /** This Mon–Sun week's Planned Meals. */
  thisWeek: PlannedMeal[];
  /** Next week's, only needed on a Sunday. Undefined while loading. */
  nextWeek?: PlannedMeal[];
}): HomeState {
  const { today, thisWeek, nextWeek } = opts;
  const tonight = thisWeek.find((m) => m.date === today);
  if (!tonight) return thisWeek.length > 0 ? { kind: 'free' } : { kind: 'empty' };
  if (tonight.cooked_at === null) return { kind: 'planned', tonight };

  const date = addDays(today, 1);
  const from = needsNextWeek(today) ? nextWeek : thisWeek;
  const meal = from === undefined ? undefined : (from.find((m) => m.date === date) ?? null);
  return { kind: 'cooked', tonight, tomorrow: { date, meal } };
}

/** "rice", "rice and eggs", "a, b and c", "a, b, c and 2 more". */
export function joinNames(names: string[]): string {
  const shown = names.length > 3 ? [...names.slice(0, 3), `${names.length - 3} more`] : names;
  if (shown.length <= 1) return shown.join('');
  return `${shown.slice(0, -1).join(', ')} and ${shown[shown.length - 1]}`;
}

/**
 * The line under tonight's dinner. Before Cooked: what it uses from the Kitchen. After:
 * what Cooked took out (the server sends that once it's cooked, see `kitchen_uses`).
 */
export function usesLine(meal: PlannedMeal): string {
  const serves = `Serves ${meal.servings}`;
  if (meal.kitchen_uses.length === 0) return serves;
  const names = joinNames(meal.kitchen_uses);
  return meal.cooked_at === null
    ? `${serves} · uses your ${names}`
    : `Taken out of your Kitchen: ${names}`;
}
