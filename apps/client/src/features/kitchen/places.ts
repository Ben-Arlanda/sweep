/**
 * Places in the Kitchen: Fridge, Freezer, Cupboard (ADR 0011). The server says where
 * each item lives; this groups them for the screen. Plain functions, easy to test.
 */
import type { components } from '@/lib/api/schema';

export type Place = components['schemas']['Place'];
export type Tracked = components['schemas']['KitchenItemOut'];
export type Staple = components['schemas']['StapleOut'];
export type KitchenRows = { tracked: readonly Tracked[]; staples: readonly Staple[] };
export type PlaceFilter = 'all' | Place;

/** In the order you'd open them: fridge, freezer, then the cupboard. */
export const PLACES: readonly { place: Place; label: string }[] = [
  { place: 'fridge', label: 'Fridge' },
  { place: 'freezer', label: 'Freezer' },
  { place: 'cupboard', label: 'Cupboard' },
];

export type PlaceSection = { place: Place; label: string; tracked: Tracked[]; staples: Staple[] };

/**
 * "All" skips empty Places (nothing to look at); a chosen Place always shows, so the
 * screen can say "Nothing in the freezer" instead of going blank.
 */
export function byPlace(kitchen: KitchenRows, filter: PlaceFilter): PlaceSection[] {
  return PLACES.filter(({ place }) => filter === 'all' || filter === place)
    .map(({ place, label }) => ({
      place,
      label,
      tracked: kitchen.tracked.filter((t) => t.place === place),
      // Run-out Staples first: they're the ones that need buying.
      staples: kitchen.staples
        .filter((s) => s.place === place)
        .sort((a, b) => Number(a.have) - Number(b.have)),
    }))
    .filter((s) => filter !== 'all' || s.tracked.length + s.staples.length > 0);
}

export function isPlaceFilter(value: unknown): value is PlaceFilter {
  return value === 'all' || PLACES.some((p) => p.place === value);
}
