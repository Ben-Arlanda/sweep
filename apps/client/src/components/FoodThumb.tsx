import { Text, View } from 'react-native';

import type { TintName } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

/**
 * A food emoji on a pastel square: the thumbnail on list rows, Cabinet rows and recipes
 * (ADR 0007). Decorative, so screen readers skip it; the name next to it says the same.
 *
 * `tint` is the square's pastel. `onWhite` flips it for use inside a pastel card, where
 * a white square stands out better (the design's recipe cards).
 */
export function FoodThumb({
  emoji,
  tint,
  size = 40,
  onWhite = false,
}: {
  emoji: string;
  tint: TintName;
  size?: number;
  onWhite?: boolean;
}) {
  const t = useTheme();
  return (
    <View
      aria-hidden
      importantForAccessibility="no-hide-descendants"
      style={{
        width: size,
        height: size,
        borderRadius: Math.round(size * 0.3),
        backgroundColor: onWhite ? t.colors.surface : t.tints[tint].bg,
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* Emoji draw in their own colours, so no theme colour is needed here. */}
      <Text style={{ fontSize: Math.round(size * 0.52), lineHeight: Math.round(size * 0.7) }}>
        {emoji}
      </Text>
    </View>
  );
}
