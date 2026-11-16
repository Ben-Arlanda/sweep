/**
 * Hands a draft from the Add Sheet to the review screen.
 *
 * A draft can hold 60 lines and 40 method steps: too big for a route param (that would
 * put it in the web address). So the Sheet stores it here and passes only an id. It lives
 * in memory on purpose: nothing a Member hasn't saved is written anywhere, and a reload
 * loses it (the review screen says so and offers to start again).
 */
import type { ImportDraft } from '@/lib/api/imports';

const drafts = new Map<string, ImportDraft>();
let next = 0;

export function keepDraft(draft: ImportDraft): string {
  const id = `d${++next}`;
  drafts.clear(); // only the newest one is ever reviewed
  drafts.set(id, draft);
  return id;
}

export function findDraft(id: string | undefined): ImportDraft | null {
  return (id && drafts.get(id)) || null;
}

/** After Save, or leaving without saving. */
export function dropDraft(id: string | undefined) {
  if (id) drafts.delete(id);
}
