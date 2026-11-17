/**
 * The Kitchen: server state and changes, same pattern as lists.ts.
 *
 * These changes aren't optimistic. They're usually made at home on good signal, and the
 * server decides things the app shouldn't guess (unit conversion, status). Each change
 * still gets an Idempotency-Key at tap time and goes through the persisted queue, so a
 * flaky connection can't apply it twice or lose it.
 */
import { keepPreviousData, useMutation, useQuery, type QueryClient } from '@tanstack/react-query';
import { randomUUID } from 'expo-crypto';

import { api, ApiError, unwrap } from './client';
import { listKeys } from './lists';
import type { components } from './schema';

type Place = components['schemas']['Place'];

export const kitchenKeys = {
  all: ['kitchen'] as const,
  ingredients: (q: string) => ['ingredients', q] as const,
};

const mutationKeys = {
  setTracked: ['kitchen', 'setTracked'] as const,
  removeTracked: ['kitchen', 'removeTracked'] as const,
  setStaple: ['kitchen', 'setStaple'] as const,
  removeStaple: ['kitchen', 'removeStaple'] as const,
  setPlace: ['kitchen', 'setPlace'] as const,
  addNew: ['kitchen', 'addNew'] as const,
  setStock: ['kitchen', 'setStock'] as const,
  setStapleAmount: ['kitchen', 'setStapleAmount'] as const,
  toList: ['kitchen', 'toList'] as const,
  unlist: ['kitchen', 'unlist'] as const,
};

type Keyed = { idempotencyKey: string };
type SetTrackedVars = Keyed & { ingredientId: string; quantity: string | null; unit?: string };
type IngredientVars = Keyed & { ingredientId: string };
type SetStapleVars = Keyed & { ingredientId: string; have: boolean };
type SetPlaceVars = Keyed & { ingredientId: string; place: Place | null };
// Two requests, so two keys, both made at tap time: a retry repeats each one safely.
type AddNewVars = { name: string; createKey: string; setKey: string };
type UnlistVars = Keyed & { listId: string; itemId: string };
export type Stock = components['schemas']['SetStockIn']['stock'];
type SetStockVars = Keyed & { ingredientId: string; stock: Stock };
export type StockOut = components['schemas']['StockOut'];
export type OnListOut = components['schemas']['OnListOut'];

const header = (v: Keyed) => ({ 'Idempotency-Key': v.idempotencyKey });
const scope = { id: 'kitchen' };

function shouldRetry(failureCount: number, error: unknown) {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < 5;
}

export function registerKitchenMutations(queryClient: QueryClient) {
  const settled = {
    retry: shouldRetry,
    onSettled: () => queryClient.invalidateQueries({ queryKey: kitchenKeys.all }),
  };

  queryClient.setMutationDefaults(mutationKeys.setTracked, {
    mutationFn: async (v: SetTrackedVars) =>
      unwrap(
        await api.PUT('/kitchen/items/{ingredient_id}', {
          params: { path: { ingredient_id: v.ingredientId }, header: header(v) },
          body: { quantity: v.quantity, unit: v.unit ?? null },
        }),
      ),
    ...settled,
  });
  queryClient.setMutationDefaults(mutationKeys.setStapleAmount, {
    mutationFn: async (v: SetTrackedVars) =>
      unwrap(
        await api.PUT('/kitchen/staples/{ingredient_id}/amount', {
          params: { path: { ingredient_id: v.ingredientId }, header: header(v) },
          body: { quantity: v.quantity, unit: v.unit ?? null },
        }),
      ),
    ...settled,
  });
  queryClient.setMutationDefaults(mutationKeys.removeTracked, {
    mutationFn: async (v: IngredientVars) =>
      unwrap(
        await api.DELETE('/kitchen/items/{ingredient_id}', {
          params: { path: { ingredient_id: v.ingredientId }, header: header(v) },
        }),
      ),
    ...settled,
  });
  queryClient.setMutationDefaults(mutationKeys.setStaple, {
    mutationFn: async (v: SetStapleVars) =>
      unwrap(
        await api.PUT('/kitchen/staples/{ingredient_id}', {
          params: { path: { ingredient_id: v.ingredientId }, header: header(v) },
          body: { have: v.have },
        }),
      ),
    ...settled,
  });
  queryClient.setMutationDefaults(mutationKeys.removeStaple, {
    mutationFn: async (v: IngredientVars) =>
      unwrap(
        await api.DELETE('/kitchen/staples/{ingredient_id}', {
          params: { path: { ingredient_id: v.ingredientId }, header: header(v) },
        }),
      ),
    ...settled,
  });
  queryClient.setMutationDefaults(mutationKeys.setPlace, {
    mutationFn: async (v: SetPlaceVars) =>
      unwrap(
        await api.PUT('/kitchen/places/{ingredient_id}', {
          params: { path: { ingredient_id: v.ingredientId }, header: header(v) },
          body: { place: v.place },
        }),
      ),
    ...settled,
  });

  // Stock status (ADR 0024). A Staple set to Out also lands on the list, so refresh both.
  const kitchenAndList = {
    retry: shouldRetry,
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: kitchenKeys.all });
      void queryClient.invalidateQueries({ queryKey: listKeys.all });
    },
  };
  queryClient.setMutationDefaults(mutationKeys.setStock, {
    mutationFn: async (v: SetStockVars) =>
      unwrap(
        await api.PUT('/kitchen/stock/{ingredient_id}', {
          params: { path: { ingredient_id: v.ingredientId }, header: header(v) },
          body: { stock: v.stock },
        }),
      ),
    ...kitchenAndList,
  });
  queryClient.setMutationDefaults(mutationKeys.toList, {
    mutationFn: async (v: IngredientVars) =>
      unwrap(
        await api.POST('/kitchen/to-list/{ingredient_id}', {
          params: { path: { ingredient_id: v.ingredientId }, header: header(v) },
        }),
      ),
    ...kitchenAndList,
  });
  // Undo's half on the list: take off the item a status change or Add to list added.
  queryClient.setMutationDefaults(mutationKeys.unlist, {
    mutationFn: async (v: UnlistVars) =>
      unwrap(
        await api.DELETE('/lists/{list_id}/items/{item_id}', {
          params: { path: { list_id: v.listId, item_id: v.itemId }, header: header(v) },
        }),
      ),
    ...kitchenAndList,
  });

  // "Add 'kale'": find or create the Household Ingredient, then put it in the Kitchen.
  queryClient.setMutationDefaults(mutationKeys.addNew, {
    mutationFn: async (v: AddNewVars) => {
      const ingredient = unwrap(
        await api.POST('/ingredients', {
          params: { header: { 'Idempotency-Key': v.createKey } },
          body: { name: v.name },
        }),
      );
      return unwrap(
        await api.PUT('/kitchen/items/{ingredient_id}', {
          params: {
            path: { ingredient_id: ingredient.id },
            header: { 'Idempotency-Key': v.setKey },
          },
          body: { quantity: null },
        }),
      );
    },
    retry: shouldRetry,
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: kitchenKeys.all });
      // Search results are cached for minutes; the new Ingredient should show up now.
      void queryClient.invalidateQueries({ queryKey: ['ingredients'] });
    },
  });
}

export function useKitchen() {
  return useQuery({
    queryKey: kitchenKeys.all,
    queryFn: async () => unwrap(await api.GET('/kitchen')),
  });
}

/** Search as you type. Keeps the last results on screen while the next ones load. */
export function useIngredientSearch(query: string) {
  const q = query.trim();
  return useQuery({
    queryKey: kitchenKeys.ingredients(q),
    queryFn: async () => unwrap(await api.GET('/ingredients', { params: { query: { q } } })),
    enabled: q.length >= 2,
    placeholderData: keepPreviousData,
    staleTime: 5 * 60_000, // the Ingredient list rarely changes
  });
}

export function useKitchenActions() {
  const setTracked = useMutation<unknown, Error, SetTrackedVars>({
    mutationKey: mutationKeys.setTracked,
    scope,
  });
  const setStapleAmount = useMutation<unknown, Error, SetTrackedVars>({
    mutationKey: mutationKeys.setStapleAmount,
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
  const setPlace = useMutation<unknown, Error, SetPlaceVars>({
    mutationKey: mutationKeys.setPlace,
    scope,
  });
  const addNew = useMutation<unknown, Error, AddNewVars>({
    mutationKey: mutationKeys.addNew,
    scope,
  });
  const setStock = useMutation<StockOut, Error, SetStockVars>({
    mutationKey: mutationKeys.setStock,
    scope,
  });
  const toList = useMutation<OnListOut, Error, IngredientVars>({
    mutationKey: mutationKeys.toList,
    scope,
  });
  const unlist = useMutation<unknown, Error, UnlistVars>({
    mutationKey: mutationKeys.unlist,
    scope,
  });

  return {
    error:
      setTracked.error ??
      setStapleAmount.error ??
      removeTracked.error ??
      setStaple.error ??
      removeStaple.error ??
      setPlace.error ??
      addNew.error ??
      setStock.error ??
      toList.error ??
      unlist.error,
    /** A Non-staple's amount; `unit` (kg, L…) is converted by the server. */
    setAmount: (ingredientId: string, quantity: string | null, unit?: string) =>
      setTracked.mutate({ ingredientId, quantity, unit, idempotencyKey: randomUUID() }),
    /** A Staple's amount: a note only (ADR 0024). */
    setStapleAmount: (ingredientId: string, quantity: string | null, unit?: string) =>
      setStapleAmount.mutate({ ingredientId, quantity, unit, idempotencyKey: randomUUID() }),
    /** In stock / Running low / Out. Resolves with where a Staple went on the list. */
    setStock: (ingredientId: string, stock: Stock) =>
      setStock.mutateAsync({ ingredientId, stock, idempotencyKey: randomUUID() }),
    /** "Add to list" for a Kitchen item. Resolves with where it went, for Undo. */
    toList: (ingredientId: string) =>
      toList.mutateAsync({ ingredientId, idempotencyKey: randomUUID() }),
    /** "It isn't here" (a misread photo): out of the Kitchen, not onto the list. */
    remove: (ingredientId: string) =>
      removeTracked.mutate({ ingredientId, idempotencyKey: randomUUID() }),
    unlist: (listId: string, itemId: string) =>
      unlist.mutate({ listId, itemId, idempotencyKey: randomUUID() }),
    setStaple: (ingredientId: string, have: boolean) =>
      setStaple.mutate({ ingredientId, have, idempotencyKey: randomUUID() }),
    notAStaple: (ingredientId: string) =>
      removeStaple.mutate({ ingredientId, idempotencyKey: randomUUID() }),
    /** Move it to another Place; null puts it back where its category usually goes. */
    setPlace: (ingredientId: string, place: Place | null) =>
      setPlace.mutate({ ingredientId, place, idempotencyKey: randomUUID() }),
    /** Add something Sweep doesn't know yet ("kale"), as "some". */
    addNew: (name: string) =>
      addNew.mutate({ name, createKey: randomUUID(), setKey: randomUUID() }),
  };
}
