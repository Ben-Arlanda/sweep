/**
 * Hands what Sweep read from a Kitchen Photo to the review screen, by id: up to 60 rows
 * don't belong in a web address. In memory on purpose (like recipe drafts): nothing the
 * Member hasn't approved is written anywhere, and a reload loses it.
 */
import type { KitchenPhotoRead } from '@/lib/api/kitchenPhotos';

let kept: { id: string; read: KitchenPhotoRead } | null = null;
let next = 0;

export function keepPhotoRead(read: KitchenPhotoRead): string {
  kept = { id: `k${++next}`, read };
  return kept.id;
}

export function findPhotoRead(id: string | undefined): KitchenPhotoRead | null {
  return kept && kept.id === id ? kept.read : null;
}

export function dropPhotoRead() {
  kept = null;
}
