/**
 * Courses (see CONTEXT.md): what a recipe is for. Every recipe has exactly one. Plans
 * only offer mains, because a Planned Meal is a dinner; the Recipes screen lets you
 * browse the rest.
 */
import type { components } from '@/lib/api/schema';

export type Course = components['schemas']['Course'];

/** In screen order, with the plural the filter tiles show. */
export const COURSES: { value: Course; label: string; one: string }[] = [
  { value: 'main', label: 'Mains', one: 'Main' },
  { value: 'side', label: 'Sides', one: 'Side' },
  { value: 'dessert', label: 'Desserts', one: 'Dessert' },
  { value: 'breakfast', label: 'Breakfast', one: 'Breakfast' },
  { value: 'lunch', label: 'Lunch', one: 'Lunch' },
];

/** One recipe's Course, for a meta line ("Side · 25 min"). */
export function courseName(course: Course): string {
  return COURSES.find((c) => c.value === course)?.one ?? course;
}

/** The All recipes tiles (slice 6f): All, then the four big Courses. Lunch shows under All. */
export const TILES: { value: Course | null; label: string }[] = [
  { value: null, label: 'All' },
  ...COURSES.filter((c) => c.value !== 'lunch'),
];
