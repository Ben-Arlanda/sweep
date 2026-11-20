import type { Item } from '@/lib/api/client';

/** "Added by you / Alex / Sweep" for an item's ••• menu. */
export function addedByText(
  item: Pick<Item, 'added_by' | 'added_by_member_id'>,
  meId: string | undefined,
  members: ReadonlyMap<string, { display_name: string }>,
): string {
  if (item.added_by === 'agent') return 'Added by Sweep';
  const id = item.added_by_member_id;
  if (id && id === meId) return 'Added by you';
  const name = id ? members.get(id)?.display_name : undefined;
  return `Added by ${name ?? 'a former member'}`;
}
