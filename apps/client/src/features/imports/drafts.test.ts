import type { ImportDraft } from '@/lib/api/imports';

import { dropDraft, findDraft, keepDraft } from './drafts';

const draft = (title: string) => ({ title }) as ImportDraft;

it('hands a draft over by id, and forgets it when dropped', () => {
  const id = keepDraft(draft('Ragu'));
  expect(findDraft(id)?.title).toBe('Ragu');
  dropDraft(id);
  expect(findDraft(id)).toBeNull();
});

it('keeps only the newest draft', () => {
  const first = keepDraft(draft('One'));
  const second = keepDraft(draft('Two'));
  expect(findDraft(first)).toBeNull();
  expect(findDraft(second)?.title).toBe('Two');
});

it('an unknown or missing id finds nothing (e.g. after a reload)', () => {
  expect(findDraft('d999')).toBeNull();
  expect(findDraft(undefined)).toBeNull();
});
