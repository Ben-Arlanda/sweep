import type { components } from '@/lib/api/schema';

import { onListIds } from './onList';

type ListItem = components['schemas']['ItemOut'];

const item = (id: string | null, checked: boolean) =>
  ({ ingredient: id ? { id } : null, checked }) as unknown as ListItem;

describe('onListIds', () => {
  it('is the Ingredients waiting on the list: unticked, linked', () => {
    const ids = onListIds([item('milk', false), item('eggs', true), item(null, false)]);
    expect([...ids]).toEqual(['milk']);
  });
  it('is empty with no list yet', () => {
    expect(onListIds(undefined).size).toBe(0);
  });
});
