/**
 * Shopping Lists: server state, optimistic updates and the retry queue.
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
 * Mutations on one list share a `scope`, so they go one at a time, in order: an item's
 * tick can never overtake the add that created it.
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

import { api, ApiError, unwrap, type ListDetail, type MeOut } from './client';
import { queryKeys as householdKeys } from './households';

export const listKeys = {
  all: ['lists'] as const,
  summaries: ['lists', 'summaries'] as const,
  detail: (id: string) => ['lists', 'detail', id] as const,
};

const mutationKeys = {
  addItem: ['lists', 'addItem'] as const,
  setChecked: ['lists', 'setChecked'] as const,
  deleteItem: ['lists', 'deleteItem'] as const,
  createList: ['lists', 'createList'] as const,
  renameList: ['lists', 'renameList'] as const,
  deleteList: ['lists', 'deleteList'] as const,
};

type Keyed = { idempotencyKey: string };
type AddItemVars = Keyed & { listId: string; itemId: string; text: string };
type SetCheckedVars = Keyed & {
  listId: string;
  itemId: string;
  checked: boolean;
};
type DeleteItemVars = Keyed & { listId: string; itemId: string };
type CreateListVars = Keyed & { name: string };
type RenameListVars = Keyed & { listId: string; name: string };
type DeleteListVars = Keyed & { listId: string };

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

  /** Shared optimistic plumbing for changes to one list's items. */
  function optimistic<V extends { listId: string }>(
    apply: (list: ListDetail, vars: V) => ListDetail,
  ) {
    return {
      retry: shouldRetry,
      onMutate: async (vars: V): Promise<Snapshot> => {
        const key = listKeys.detail(vars.listId);
        // Stop any refetch in flight, or its (older) answer could overwrite our change.
        await queryClient.cancelQueries({ queryKey: key });
        const previous = queryClient.getQueryData<ListDetail>(key);
        if (previous) queryClient.setQueryData(key, apply(previous, vars));
        return { previous };
      },
      onError: (_error: unknown, vars: V, snapshot: Snapshot | undefined) => {
        if (snapshot?.previous) {
          queryClient.setQueryData(listKeys.detail(vars.listId), snapshot.previous);
        }
      },
      onSettled: () => settle(queryClient),
    };
  }

  queryClient.setMutationDefaults(mutationKeys.addItem, {
    mutationFn: async (v: AddItemVars) =>
      unwrap(
        await api.POST('/lists/{list_id}/items', {
          params: { path: { list_id: v.listId }, header: header(v) },
          body: { id: v.itemId, text: v.text },
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

  // List-level changes are rarer and not optimistic: wait for the server, then refetch.
  queryClient.setMutationDefaults(mutationKeys.createList, {
    mutationFn: async (v: CreateListVars) =>
      unwrap(
        await api.POST('/lists', {
          params: { header: header(v) },
          body: { name: v.name },
        }),
      ),
    retry: shouldRetry,
    onSettled: () => settle(queryClient),
  });

  queryClient.setMutationDefaults(mutationKeys.renameList, {
    mutationFn: async (v: RenameListVars) =>
      unwrap(
        await api.PATCH('/lists/{list_id}', {
          params: { path: { list_id: v.listId }, header: header(v) },
          body: { name: v.name },
        }),
      ),
    retry: shouldRetry,
    onSettled: () => settle(queryClient),
  });

  queryClient.setMutationDefaults(mutationKeys.deleteList, {
    mutationFn: async (v: DeleteListVars) =>
      unwrap(
        await api.DELETE('/lists/{list_id}', {
          params: { path: { list_id: v.listId }, header: header(v) },
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
    // Ticking a linked item changes the Cabinet too.
    void queryClient.invalidateQueries({ queryKey: ['cabinet'] });
  }
}

// --- Hooks for screens ---------------------------------------------------------------

export function useLists(enabled = true) {
  return useQuery({
    queryKey: listKeys.summaries,
    queryFn: async () => unwrap(await api.GET('/lists')),
    enabled,
  });
}

export function useList(listId: string) {
  return useQuery({
    queryKey: listKeys.detail(listId),
    queryFn: async () =>
      unwrap(
        await api.GET('/lists/{list_id}', {
          params: { path: { list_id: listId } },
        }),
      ),
  });
}

/**
 * The idempotency key (and a new item's id) are made here, when the Member taps, and
 * stored with the queued mutation. Every retry, even after an app restart, reuses them.
 */
export function useListActions(listId: string) {
  const scope = { id: `list:${listId}` };
  const add = useMutation<unknown, Error, AddItemVars>({
    mutationKey: mutationKeys.addItem,
    scope,
  });
  const check = useMutation<unknown, Error, SetCheckedVars>({
    mutationKey: mutationKeys.setChecked,
    scope,
  });
  const remove = useMutation<unknown, Error, DeleteItemVars>({
    mutationKey: mutationKeys.deleteItem,
    scope,
  });
  const rename = useMutation<unknown, Error, RenameListVars>({
    mutationKey: mutationKeys.renameList,
    scope,
  });
  const removeList = useMutation<unknown, Error, DeleteListVars>({
    mutationKey: mutationKeys.deleteList,
    scope,
  });

  return {
    error: add.error ?? check.error ?? remove.error ?? rename.error ?? removeList.error,
    addItem: (text: string) =>
      add.mutate({
        listId,
        itemId: randomUUID(),
        text,
        idempotencyKey: randomUUID(),
      }),
    setChecked: (itemId: string, checked: boolean) =>
      check.mutate({ listId, itemId, checked, idempotencyKey: randomUUID() }),
    deleteItem: (itemId: string) => remove.mutate({ listId, itemId, idempotencyKey: randomUUID() }),
    rename: (name: string) => rename.mutate({ listId, name, idempotencyKey: randomUUID() }),
    deleteList: () => removeList.mutateAsync({ listId, idempotencyKey: randomUUID() }),
  };
}

export function useCreateList() {
  const create = useMutation<unknown, Error, CreateListVars>({
    mutationKey: mutationKeys.createList,
  });
  return {
    ...create,
    create: (name: string) => create.mutate({ name, idempotencyKey: randomUUID() }),
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
