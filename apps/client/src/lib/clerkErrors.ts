import { isClerkAPIResponseError } from '@clerk/expo';

/** Clerk's error codes, e.g. "form_identifier_not_found". */
export function clerkErrorCodes(error: unknown): string[] {
  if (isClerkAPIResponseError(error)) return error.errors.map((e) => e.code);
  if (error && typeof error === 'object' && 'code' in error && typeof error.code === 'string') {
    return [error.code];
  }
  return [];
}

/** A message that's safe to show the person. */
export function clerkErrorMessage(error: unknown): string {
  if (isClerkAPIResponseError(error)) {
    const first = error.errors[0];
    return first?.longMessage ?? first?.message ?? 'Something went wrong. Please try again.';
  }
  if (error instanceof Error) return error.message;
  return 'Something went wrong. Please try again.';
}
