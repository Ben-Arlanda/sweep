/// <reference types="jest" />
import { COURSES, courseName, TILES } from './courses';

describe('Course tiles', () => {
  it('lists every Course, mains first, as the screen shows them', () => {
    expect(COURSES.map((c) => c.value)).toEqual(['main', 'side', 'dessert', 'breakfast', 'lunch']);
    expect(COURSES.map((c) => c.label)).toEqual([
      'Mains',
      'Sides',
      'Desserts',
      'Breakfast',
      'Lunch',
    ]);
  });

  it('the tiles are All, then the four big Courses (Lunch shows under All)', () => {
    expect(TILES.map((c) => c.value)).toEqual([null, 'main', 'side', 'dessert', 'breakfast']);
    expect(TILES.map((c) => c.label)).toEqual(['All', 'Mains', 'Sides', 'Desserts', 'Breakfast']);
  });
});

describe('courseName', () => {
  it('names one recipe’s Course in the singular', () => {
    expect(courseName('main')).toBe('Main');
    expect(courseName('side')).toBe('Side');
    expect(courseName('breakfast')).toBe('Breakfast');
  });
});
