/// <reference types="jest" />
import { COURSES, courseName, tapCourse } from './courses';

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

  it('tapping a tile picks it, and tapping it again shows every Course', () => {
    expect(tapCourse(null, 'dessert')).toBe('dessert');
    expect(tapCourse('dessert', 'main')).toBe('main');
    expect(tapCourse('dessert', 'dessert')).toBeNull(); // there's no "All" tile
  });
});

describe('courseName', () => {
  it('names one recipe’s Course in the singular', () => {
    expect(courseName('main')).toBe('Main');
    expect(courseName('side')).toBe('Side');
    expect(courseName('breakfast')).toBe('Breakfast');
  });
});
