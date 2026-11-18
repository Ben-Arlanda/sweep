/**
 * Places in the Kitchen: Fridge, Freezer, Cupboard (ADR 0011). The server says where
 * each item lives.
 */
import type { components } from '@/lib/api/schema';

export type Place = components['schemas']['Place'];
export type PlaceFilter = 'all' | Place;

/** In the order you'd open them: fridge, freezer, then the cupboard. */
export const PLACES: readonly { place: Place; label: string }[] = [
  { place: 'fridge', label: 'Fridge' },
  { place: 'freezer', label: 'Freezer' },
  { place: 'cupboard', label: 'Cupboard' },
];

export function isPlaceFilter(value: unknown): value is PlaceFilter {
  return value === 'all' || PLACES.some((p) => p.place === value);
}
