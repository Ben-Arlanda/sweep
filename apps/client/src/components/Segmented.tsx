import { View } from 'react-native';

import { PressableScale } from '@/components/PressableScale';
import { Text } from '@/components/ui';
import { haptic } from '@/lib/haptics';
import { useTheme } from '@/theme/useTheme';

/**
 * Two or three tabs on a grey track; the selected one is a raised white button
 * (Staples | Non-staples, This week | Next week, Ingredients | Method). Selected also
 * gets the heavier label, so it isn't shown by colour alone (WCAG 1.4.1).
 */
export function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  /** Names the tab list for screen readers ("Kind", "Week"). */
  label: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}) {
  const t = useTheme();
  return (
    <View
      accessibilityRole="tablist"
      accessibilityLabel={label}
      style={{
        flexDirection: 'row',
        gap: 3,
        padding: 3,
        borderRadius: t.radius.md,
        borderWidth: 1,
        borderColor: t.colors.border,
        backgroundColor: t.colors.fill,
      }}
    >
      {options.map((o) => {
        const on = o.value === value;
        return (
          <PressableScale
            key={o.value}
            accessibilityRole="tab"
            accessibilityState={{ selected: on }}
            onPress={() => {
              if (on) return;
              haptic.select();
              onChange(o.value);
            }}
            style={{
              flex: 1,
              minHeight: t.touchTarget - 6, // with the track's padding the tap area is 44
              borderRadius: t.radius.md - 3,
              alignItems: 'center',
              justifyContent: 'center',
              paddingHorizontal: t.space.sm,
              backgroundColor: on ? t.colors.surface : 'transparent',
              boxShadow: on ? '0 1px 3px rgba(18, 26, 46, 0.15)' : undefined,
            }}
          >
            <Text
              numberOfLines={1}
              style={{
                fontSize: 14,
                lineHeight: 18,
                fontFamily: on ? t.fonts.bold : t.fonts.medium,
                color: on ? t.colors.text : t.colors.textMuted,
              }}
            >
              {o.label}
            </Text>
          </PressableScale>
        );
      })}
    </View>
  );
}
