import { addDays, weekDays } from './week';

const meal = (date: string, title: string) => ({
  id: `id-${date}`,
  date,
  recipe_id: 'r1',
  title,
  servings: 4,
  cooked_at: null,
  cooked_by: null,
});

describe('addDays', () => {
  it('moves forward and back across months and years', () => {
    expect(addDays('2026-11-30', 1)).toBe('2026-12-01');
    expect(addDays('2026-12-28', 7)).toBe('2027-01-04');
    expect(addDays('2026-03-01', -1)).toBe('2026-02-28');
  });

  it('is not thrown off by daylight saving (Sydney springs forward on 4 Oct 2026)', () => {
    expect(addDays('2026-10-03', 1)).toBe('2026-10-04');
    expect(addDays('2026-10-04', 1)).toBe('2026-10-05');
  });
});

describe('weekDays', () => {
  it('gives all 7 days from start, with empty days as null', () => {
    const days = weekDays('2026-11-15', [meal('2026-11-17', 'Dhal'), meal('2026-11-15', 'Tacos')]);
    expect(days.map((d) => d.date)).toEqual([
      '2026-11-15',
      '2026-11-16',
      '2026-11-17',
      '2026-11-18',
      '2026-11-19',
      '2026-11-20',
      '2026-11-21',
    ]);
    expect(days.map((d) => d.meal?.title ?? null)).toEqual([
      'Tacos',
      null,
      'Dhal',
      null,
      null,
      null,
      null,
    ]);
  });

  it('ignores meals outside the week', () => {
    const days = weekDays('2026-11-15', [meal('2026-11-22', 'Late')]);
    expect(days.every((d) => d.meal === null)).toBe(true);
  });
});
