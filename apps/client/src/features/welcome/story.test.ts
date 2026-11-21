import { shownAt } from './loop';
import { STORY } from './story';

describe('STORY', () => {
  it('walks through the six built features in app order', () => {
    expect(STORY.map((s) => s.key)).toEqual(['snap', 'ideas', 'recipes', 'plan', 'list', 'sync']);
  });

  it('only promises features a new user can try (no Coming soon pages)', () => {
    for (const page of STORY) expect(page).not.toHaveProperty('upcoming');
  });
});

describe('shownAt', () => {
  it('is hidden before its window opens', () => {
    expect(shownAt(0.1, 0.2, 0.8)).toBe(0);
  });

  it('is fully shown inside its window', () => {
    expect(shownAt(0.5, 0.2, 0.8)).toBe(1);
  });

  it('fades in over the first part of the window', () => {
    expect(shownAt(0.23, 0.2, 0.8, 0.06)).toBeCloseTo(0.5);
  });

  it('fades out at the end and is gone after', () => {
    expect(shownAt(0.77, 0.2, 0.8, 0.06)).toBeCloseTo(0.5);
    expect(shownAt(0.9, 0.2, 0.8)).toBe(0);
  });
});
