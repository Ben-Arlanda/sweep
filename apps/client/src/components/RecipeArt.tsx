import { Image } from 'expo-image';
import { useState } from 'react';
import { Text, View, type DimensionValue } from 'react-native';

import { photoUrl, type RecipeImage } from '@/features/recipes/photo';
import { recipeEmoji } from '@/theme/foodEmoji';
import { tintFor } from '@/theme/tint';
import { useTheme } from '@/theme/useTheme';

/**
 * The picture slot for a recipe on cards, rows and the recipe header: its stock photo
 * (slice 4f, ADR 0029), else an emoji on its pastel. Only the recipe page's large photo
 * is announced; elsewhere the title beside it says the same.
 */
export function RecipeArt({
  title,
  image,
  hero = false,
  width = 44,
  height,
  radius,
  emojiSize,
}: {
  title: string;
  image?: RecipeImage | null;
  hero?: boolean;
  width?: DimensionValue;
  height?: number;
  radius?: number;
  emojiSize?: number;
}) {
  const t = useTheme();
  const [failed, setFailed] = useState<string | null>(null); // the URL that didn't load
  const h = height ?? (typeof width === 'number' ? width : 120);
  const size = emojiSize ?? Math.round(h * 0.5);
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
        backgroundColor: t.tints[tintFor(title)].bg, // the same pastel as its FoodThumb rows
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
        <Text style={{ fontSize: size, lineHeight: Math.round(size * 1.3) }}>
          {recipeEmoji(title)}
        </Text>
      )}
    </View>
  );
}
