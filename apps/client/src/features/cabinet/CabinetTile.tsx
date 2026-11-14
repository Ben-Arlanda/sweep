import { ErrorText } from '@/components/ui';
import { Tile } from '@/components/Tile';
import { useCabinet } from '@/lib/api/cabinet';

/** Home board tile: what's tracked, and what needs a look. */
export function CabinetTile() {
  const cabinet = useCabinet();
  const tracked = cabinet.data?.tracked ?? [];
  const unknown = tracked.filter((i) => i.status === 'unknown').length;
  const ranOut = (cabinet.data?.staples ?? []).filter((s) => !s.have).length;

  const notes = [
    `${tracked.length} tracked`,
    unknown > 0 ? `${unknown} to check` : null,
    ranOut > 0 ? `${ranOut} run out` : null,
  ].filter(Boolean);

  return (
    <>
      <Tile
        href="/cabinet"
        tint="mint"
        emoji="🥫"
        title="Cabinet"
        subtitle={cabinet.data ? notes.join(' · ') : undefined}
      />
      <ErrorText message={cabinet.error?.message} />
    </>
  );
}
