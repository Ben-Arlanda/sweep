/**
 * Server state for the Household, through TanStack Query.
 *
 * Mental model: TanStack Query is a cache of server data, keyed by name ("me",
 * "household"). Screens read from the cache; mutations change the server and then
 * mark cache entries as stale ("invalidate") so they refetch. Components never copy
 * server data into useState.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ApiError, unwrap, useApi, type MeOut } from './client';

export const queryKeys = {
  me: ['me'] as const,
  household: ['household'] as const,
};

/**
 * Who am I, and which Household am I in?
 * Returns `null` (not an error) when signed in but not in a Household yet: that's a
 * normal state the app shows onboarding for, not a failure.
 */
export function useMe() {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.me,
    queryFn: async (): Promise<MeOut | null> => {
      try {
        return unwrap(await api.GET('/me'));
      } catch (error) {
        if (error instanceof ApiError && error.code === 'not_in_household') return null;
        throw error;
      }
    },
  });
}

export function useHousehold(enabled: boolean) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.household,
    queryFn: async () => unwrap(await api.GET('/households/current')),
    enabled,
  });
}

/** After any membership change, both cached answers may be out of date. */
function useInvalidateAll() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries();
}

export function useCreateHousehold() {
  const api = useApi();
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: async (body: { name: string; display_name: string }) =>
      unwrap(await api.POST('/households', { body })),
    onSuccess: invalidate,
  });
}

export function useAcceptInvite() {
  const api = useApi();
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: async ({ code, displayName }: { code: string; displayName: string }) =>
      unwrap(
        await api.POST('/invites/{code}/accept', {
          params: { path: { code: code.trim() } },
          body: { display_name: displayName },
        }),
      ),
    onSuccess: invalidate,
  });
}

export function useCreateInvite() {
  const api = useApi();
  return useMutation({
    mutationFn: async () => unwrap(await api.POST('/households/current/invites')),
  });
}

export function useRemoveMember() {
  const api = useApi();
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: async (memberId: string) =>
      unwrap(
        await api.DELETE('/households/current/members/{member_id}', {
          params: { path: { member_id: memberId } },
        }),
      ),
    onSuccess: invalidate,
  });
}

export function useDeleteMyData() {
  const api = useApi();
  return useMutation({
    mutationFn: async () => unwrap(await api.DELETE('/me')),
  });
}
