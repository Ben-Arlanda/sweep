import type { ReactNode } from 'react';
import type { StyleProp, ViewStyle } from 'react-native';
import Animated, { FadeInDown, ReduceMotion } from 'react-native-reanimated';

import { useTheme } from '@/theme/useTheme';

/**
 * Springs its child up into place, `index` steps after the first one, so a group of
 * Rises comes in one after another (the "rise" motion in ADR 0007).
 *
 * It only animates when it first appears (Reanimated's `entering`). To replay it, give
 * the parent a new `key` so React mounts it again.
 */
export function Rise({
  index = 0,
  delay = 0,
  style,
  children,
}: {
  index?: number;
  /** Extra wait, in ms, before the first item. */
  delay?: number;
  style?: StyleProp<ViewStyle>;
  children: ReactNode;
}) {
  const t = useTheme();
  return (
    <Animated.View
      style={style}
      entering={FadeInDown.delay(delay + index * t.motion.staggerMs * 2)
        .springify()
        .damping(t.motion.spring.gentle.damping)
        .stiffness(t.motion.spring.gentle.stiffness)
        .reduceMotion(ReduceMotion.System)}
    >
      {children}
    </Animated.View>
  );
}
