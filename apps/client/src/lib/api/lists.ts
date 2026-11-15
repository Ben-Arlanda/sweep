/**
 * The Household's Shopping List and its Shops: server state, optimistic updates and the
 * retry queue. There is one list per Household (ADR 0009), fetched with `GET /list`.
 *
 * How a tap becomes a saved change:
 *
 *   tap ─► mutate({ ...change, idempotencyKey })        key made ONCE, here
 *        ─► onMutate: update the cache now (optimistic)  the screen changes instantly
 *        ─► mutationFn: send it                          offline? TanStack pauses it,
 *                                                        persists it, and sends it later
 *        ─► onError: put the old list back
 *        ─► onSettled: refetch from the server            the real answer replaces the guess
 *
 * List mutations share a `scope`, so they go one at a time, in order: an item's tick
 * can never overtake the add that created it.
 *
 * The functions live in `setMutationDefaults`, keyed by name, not inside each
 * useMutation call. A mutation restored from storage after a restart is only data
 * (key + variables); TanStack finds its code again by key.
 */
import {
  onlineManager,
  useMutation,
  useMutationState,
  useQuery,
  type QueryClient,
} from '@tanstack/react-query';
import { randomUUID } from 'expo-crypto';
import { useSyncExternalStore } from 'react';

import {
  newItem,
  withItemAdded,
  withItemChecked,
  withItemRemoved,
} from '@/features/lists/listCache';
import { withItemShop } from '@/features/lists/shops';

import { api, ApiError, unwrap, type ListDetail, type MeOut } from './client';
import { queryKeys as householdKeys } from './households';

export const listKeys = {
  all: ['lists'] as const,
  current: ['lists', 'current'] as const,
};

const mutationKeys = {
  addItem: ['lists', 'addItem'] as const,
  setChecked: ['lists', 'setChecked'] as const,
  setShop: ['lists', 'setShop'] as const,
  deleteItem: ['lists', 'deleteItem'] as const,
  addShop: ['lists', 'addShop'] as const,
  renameShop: ['lists', 'renameShop'] as const,
  deleteShop: ['lists', 'deleteShop'] as const,
};

/** One scope for every list change, so they reach the server in the order tapped. */
const SCOPE = { id: 'list' };

type Keyed = { idempotencyKey: string };
type AddItemVars = Keyed & {
  listId: string;
  itemId: string;
  text: string;
  // The app no longer sends one, but an add queued offline by an older version might.
  shopId?: string | null;
};
type SetCheckedVars = Keyed & {
  listId: string;
  itemId: string;
  checked: boolean;
};
type SetShopVars = Keyed & {
  listId: string;
  itemId: string;
  shopId: string | null;
};
type DeleteItemVars = Keyed & { listId: string; itemId: string };
type AddShopVars = Keyed & { name: string };
type RenameShopVars = Keyed & { shopId: string; name: string };
type DeleteShopVars = Keyed & { shopId: string };

type Snapshot = { previous: ListDetail | undefined };

/** Typed by the OpenAPI schema: TypeScript won't let a list mutation forget it. */
const header = (v: Keyed) => ({ 'Idempotency-Key': v.idempotencyKey });

/**
 * Retry network failures and server errors (5xx); never retry a 4xx, because the same
 * request would be refused again. While the device is offline, TanStack pauses
 * mutations instead of failing them, so those don't use up retries.
 */
function shouldRetry(failureCount: number, error: unknown) {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < 5;
}

export function registerListMutations(queryClient: QueryClient) {
  const myMemberId = () =>
    queryClient.getQueryData<MeOut | null>(householdKeys.me)?.member.id ?? null;

  /** Shared optimistic plumbing for changes to the list's items. */
  function optimistic<V>(apply: (list: ListDetail, vars: V) => ListDetail) {
    const key = listKeys.current;
    return {
      retry: shouldRetry,
      onMutate: async (vars: V): Promise<Snapshot> => {
        // Stop any refetch in flight, or its (older) answer could overwrite our change.
        await queryClient.cancelQueries({ queryKey: key });
        const previous = queryClient.getQueryData<ListDetail>(key);
        if (previous) queryClient.setQueryData(key, apply(previous, vars));
        return { previous };
      },
      onError: (_error: unknown, _vars: V, snapshot: Snapshot | undefined) => {
        if (snapshot?.previous) queryClient.setQueryData(key, snapshot.previous);
      },
      onSettled: () => settle(queryClient),
    };
  }

  queryClient.setMutationDefaults(mutationKeys.addItem, {
    mutationFn: async (v: AddItemVars) =>
      unwrap(
        await api.POST('/lists/{list_id}/items', {
          params: { path: { list_id: v.listId }, header: header(v) },
          body: { id: v.itemId, text: v.text, shop_id: v.shopId ?? null },
        }),
      ),
    ...optimistic<AddItemVars>((list, v) =>
      withItemAdded(
        list,
        newItem({
          id: v.itemId,
          text: v.text,
          memberId: myMemberId(),
          now: new Date().toISOString(),
          shopId: v.shopId,
        }),
      ),
    ),
  });

  queryClient.setMutationDefaults(mutationKeys.setChecked, {
    mutationFn: async (v: SetCheckedVars) =>
      unwrap(
        await api.PUT('/lists/{list_id}/items/{item_id}/checked', {
          params: {
            path: { list_id: v.listId, item_id: v.itemId },
            header: header(v),
          },
          body: { checked: v.checked },
        }),
      ),
    ...optimistic<SetCheckedVars>((list, v) =>
      withItemChecked(list, v.itemId, v.checked, myMemberId(), new Date().toISOString()),
    ),
  });

  queryClient.setMutationDefaults(mutationKeys.setShop, {
    mutationFn: async (v: SetShopVars) =>
      unwrap(
        await api.PATCH('/lists/{list_id}/items/{item_id}', {
          params: {
            path: { list_id: v.listId, item_id: v.itemId },
            header: header(v),
          },
          body: { shop_id: v.shopId },
        }),
      ),
    ...optimistic<SetShopVars>((list, v) => withItemShop(list, v.itemId, v.shopId)),
  });

  queryClient.setMutationDefaults(mutationKeys.deleteItem, {
    mutationFn: async (v: DeleteItemVars) =>
      unwrap(
        await api.DELETE('/lists/{list_id}/items/{item_id}', {
          params: {
            path: { list_id: v.listId, item_id: v.itemId },
            header: header(v),
          },
        }),
      ),
    ...optimistic<DeleteItemVars>((list, v) => withItemRemoved(list, v.itemId)),
  });

  // Shop changes are rarer and not optimistic: wait for the server, then refetch.
  queryClient.setMutationDefaults(mutationKeys.addShop, {
    mutationFn: async (v: AddShopVars) =>
      unwrap(
        await api.POST('/shops', {
          params: { header: header(v) },
          body: { name: v.name },
        }),
      ),
    retry: shouldRetry,
    onSettled: () => settle(queryClient),
  });

  queryClient.setMutationDefaults(mutationKeys.renameShop, {
    mutationFn: async (v: RenameShopVars) =>
      unwrap(
        await api.PATCH('/shops/{shop_id}', {
          params: { path: { shop_id: v.shopId }, header: header(v) },
          body: { name: v.name },
        }),
      ),
    retry: shouldRetry,
    onSettled: () => settle(queryClient),
  });

  queryClient.setMutationDefaults(mutationKeys.deleteShop, {
    mutationFn: async (v: DeleteShopVars) =>
      unwrap(
        await api.DELETE('/shops/{shop_id}', {
          params: { path: { shop_id: v.shopId }, header: header(v) },
        }),
      ),
    retry: shouldRetry,
    onSettled: () => settle(queryClient),
  });
}

/**
 * Refetch lists, but only once every queued list change has finished. Refetching
 * between two of our own changes would briefly show the list without the second one.
 */
export function settle(queryClient: QueryClient) {
  // This mutation still counts as running while onSettled runs, hence "<= 1".
  if (queryClient.isMutating({ mutationKey: listKeys.all }) <= 1) {
    void queryClient.invalidateQueries({ queryKey: listKeys.all });
    // Ticking a linked item changes the Kitchen too.
    void queryClient.invalidateQueries({ queryKey: ['kitchen'] });
  }
}

// --- Hooks for screens ---------------------------------------------------------------

/** The Household's one Shopping List, with its items and Shops. */
export function useList(enabled = true) {
  return useQuery({
    queryKey: listKeys.current,
    queryFn: async () => unwrap(await api.GET('/list')),
    enabled,
  });
}

/**
 * The idempotency key (and a new item's id) are made here, when the Member taps, and
 * stored with the queued mutation. Every retry, even after an app restart, reuses them.
 */
export function useListActions(listId: string) {
  const add = useMutation<unknown, Error, AddItemVars>({
    mutationKey: mutationKeys.addItem,
    scope: SCOPE,
  });
  const check = useMutation<unknown, Error, SetCheckedVars>({
    mutationKey: mutationKeys.setChecked,
    scope: SCOPE,
  });
  const tag = useMutation<unknown, Error, SetShopVars>({
    mutationKey: mutationKeys.setShop,
    scope: SCOPE,
  });
  const remove = useMutation<unknown, Error, DeleteItemVars>({
    mutationKey: mutationKeys.deleteItem,
    scope: SCOPE,
  });

  return {
    error: add.error ?? check.error ?? tag.error ?? remove.error,
    addItem: (text: string) =>
      add.mutate({
        listId,
        itemId: randomUUID(),
        text,
        idempotencyKey: randomUUID(),
      }),
    setChecked: (itemId: string, checked: boolean) =>
      check.mutate({ listId, itemId, checked, idempotencyKey: randomUUID() }),
    setShop: (itemId: string, shopId: string | null) =>
      tag.mutate({ listId, itemId, shopId, idempotencyKey: randomUUID() }),
    deleteItem: (itemId: string) => remove.mutate({ listId, itemId, idempotencyKey: randomUUID() }),
  };
}

export function useShopActions() {
  const add = useMutation<unknown, Error, AddShopVars>({
    mutationKey: mutationKeys.addShop,
    scope: SCOPE,
  });
  const rename = useMutation<unknown, Error, RenameShopVars>({
    mutationKey: mutationKeys.renameShop,
    scope: SCOPE,
  });
  const remove = useMutation<unknown, Error, DeleteShopVars>({
    mutationKey: mutationKeys.deleteShop,
    scope: SCOPE,
  });
  return {
    error: add.error ?? rename.error ?? remove.error,
    addShop: (name: string) => add.mutate({ name, idempotencyKey: randomUUID() }),
    renameShop: (shopId: string, name: string) =>
      rename.mutate({ shopId, name, idempotencyKey: randomUUID() }),
    deleteShop: (shopId: string) => remove.mutate({ shopId, idempotencyKey: randomUUID() }),
  };
}

/** How many list changes are waiting to reach the server (queued or in flight). */
export function usePendingListChanges() {
  return useMutationState({
    filters: { mutationKey: listKeys.all, status: 'pending' },
    select: (m) => m.state.submittedAt,
  }).length;
}

export function useIsOnline() {
  return useSyncExternalStore(
    (onChange) => onlineManager.subscribe(onChange),
    () => onlineManager.isOnline(),
  );
}
