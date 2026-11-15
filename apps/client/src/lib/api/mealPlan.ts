/**
 * The Meal Plan: a week of Planned Meals, removing one, and Mark as Cooked (with undo).
 *
 * Unlike the list and the Kitchen, these changes aren't saved to the offline queue.
 * They're occasional taps, and Cooked changes the Kitchen in ways the app can't guess,
 * so they should happen now or fail visibly. Each still gets an Idempotency-Key at tap
 * time, so TanStack's own retries (same variables, same key) can't apply it twice.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { randomUUID } from 'expo-crypto';

import { api, ApiError, unwrap } from './client';
import { kitchenKeys } from './kitchen';

export const mealPlanKeys = {
  all: ['meal-plan'] as const,
  /** `null` = the week from today, as the server counts it (Sydney time). */
  week: (start: string | null) => ['meal-plan', start ?? 'today'] as const,
};

export function useMealPlan(start: string | null) {
  return useQuery({
    queryKey: mealPlanKeys.week(start),
    queryFn: async () =>
      unwrap(await api.GET('/meal-plan', { params: { query: start ? { start } : {} } })),
  });
}

type MealVars = { mealId: string; idempotencyKey: string };

/** Make the variables at tap time: the key must be the same on every retry of one tap. */
export const mealTap = (mealId: string): MealVars => ({ mealId, idempotencyKey: randomUUID() });

function retryServerErrors(failureCount: number, error: Error) {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < 3;
}

export function useMealPlanActions() {
  const queryClient = useQueryClient();
  const refresh = (kitchenToo: boolean) => async () => {
    await queryClient.invalidateQueries({ queryKey: mealPlanKeys.all });
    // Cooked takes the recipe's amounts out of the Kitchen; undo puts them back.
    if (kitchenToo) await queryClient.invalidateQueries({ queryKey: kitchenKeys.all });
  };
  const opts = { retry: retryServerErrors };
  const header = (v: MealVars) => ({ 'Idempotency-Key': v.idempotencyKey });

  const cooked = useMutation({
    ...opts,
    onSettled: refresh(true),
    mutationFn: async (v: MealVars) =>
      unwrap(
        await api.POST('/planned-meals/{meal_id}/cooked', {
          params: { path: { meal_id: v.mealId }, header: header(v) },
        }),
      ),
  });
  const undoCooked = useMutation({
    ...opts,
    onSettled: refresh(true),
    mutationFn: async (v: MealVars) =>
      unwrap(
        await api.DELETE('/planned-meals/{meal_id}/cooked', {
          params: { path: { meal_id: v.mealId }, header: header(v) },
        }),
      ),
  });
  const remove = useMutation<void, Error, MealVars>({
    ...opts,
    onSettled: refresh(false),
    mutationFn: async (v) => {
      unwrap(
        await api.DELETE('/planned-meals/{meal_id}', {
          params: { path: { meal_id: v.mealId }, header: header(v) },
        }),
      );
    },
  });
  return { cooked, undoCooked, remove };
}
