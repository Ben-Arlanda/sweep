import type { components } from '@/lib/api/schema';

export type RecipeImage = components['schemas']['RecipeImageOut'];

/** Which photo to show, or null for the emoji art. */
export function photoUrl(image: RecipeImage | null | undefined, hero: boolean): string | null {
  if (!image) return null;
  return hero ? image.hero_url : image.thumb_url;
}
