import { Tile } from '@/components/Tile';
import { ErrorText } from '@/components/ui';
import { useList } from '@/lib/api/lists';
import { tintFor } from '@/theme/tint';

/** The Household's Shopping List as a pastel tile on the home board. */
export function ShoppingListTile() {
  const list = useList();
  const toBuy = list.data?.items.filter((item) => !item.checked).length ?? 0;
  if (list.error) return <ErrorText message={list.error.message} />;
  return (
    <Tile
      href="/lists"
      tint={tintFor(list.data?.id ?? 'list')}
      emoji="🧺"
      title="Shopping List"
      subtitle={toBuy === 0 ? 'Nothing to buy' : `${toBuy} to buy`}
    />
  );
}
