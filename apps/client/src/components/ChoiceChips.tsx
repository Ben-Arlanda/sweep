import { Pressable, View } from 'react-native';

import { Text } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

/** How tall a small pill looks. Its tap area stays the full touch target. */
const SMALL_PILL = 36;

/**
 * Pick one of a few options, shown as pills ("Any time / 20 min / 30 min", "Dark /
 * Light"). For screen readers it's a radio group: each pill says whether it's selected.
 *
 * `size="small"` draws a shorter pill inside a full-size tap area (a transparent
 * Pressable around it), so it still meets the 44pt touch target on every platform.
 * `fill` shares the width equally, so the pills stay on one row.
 */
export function ChoiceChips<T>({
  label,
  options,
  value,
  onChange,
  size = 'regular',
  fill = false,
}: {
  /** What the group is for, read out before the options ("Ready in", "Appearance"). */
  label: string;
  options: { label: string; value: T; accessibilityLabel?: string }[];
  value: T;
  onChange: (value: T) => void;
  size?: 'regular' | 'small';
  fill?: boolean;
}) {
  const t = useTheme();
  const small = size === 'small';
  return (
    <View
      accessibilityRole="radiogroup"
      accessibilityLabel={label}
      style={{
        flexDirection: 'row',
        flexWrap: fill ? 'nowrap' : 'wrap',
        gap: fill ? t.space.xs + 2 : t.space.sm,
      }}
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
              justifyContent: 'center',
              opacity: pressed ? 0.75 : 1,
              ...(fill ? { flex: 1, minWidth: 0 } : null),
            })}
          >
            <View
              style={{
                minHeight: small ? SMALL_PILL : t.touchTarget,
                paddingHorizontal: fill ? t.space.xs : small ? t.space.md - 1 : t.space.md,
                borderRadius: t.radius.pill,
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: selected ? t.colors.inverse : t.colors.surface,
                borderWidth: 1,
                borderColor: selected ? t.colors.inverse : t.colors.border,
              }}
            >
              <Text
                variant="label"
                numberOfLines={1}
                style={[
                  small ? { fontSize: 14, lineHeight: 18 } : null,
                  { color: selected ? t.colors.onInverse : t.colors.text },
                ]}
              >
                {option.label}
              </Text>
            </View>
          </Pressable>
        );
      })}
    </View>
  );
}
