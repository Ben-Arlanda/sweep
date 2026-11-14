import { Pressable, View } from 'react-native';

import { Text } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

/**
 * Pick one of a few options, shown as pills ("Any time / 20 min / 30 min", "Dark /
 * Light"). For screen readers it's a radio group: each pill says whether it's selected.
 */
export function ChoiceChips<T>({
  label,
  options,
  value,
  onChange,
}: {
  /** What the group is for, read out before the options ("Ready in", "Appearance"). */
  label: string;
  options: { label: string; value: T; accessibilityLabel?: string }[];
  value: T;
  onChange: (value: T) => void;
}) {
  const t = useTheme();
  return (
    <View
      accessibilityRole="radiogroup"
      accessibilityLabel={label}
      style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}
    >
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <Pressable
            key={option.label}
            accessibilityRole="radio"
            aria-checked={selected}
            accessibilityLabel={option.accessibilityLabel ?? option.label}
            onPress={() => onChange(option.value)}
            style={({ pressed }) => ({
              minHeight: t.touchTarget,
              paddingHorizontal: t.space.md,
              borderRadius: t.radius.pill,
              justifyContent: 'center',
              backgroundColor: selected ? t.colors.inverse : t.colors.surface,
              borderWidth: 1,
              borderColor: selected ? t.colors.inverse : t.colors.border,
              opacity: pressed ? 0.75 : 1,
            })}
          >
            <Text variant="label" style={{ color: selected ? t.colors.onInverse : t.colors.text }}>
              {option.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}
