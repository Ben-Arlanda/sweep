/**
 * A recipe's two views of one method (ADR 0028): the Detailed View (Recipe Stages, each
 * with its minutes) and the Quick View (3–6 short steps). Seed Recipes have both;
 * Imported Recipes only the Quick View. Cook Mode steps through whichever is showing.
 */
import type { components } from '@/lib/api/schema';

import { courseName, type Course } from './courses';
import { minutesText } from './kitchenMatch';

type Stage = components['schemas']['RecipeStageOut'];

export type MethodView = 'detailed' | 'quick';

export function isMethodView(value: unknown): value is MethodView {
  return value === 'detailed' || value === 'quick';
}

/** The views this recipe has, the default first. */
export function viewsOf(recipe: { stages: Stage[] | null }): MethodView[] {
  return recipe.stages?.length ? ['detailed', 'quick'] : ['quick'];
}

export type CookStep = { stage: string | null; text: string };

/** Every step of the chosen view, in order. Falls back to Quick when there are no stages. */
export function cookSteps(
  recipe: { method: string[] | null; stages: Stage[] | null },
  view: MethodView,
): CookStep[] {
  if (view === 'detailed' && recipe.stages?.length) {
    return recipe.stages.flatMap((s) => s.steps.map((text) => ({ stage: s.title, text })));
  }
  return (recipe.method ?? []).map((text) => ({ stage: null, text }));
}

/** "Prep 20 min · Cook 2 h 35 min · Serves 4 · Main", or the total when it's all we have. */
export function metaParts(recipe: {
  prep_minutes: number | null;
  cook_minutes: number | null;
  total_minutes: number | null;
  servings: number;
  course: Course;
}): string[] {
  const split = recipe.prep_minutes !== null && recipe.cook_minutes !== null;
  const times = split
    ? [
        recipe.prep_minutes ? `Prep ${minutesText(recipe.prep_minutes)}` : null,
        recipe.cook_minutes ? `Cook ${minutesText(recipe.cook_minutes)}` : null,
      ]
    : [recipe.total_minutes ? minutesText(recipe.total_minutes) : null];
  return [...times, `Serves ${recipe.servings}`, courseName(recipe.course)].filter(
    (part): part is string => Boolean(part),
  );
}
