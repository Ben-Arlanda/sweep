import { Text, View, type DimensionValue } from 'react-native';

import { recipeEmoji } from '@/theme/foodEmoji';
import { tintFor } from '@/theme/tint';
import { useTheme } from '@/theme/useTheme';

/**
 * The picture slot for a recipe on cards, rows and the recipe header (slice 6e). For now
 * an emoji on its pastel; real photos can replace it here later, with this as the
 * fallback for recipes that have none. Decorative: the title next to it says the same.
 */
export function RecipeArt({
  title,
  width = 44,
  height,
  radius,
  emojiSize,
}: {
  title: string;
  width?: DimensionValue;
  height?: number;
  radius?: number;
  emojiSize?: number;
}) {
  const t = useTheme();
  const h = height ?? (typeof width === 'number' ? width : 120);
  const size = emojiSize ?? Math.round(h * 0.5);
  return (
    <View
      aria-hidden
      importantForAccessibility="no-hide-descendants"
      style={{
        width,
        height: h,
        borderRadius: radius ?? Math.round(Math.min(h, 60) * 0.3),
        backgroundColor: t.tints[tintFor(title)].bg, // the same pastel as its FoodThumb rows
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Text style={{ fontSize: size, lineHeight: Math.round(size * 1.3) }}>
        {recipeEmoji(title)}
      </Text>
    </View>
  );
}
