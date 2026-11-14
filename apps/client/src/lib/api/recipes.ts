/**
 * The Recipe Knowledge Base: read-only server state.
 *
 * Browsing pages through recipes by title. Searching asks the server to rank by meaning,
 * so it waits until the person pauses typing (debounce): every search costs an
 * embedding call, and "c", "ch", "chi", "chic" are four wasted ones.
 */
import { keepPreviousData, useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import { api, ApiError, unwrap } from './client';

export const PAGE = 30;

export const recipeKeys = {
  all: ['recipes'] as const,
  browse: (maxMinutes: number | null) => ['recipes', 'browse', maxMinutes] as const,
  search: (q: string, maxMinutes: number | null) => ['recipes', 'search', q, maxMinutes] as const,
  one: (id: string) => ['recipes', 'one', id] as const,
};

const query = (maxMinutes: number | null) => (maxMinutes ? { max_minutes: maxMinutes } : {});

/** All recipes by title, a page at a time. */
export function useRecipeBrowse(maxMinutes: number | null, enabled: boolean) {
  return useInfiniteQuery({
    queryKey: recipeKeys.browse(maxMinutes),
    queryFn: async ({ pageParam }) =>
      unwrap(
        await api.GET('/recipes', {
          params: { query: { ...query(maxMinutes), limit: PAGE, offset: pageParam } },
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
export function useRecipeSearch(q: string, maxMinutes: number | null) {
  return useQuery({
    queryKey: recipeKeys.search(q, maxMinutes),
    queryFn: async () =>
      unwrap(await api.GET('/recipes', { params: { query: { q, ...query(maxMinutes) } } })),
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
