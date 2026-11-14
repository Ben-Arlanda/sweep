/**
 * Typed API client.
 *
 * `paths` is generated from FastAPI's OpenAPI schema (`npm run api:types`), so
 * TypeScript knows every endpoint's URL, body and response. If the backend changes
 * a field and we regenerate, mistakes show up as type errors here instead of as
 * bugs on a user's phone.
 */
import { useAuth } from '@clerk/expo';
import createClient, { type Middleware } from 'openapi-fetch';
import { useMemo } from 'react';

import { API_URL } from '@/lib/config';

import type { components, paths } from './schema';

export type MeOut = components['schemas']['MeOut'];
export type HouseholdDetail = components['schemas']['HouseholdDetailOut'];
export type MemberOut = components['schemas']['MemberOut'];
export type InviteOut = components['schemas']['InviteOut'];

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
 * The API client for the signed-in user.
 *
 * The middleware runs before every request and asks Clerk for a fresh session token.
 * Clerk tokens are short-lived (about a minute); getToken() returns a cached one or
 * quietly refreshes it, so we never store tokens ourselves.
 */
export function useApi() {
  const { getToken } = useAuth();

  return useMemo(() => {
    const client = createClient<paths>({ baseUrl: API_URL });
    const auth: Middleware = {
      async onRequest({ request }) {
        const token = await getToken();
        if (token) request.headers.set('Authorization', `Bearer ${token}`);
        return request;
      },
    };
    client.use(auth);
    return client;
  }, [getToken]);
}
