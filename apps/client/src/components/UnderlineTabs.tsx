import { useState } from 'react';
import { Pressable, View, type LayoutRectangle } from 'react-native';
import Animated, { ReduceMotion, useAnimatedStyle, withTiming } from 'react-native-reanimated';

import { Text } from '@/components/ui';
import { haptic } from '@/lib/haptics';
import { useTheme } from '@/theme/useTheme';

/**
 * Text tabs spread edge to edge (first left, last right, even gaps) over a hairline track;
 * a bar under the chosen one slides to the next. For a
 * page's sections (a recipe's Overview, Ingredients, Method). Screen readers hear a tab
 * list, like Segmented.
 */
export function UnderlineTabs<T extends string>({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: T;
  onChange: (value: T) => void;
  options: { value: T; label: string }[];
}) {
  const t = useTheme();
  const [boxes, setBoxes] = useState<Partial<Record<T, LayoutRectangle>>>({});
  const box = boxes[value];
  const bar = useAnimatedStyle(() => {
    const timing = { duration: t.motion.duration.base, reduceMotion: ReduceMotion.System };
    return {
      opacity: box ? 1 : 0,
      width: withTiming(box?.width ?? 0, timing),
      transform: [{ translateX: withTiming(box?.x ?? 0, timing) }],
    };
  });

  return (
    <View accessibilityRole="tablist" accessibilityLabel={label}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
        {options.map((o) => {
          const on = o.value === value;
          return (
            <Pressable
              key={o.value}
              accessibilityRole="tab"
              accessibilityState={{ selected: on }}
              aria-selected={on}
              onPress={() => {
                if (on) return;
                haptic.select();
                onChange(o.value);
              }}
              onLayout={(e) => {
                const next = e.nativeEvent.layout;
                setBoxes((now) => ({ ...now, [o.value]: next }));
              }}
              style={{ minHeight: t.touchTarget, justifyContent: 'center' }}
            >
              <Text
                style={{
                  fontSize: 17,
                  lineHeight: 22,
                  fontFamily: on ? t.fonts.bold : t.fonts.medium,
                  color: on ? t.colors.text : t.colors.onBackgroundMuted,
                }}
              >
                {o.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
      <View style={{ height: 3, borderRadius: 2, backgroundColor: t.colors.border }}>
        <Animated.View
          style={[
            { position: 'absolute', left: 0, top: 0, height: 3, borderRadius: 2 },
            { backgroundColor: t.colors.text },
            bar,
          ]}
        />
      </View>
    </View>
  );
}
