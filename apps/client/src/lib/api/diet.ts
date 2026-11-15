/**
 * The Household's Dietary Rules (hard: never broken) and Preferences (soft: lean
 * towards). Any Member can change them. The agent reads them fresh on every turn, so a
 * change applies to the very next message.
 *
 * Saves aren't queued offline like Kitchen changes: they're a deliberate "Save" that
 * should succeed or say why. Each still carries an Idempotency-Key, so a retry after a
 * timeout can't be applied twice.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { randomUUID } from 'expo-crypto';

import { api, ApiError, unwrap } from './client';
import type { components } from './schema';

export type Diet = components['schemas']['Diet'];
export type DietaryRules = components['schemas']['DietaryRulesOut'];
export type Preferences = components['schemas']['PreferencesOut'];
export type PreferencesIn = components['schemas']['PreferencesIn'];

export const dietKeys = {
  rules: ['diet', 'rules'] as const,
  preferences: ['diet', 'preferences'] as const,
  cuisines: ['recipes', 'cuisines'] as const,
};

export function useDietaryRules() {
  return useQuery({
    queryKey: dietKeys.rules,
    queryFn: async () => unwrap(await api.GET('/households/current/dietary-rules')),
  });
}

export function usePreferences() {
  return useQuery({
    queryKey: dietKeys.preferences,
    queryFn: async () => unwrap(await api.GET('/households/current/preferences')),
  });
}

/** The cuisines the recipe library covers, most common first. */
export function useCuisines() {
  return useQuery({
    queryKey: dietKeys.cuisines,
    queryFn: async () => unwrap(await api.GET('/recipes/cuisines')),
    staleTime: 60 * 60_000,
  });
}

/** Retry only what might work next time: network trouble and server errors. */
function retryable(failureCount: number, error: Error) {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < 2;
}

/** Saves both halves. One key per Save tap, reused by its retries. */
export function useSaveDiet() {
  const queryClient = useQueryClient();
  return useMutation({
    retry: retryable,
    mutationFn: async (v: {
      key: string;
      rules: { diets: Diet[]; excluded_ingredient_ids: string[] };
      preferences: PreferencesIn;
    }) => {
      const [rules, preferences] = await Promise.all([
        api
          .PUT('/households/current/dietary-rules', {
            params: { header: { 'Idempotency-Key': `${v.key}-rules` } },
            body: v.rules,
          })
          .then(unwrap),
        api
          .PUT('/households/current/preferences', {
            params: { header: { 'Idempotency-Key': `${v.key}-preferences` } },
            body: v.preferences,
          })
          .then(unwrap),
      ]);
      return { rules, preferences };
    },
    onSuccess: ({ rules, preferences }) => {
      queryClient.setQueryData(dietKeys.rules, rules);
      queryClient.setQueryData(dietKeys.preferences, preferences);
    },
  });
}

export const newSaveKey = () => randomUUID();

/**
 * The days the "Plan my week" sheet starts with, saved when a plan starts from it. Its
 * own route: sending the whole Preferences could overwrite another Member's change.
 * Fire and forget: if it fails, the plan still starts; next time just starts from the
 * old days.
 */
export function useSavePlanWeekdays() {
  const queryClient = useQueryClient();
  return useMutation({
    retry: retryable,
    mutationFn: async (v: { key: string; weekdays: number[] }) =>
      unwrap(
        await api.PUT('/households/current/plan-weekdays', {
          params: { header: { 'Idempotency-Key': v.key } },
          body: { weekdays: v.weekdays },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: dietKeys.preferences }),
  });
}
