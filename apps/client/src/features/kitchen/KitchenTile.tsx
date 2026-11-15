import { ErrorText } from '@/components/ui';
import { Tile } from '@/components/Tile';
import { useKitchen } from '@/lib/api/kitchen';

/** Home board tile: what's tracked, and what needs a look. */
export function KitchenTile() {
  const kitchen = useKitchen();
  const tracked = kitchen.data?.tracked ?? [];
  const unknown = tracked.filter((i) => i.status === 'unknown').length;
  const ranOut = (kitchen.data?.staples ?? []).filter((s) => !s.have).length;

  const notes = [
    `${tracked.length} tracked`,
    unknown > 0 ? `${unknown} to check` : null,
    ranOut > 0 ? `${ranOut} run out` : null,
  ].filter(Boolean);

  return (
    <>
      <Tile
        href="/kitchen"
        tint="mint"
        emoji="🥫"
        title="Kitchen"
        subtitle={kitchen.data ? notes.join(' · ') : undefined}
      />
      <ErrorText message={kitchen.error?.message} />
    </>
  );
}
