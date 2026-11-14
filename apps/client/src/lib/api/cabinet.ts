/**
 * The Cabinet: server state and changes, same pattern as lists.ts.
 *
 * These changes aren't optimistic. They're usually made at home on good signal, and the
 * server decides things the app shouldn't guess (unit conversion, status). Each change
 * still gets an Idempotency-Key at tap time and goes through the persisted queue, so a
 * flaky connection can't apply it twice or lose it.
 */
import { keepPreviousData, useMutation, useQuery, type QueryClient } from '@tanstack/react-query';
import { randomUUID } from 'expo-crypto';

import { api, ApiError, unwrap } from './client';

export const cabinetKeys = {
  all: ['cabinet'] as const,
  ingredients: (q: string) => ['ingredients', q] as const,
};

const mutationKeys = {
  setTracked: ['cabinet', 'setTracked'] as const,
  removeTracked: ['cabinet', 'removeTracked'] as const,
  setStaple: ['cabinet', 'setStaple'] as const,
  removeStaple: ['cabinet', 'removeStaple'] as const,
};

type Keyed = { idempotencyKey: string };
type SetTrackedVars = Keyed & { ingredientId: string; quantity: string | null };
type IngredientVars = Keyed & { ingredientId: string };
type SetStapleVars = Keyed & { ingredientId: string; have: boolean };

const header = (v: Keyed) => ({ 'Idempotency-Key': v.idempotencyKey });
const scope = { id: 'cabinet' };

function shouldRetry(failureCount: number, error: unknown) {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < 5;
}

export function registerCabinetMutations(queryClient: QueryClient) {
  const settled = {
    retry: shouldRetry,
    onSettled: () => queryClient.invalidateQueries({ queryKey: cabinetKeys.all }),
  };

  queryClient.setMutationDefaults(mutationKeys.setTracked, {
    mutationFn: async (v: SetTrackedVars) =>
      unwrap(
        await api.PUT('/cabinet/items/{ingredient_id}', {
          params: { path: { ingredient_id: v.ingredientId }, header: header(v) },
          body: { quantity: v.quantity },
        }),
      ),
    ...settled,
  });
  queryClient.setMutationDefaults(mutationKeys.removeTracked, {
    mutationFn: async (v: IngredientVars) =>
      unwrap(
        await api.DELETE('/cabinet/items/{ingredient_id}', {
          params: { path: { ingredient_id: v.ingredientId }, header: header(v) },
        }),
      ),
    ...settled,
  });
  queryClient.setMutationDefaults(mutationKeys.setStaple, {
    mutationFn: async (v: SetStapleVars) =>
      unwrap(
        await api.PUT('/cabinet/staples/{ingredient_id}', {
          params: { path: { ingredient_id: v.ingredientId }, header: header(v) },
          body: { have: v.have },
        }),
      ),
    ...settled,
  });
  queryClient.setMutationDefaults(mutationKeys.removeStaple, {
    mutationFn: async (v: IngredientVars) =>
      unwrap(
        await api.DELETE('/cabinet/staples/{ingredient_id}', {
          params: { path: { ingredient_id: v.ingredientId }, header: header(v) },
        }),
      ),
    ...settled,
  });
}

export function useCabinet() {
  return useQuery({
    queryKey: cabinetKeys.all,
    queryFn: async () => unwrap(await api.GET('/cabinet')),
  });
}

/** Search as you type. Keeps the last results on screen while the next ones load. */
export function useIngredientSearch(query: string) {
  const q = query.trim();
  return useQuery({
    queryKey: cabinetKeys.ingredients(q),
    queryFn: async () => unwrap(await api.GET('/ingredients', { params: { query: { q } } })),
    enabled: q.length >= 2,
    placeholderData: keepPreviousData,
    staleTime: 5 * 60_000, // the Ingredient list rarely changes
  });
}

export function useCabinetActions() {
  const setTracked = useMutation<unknown, Error, SetTrackedVars>({
    mutationKey: mutationKeys.setTracked,
    scope,
  });
  const removeTracked = useMutation<unknown, Error, IngredientVars>({
    mutationKey: mutationKeys.removeTracked,
    scope,
  });
  const setStaple = useMutation<unknown, Error, SetStapleVars>({
    mutationKey: mutationKeys.setStaple,
    scope,
  });
  const removeStaple = useMutation<unknown, Error, IngredientVars>({
    mutationKey: mutationKeys.removeStaple,
    scope,
  });

  return {
    error: setTracked.error ?? removeTracked.error ?? setStaple.error ?? removeStaple.error,
    setAmount: (ingredientId: string, quantity: string | null) =>
      setTracked.mutate({ ingredientId, quantity, idempotencyKey: randomUUID() }),
    usedUp: (ingredientId: string) =>
      removeTracked.mutate({ ingredientId, idempotencyKey: randomUUID() }),
    setStaple: (ingredientId: string, have: boolean) =>
      setStaple.mutate({ ingredientId, have, idempotencyKey: randomUUID() }),
    notAStaple: (ingredientId: string) =>
      removeStaple.mutate({ ingredientId, idempotencyKey: randomUUID() }),
  };
}
