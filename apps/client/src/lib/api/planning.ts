/**
 * The planning screens' server calls (slice 6e, ADR 0025): Dinner Ideas, putting one on a
 * day, swap alternatives for a pending Proposal, and Favourites (hearts).
 *
 * Dinner Ideas and alternatives are plain code on the server: no AI, so they're cheap to
 * refetch. Hearts update the screen straight away and roll back if the server says no.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { randomUUID } from 'expo-crypto';

import { ideaQuery, type IdeaFilter, type IdeaRequest } from '@/features/planning/ideaRequest';

import { api, unwrap } from './client';
import { mealPlanKeys } from './mealPlan';
import { recipeKeys } from './recipes';
import type { components } from './schema';
import { haptic } from '@/lib/haptics';

export type DinnerIdea = components['schemas']['DinnerIdeaOut'];
export type { IdeaFilter } from '@/features/planning/ideaRequest';

export const planningKeys = {
  ideas: (request: IdeaRequest, filter: IdeaFilter, limit: number) =>
    [
      'dinner-ideas',
      request.mood,
      request.q,
      request.lean,
      request.maxMinutes,
      filter,
      limit,
    ] as const,
  allIdeas: ['dinner-ideas'] as const,
  alternatives: (proposalId: string, date: string) => ['alternatives', proposalId, date] as const,
};

/** Dinner Ideas for what the setup asked (or Use my Kitchen) and the chip picked. */
export function useDinnerIdeas(request: IdeaRequest, filter: IdeaFilter, limit = 3) {
  return useQuery({
    queryKey: planningKeys.ideas(request, filter, limit),
    queryFn: async () =>
      unwrap(
        await api.GET('/dinner-ideas', {
          params: { query: { ...ideaQuery(request, filter), limit } },
        }),
      ),
  });
}

/** Put a recipe on a day (a Dinner Idea picked). Planned directly: no Proposal. */
export function usePlanDay() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (v: {
      date: string;
      recipeId: string;
      servings?: number | null;
      idempotencyKey: string;
    }) =>
      unwrap(
        await api.PUT('/meal-plan/days/{day}', {
          params: { path: { day: v.date }, header: { 'Idempotency-Key': v.idempotencyKey } },
          body: { recipe_id: v.recipeId, servings: v.servings ?? null },
        }),
      ),
    onSuccess: haptic.success,
    onSettled: () => queryClient.invalidateQueries({ queryKey: mealPlanKeys.all }),
  });
}

export const planTap = (date: string, recipeId: string, servings: number | null = null) => ({
  date,
  recipeId,
  servings,
  idempotencyKey: randomUUID(),
});

/** What one day of a pending Proposal could be swapped for. */
export function useAlternatives(proposalId: string | null, date: string | null) {
  return useQuery({
    queryKey: planningKeys.alternatives(proposalId ?? '', date ?? ''),
    queryFn: async () =>
      unwrap(
        await api.GET('/proposals/{proposal_id}/alternatives', {
          params: { path: { proposal_id: proposalId ?? '' }, query: { date: date ?? '' } },
        }),
      ),
    enabled: proposalId !== null && date !== null,
  });
}

/**
 * Heart or un-heart a recipe for the Household. Recipe screens and lists read the
 * `favourite` flag, so they're refetched afterwards; the recipe itself flips at once.
 */
export function useFavourite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (v: { recipeId: string; on: boolean }) => {
      const params = { params: { path: { recipe_id: v.recipeId } } };
      unwrap(
        v.on
          ? await api.PUT('/recipes/{recipe_id}/favourite', params)
          : await api.DELETE('/recipes/{recipe_id}/favourite', params),
      );
    },
    onMutate: async (v) => {
      const key = recipeKeys.one(v.recipeId);
      await queryClient.cancelQueries({ queryKey: key });
      const before = queryClient.getQueryData<{ favourite?: boolean }>(key);
      if (before) queryClient.setQueryData(key, { ...before, favourite: v.on });
      return { before };
    },
    onError: (_e, v, context) => {
      if (context?.before) queryClient.setQueryData(recipeKeys.one(v.recipeId), context.before);
    },
    onSettled: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: recipeKeys.all }),
        queryClient.invalidateQueries({ queryKey: planningKeys.allIdeas }),
      ]);
    },
  });
}
