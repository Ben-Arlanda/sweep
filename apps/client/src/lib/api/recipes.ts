/**
 * The Recipe Knowledge Base: read-only server state.
 *
 * Browsing pages through recipes by title. Searching asks the server to rank by meaning,
 * so it waits until the person pauses typing (debounce): every search costs an
 * embedding call, and "c", "ch", "chi", "chic" are four wasted ones.
 */
import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import type { Course } from '@/features/recipes/courses';

import { api, ApiError, unwrap } from './client';
import { mealPlanKeys } from './mealPlan';

export const PAGE = 30;

export const recipeKeys = {
  all: ['recipes'] as const,
  browse: (f: RecipeFilters) =>
    ['recipes', 'browse', f.maxMinutes, f.course, f.favourites ?? false] as const,
  search: (q: string, f: RecipeFilters) =>
    ['recipes', 'search', q, f.maxMinutes, f.course, f.favourites ?? false] as const,
  one: (id: string) => ['recipes', 'one', id] as const,
  adaptations: (parentId: string) => ['recipes', 'adaptations', parentId] as const,
};

/** The Recipes screen's chips. `null` means no limit. `favourites`: hearted only. */
export type RecipeFilters = {
  maxMinutes: number | null;
  course: Course | null;
  favourites?: boolean;
};

const query = ({ maxMinutes, course, favourites }: RecipeFilters) => ({
  ...(maxMinutes ? { max_minutes: maxMinutes } : {}),
  ...(course ? { course } : {}),
  ...(favourites ? { favourites: true } : {}),
});

/** All recipes by title, a page at a time. */
export function useRecipeBrowse(filters: RecipeFilters, enabled: boolean) {
  return useInfiniteQuery({
    queryKey: recipeKeys.browse(filters),
    queryFn: async ({ pageParam }) =>
      unwrap(
        await api.GET('/recipes', {
          params: { query: { ...query(filters), limit: PAGE, offset: pageParam } },
        }),
      ),
    initialPageParam: 0,
    // A short page means there's nothing after it.
    getNextPageParam: (last, pages) => (last.length < PAGE ? undefined : pages.length * PAGE),
    enabled,
    staleTime: 10 * 60_000, // Seed Recipes change rarely
  });
}

/** Recipes closest in meaning to `q`, best first. */
export function useRecipeSearch(q: string, filters: RecipeFilters) {
  return useQuery({
    queryKey: recipeKeys.search(q, filters),
    queryFn: async () =>
      unwrap(await api.GET('/recipes', { params: { query: { q, ...query(filters) } } })),
    enabled: q.length >= 2,
    placeholderData: keepPreviousData, // keep old results on screen while new ones load
    staleTime: 10 * 60_000,
  });
}

export function useRecipe(id: string) {
  return useQuery({
    queryKey: recipeKeys.one(id),
    queryFn: async () =>
      unwrap(await api.GET('/recipes/{recipe_id}', { params: { path: { recipe_id: id } } })),
    staleTime: 10 * 60_000,
    // A 4xx (no such recipe, a broken link) will fail the same way every time.
    retry: (failures, error) => !(error instanceof ApiError && error.status < 500) && failures < 3,
  });
}

/**
 * This Household's Adaptations of a recipe, with their Swaps (ADR 0021). Only an
 * approved Proposal makes one, so there's no "create" here. Not `staleTime`d like Seed
 * Recipes: a plan approved in the chat can add one at any moment.
 */
export function useAdaptations(parentId: string, enabled = true) {
  return useQuery({
    queryKey: recipeKeys.adaptations(parentId),
    queryFn: async () =>
      unwrap(
        await api.GET('/recipes/{recipe_id}/adaptations', {
          params: { path: { recipe_id: parentId } },
        }),
      ),
    enabled,
  });
}

/** Any Member may delete an Adaptation. Meals planned with it go too (the database cascades). */
export function useDeleteAdaptation() {
  const queryClient = useQueryClient();
  return useMutation({
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: recipeKeys.all });
      await queryClient.invalidateQueries({ queryKey: mealPlanKeys.all });
    },
    mutationFn: async ({ id, idempotencyKey }: { id: string; idempotencyKey: string }) => {
      unwrap(
        await api.DELETE('/recipes/adaptations/{recipe_id}', {
          params: { path: { recipe_id: id }, header: { 'Idempotency-Key': idempotencyKey } },
        }),
      );
    },
  });
}

/** True when the recipe doesn't exist for this Household (or the link is malformed). */
export function isNotFound(error: unknown) {
  return error instanceof ApiError && (error.status === 404 || error.status === 422);
}

/** `value`, but only once it has stopped changing for `ms`. */
export function useDebounced<T>(value: T, ms = 350): T {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), ms);
    return () => clearTimeout(timer); // typed again before the timer fired: start over
  }, [value, ms]);
  return settled;
}
