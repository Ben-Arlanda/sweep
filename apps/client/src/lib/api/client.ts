/**
 * Typed API client.
 *
 * `paths` is generated from FastAPI's OpenAPI schema (`npm run api:types`), so
 * TypeScript knows every endpoint's URL, body and response. If the backend changes
 * a field and we regenerate, mistakes show up as type errors here instead of as
 * bugs on a user's phone.
 */
import createClient from 'openapi-fetch';

import { API_URL } from '@/lib/config';

import type { components, paths } from './schema';

export type MeOut = components['schemas']['MeOut'];
export type HouseholdDetail = components['schemas']['HouseholdDetailOut'];
export type MemberOut = components['schemas']['MemberOut'];
export type InviteOut = components['schemas']['InviteOut'];
export type ListSummary = components['schemas']['ShoppingListSummaryOut'];
export type ListDetail = components['schemas']['ShoppingListDetailOut'];
export type Item = components['schemas']['ItemOut'];

/** Every error from our API has this shape (see services/api/app/main.py). */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

/** Turns a non-2xx response into a thrown ApiError, so TanStack Query sees a failure. */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error !== undefined || !result.response.ok) {
    const body = (result.error ?? {}) as { code?: string; detail?: unknown };
    const message =
      typeof body.detail === 'string' ? body.detail : 'Something went wrong. Please try again.';
    throw new ApiError(result.response.status, body.code ?? 'http_error', message);
  }
  return result.data as T;
}

/**
 * Where the client gets the signed-in user's token. `TokenBridge` (root layout) points
 * this at Clerk's getToken. It lives outside React because queued mutations can run
 * after an app restart, before (or without) any particular screen being on display.
 */
let tokenGetter: () => Promise<string | null> = async () => null;

export function setTokenGetter(getter: () => Promise<string | null>) {
  tokenGetter = getter;
}

export function getToken() {
  return tokenGetter();
}

/**
 * The one API client. Before every request it asks Clerk for a session token. Clerk
 * tokens are short-lived (about a minute); getToken() returns a cached one or quietly
 * refreshes it, so we never store tokens ourselves.
 */
export const api = createClient<paths>({ baseUrl: API_URL });
api.use({
  async onRequest({ request }) {
    const token = await tokenGetter();
    if (token) request.headers.set('Authorization', `Bearer ${token}`);
    return request;
  },
});

/** Kept as a hook so screens don't care where the client comes from. */
export function useApi() {
  return api;
}
