import type { components } from '@/lib/api/schema';
import { API_URL } from '@/lib/config';

export type RecipeImage = components['schemas']['RecipeImageOut'];

/**
 * Which photo to show, or null for the food icon. A stock photo's link is absolute; a
 * Member's own photo (ADR 0031) is served by our API, so its link starts with "/".
 */
export function photoUrl(
  image: Pick<RecipeImage, 'thumb_url' | 'hero_url'> | null | undefined,
  hero: boolean,
  apiUrl: string = API_URL,
): string | null {
  if (!image) return null;
  const url = hero ? image.hero_url : image.thumb_url;
  return url.startsWith('/') ? `${apiUrl}${url}` : url;
}
