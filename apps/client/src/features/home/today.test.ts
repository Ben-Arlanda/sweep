import type { PlannedMeal } from '@/features/mealPlan/week';

import { hasPlan, homeCta, homeState, joinNames, needsNextWeek, usesLine } from './today';

// Wed 18 Nov 2026; its week is Mon 16 – Sun 22.
const WED = '2026-11-18';

const meal = (date: string, extra: Partial<PlannedMeal> = {}): PlannedMeal => ({
  id: `id-${date}`,
  date,
  recipe_id: 'r1',
  title: `Dinner ${date}`,
  servings: 4,
  total_minutes: 25,
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

describe('hasPlan', () => {
  it('is a plan once a day other than today has a dinner', () => {
    expect(hasPlan(WED, [])).toBe(false);
    expect(hasPlan(WED, [meal(WED)])).toBe(false); // just tonight: the Tonight card
    expect(hasPlan(WED, [meal(WED), meal('2026-11-19')])).toBe(true);
    expect(hasPlan(WED, [meal('2026-11-16')])).toBe(true);
  });
});

describe('homeCta', () => {
  const FRI = '2026-11-20';
  const SAT = '2026-11-21';
  const week = [meal('2026-11-16'), meal('2026-11-17')];

  it('is Plan my week before there is a plan', () => {
    expect(homeCta({ today: WED, thisWeek: [meal(WED)] })).toEqual({
      label: 'Plan my week',
      week: '2026-11-16',
    });
  });

  it('opens on next week from Saturday when nothing is planned (as the sheet does)', () => {
    expect(homeCta({ today: SAT, thisWeek: [] })).toEqual({
      label: 'Plan my week',
      week: '2026-11-23',
    });
  });

  it('is Edit my week once there is a plan, for this week', () => {
    expect(homeCta({ today: WED, thisWeek: week })).toEqual({
      label: 'Edit my week',
      week: '2026-11-16',
    });
  });

  it('is Plan next week from Friday when next week is still empty', () => {
    expect(homeCta({ today: FRI, thisWeek: week, nextWeek: [] })).toEqual({
      label: 'Plan next week',
      week: '2026-11-23',
    });
  });

  it('goes back to Edit my week once next week has a dinner', () => {
    expect(homeCta({ today: FRI, thisWeek: week, nextWeek: [meal('2026-11-24')] })).toMatchObject({
      label: 'Edit my week',
    });
  });

  it("says Edit my week while next week is loading, so it doesn't guess", () => {
    expect(homeCta({ today: FRI, thisWeek: week })).toMatchObject({ label: 'Edit my week' });
  });
});
