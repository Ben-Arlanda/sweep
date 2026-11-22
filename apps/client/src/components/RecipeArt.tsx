import { Image } from 'expo-image';
import { Utensils } from 'lucide-react-native';
import { useState } from 'react';
import { View, type DimensionValue } from 'react-native';

import { Icon } from '@/components/Icon';

import { photoUrl, type RecipeImage } from '@/features/recipes/photo';
import { useRecipe } from '@/lib/api/recipes';
import { tintFor } from '@/theme/tint';
import { useTheme } from '@/theme/useTheme';

/**
 * The picture slot for a recipe on cards, rows and the recipe header: its stock photo
 * (slice 4f, ADR 0029), else one plain food icon on its pastel: a Member's own recipes,
 * Adaptations, and a photo that fails to load. Only the recipe page's large photo
 * is announced; elsewhere the title beside it says the same.
 */
export function RecipeArt({
  title,
  image,
  hero = false,
  width = 44,
  height,
  radius,
  iconSize,
}: {
  title: string;
  image?: RecipeImage | null;
  hero?: boolean;
  width?: DimensionValue;
  height?: number;
  radius?: number;
  iconSize?: number;
}) {
  const t = useTheme();
  const [failed, setFailed] = useState<string | null>(null); // the URL that didn't load
  const h = height ?? (typeof width === 'number' ? width : 120);
  const size = iconSize ?? Math.round(h * 0.42);
  const tint = t.tints[tintFor(title)];
  const wanted = photoUrl(image, hero);
  const uri = wanted === failed ? null : wanted;
  return (
    <View
      aria-hidden={!(uri && hero)}
      importantForAccessibility={uri && hero ? 'auto' : 'no-hide-descendants'}
      style={{
        width,
        height: h,
        borderRadius: radius ?? Math.round(Math.min(h, 60) * 0.3),
        overflow: 'hidden',
        backgroundColor: tint.bg, // the same pastel as its FoodThumb rows
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {uri ? (
        <Image
          source={{ uri }}
          accessibilityLabel={hero ? `Photo of ${title}` : undefined}
          accessible={hero}
          contentFit="cover"
          transition={150}
          recyclingKey={uri}
          onError={() => setFailed(uri)}
          style={{ width: '100%', height: '100%' }}
        />
      ) : (
        <Icon icon={Utensils} size={size} color={tint.onPill} />
      )}
    </View>
  );
}

/**
 * RecipeArt for a screen that has only the recipe's id (a Proposal's meals): the photo
 * comes from the recipe, which the recipe page would fetch anyway. An Adaptation's dish
 * has changed, so it keeps the icon.
 */
export function RecipeArtFor({
  recipeId,
  adapted = false,
  ...art
}: Omit<Parameters<typeof RecipeArt>[0], 'image'> & { recipeId: string; adapted?: boolean }) {
  const recipe = useRecipe(recipeId, !adapted);
  return <RecipeArt {...art} image={adapted ? null : recipe.data?.image} />;
}
