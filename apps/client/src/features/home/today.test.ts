import type { PlannedMeal } from '@/features/mealPlan/week';

import { homeState, joinNames, needsNextWeek, usesLine } from './today';

// Wed 18 Nov 2026; its week is Mon 16 – Sun 22.
const WED = '2026-11-18';

const meal = (date: string, extra: Partial<PlannedMeal> = {}): PlannedMeal => ({
  id: `id-${date}`,
  date,
  recipe_id: 'r1',
  title: `Dinner ${date}`,
  servings: 4,
  cooked_at: null,
  cooked_by: null,
  kitchen_uses: [],
  ...extra,
});
const cooked = (date: string) => meal(date, { cooked_at: '2026-11-18T09:00:00Z' });

describe('homeState', () => {
  it('shows tonight when a dinner is planned for today', () => {
    const state = homeState({ today: WED, thisWeek: [meal('2026-11-16'), meal(WED)] });
    expect(state).toEqual({ kind: 'planned', tonight: meal(WED) });
  });

  it('after Cooked, it moves on to tomorrow', () => {
    const tomorrow = meal('2026-11-19');
    expect(homeState({ today: WED, thisWeek: [cooked(WED), tomorrow] })).toEqual({
      kind: 'cooked',
      tonight: cooked(WED),
      tomorrow: { date: '2026-11-19', meal: tomorrow },
    });
    expect(homeState({ today: WED, thisWeek: [cooked(WED)] })).toMatchObject({
      tomorrow: { date: '2026-11-19', meal: null },
    });
  });

  it("on a Sunday, tomorrow is in next week's plan", () => {
    const sun = '2026-11-22';
    const monday = meal('2026-11-23');
    expect(homeState({ today: sun, thisWeek: [cooked(sun)], nextWeek: [monday] })).toMatchObject({
      tomorrow: { date: '2026-11-23', meal: monday },
    });
    // Next week not loaded yet: tomorrow is unknown, not "nothing planned".
    expect(homeState({ today: sun, thisWeek: [cooked(sun)] })).toMatchObject({
      tomorrow: { date: '2026-11-23', meal: undefined },
    });
  });

  it('nothing tonight but other days planned is "free"; a bare week is "empty"', () => {
    expect(homeState({ today: WED, thisWeek: [meal('2026-11-16')] })).toEqual({ kind: 'free' });
    expect(homeState({ today: WED, thisWeek: [] })).toEqual({ kind: 'empty' });
  });
});

describe('needsNextWeek', () => {
  it('only on Sunday, when tomorrow is in the next week', () => {
    expect(needsNextWeek('2026-11-22')).toBe(true);
    expect(needsNextWeek(WED)).toBe(false);
  });
});

describe('joinNames', () => {
  it('reads like a sentence and stops after three', () => {
    expect(joinNames(['rice'])).toBe('rice');
    expect(joinNames(['rice', 'eggs'])).toBe('rice and eggs');
    expect(joinNames(['chicken thigh', 'rice', 'broccoli'])).toBe(
      'chicken thigh, rice and broccoli',
    );
    expect(joinNames(['a', 'b', 'c', 'd', 'e'])).toBe('a, b, c and 2 more');
  });
});

describe('usesLine', () => {
  it('says what a planned dinner uses from the Kitchen', () => {
    expect(usesLine(meal(WED, { kitchen_uses: ['chicken thigh', 'rice'] }))).toBe(
      'Serves 4 · uses your chicken thigh and rice',
    );
    expect(usesLine(meal(WED))).toBe('Serves 4');
  });

  it('once cooked, says what was taken out', () => {
    expect(usesLine({ ...cooked(WED), kitchen_uses: ['rice'] })).toBe(
      'Taken out of your Kitchen: rice',
    );
    expect(usesLine(cooked(WED))).toBe('Serves 4');
  });
});
