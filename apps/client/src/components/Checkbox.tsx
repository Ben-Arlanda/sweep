import { useEffect, useRef } from 'react';
import { Text } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withSequence,
  withSpring,
  withTiming,
} from 'react-native-reanimated';

import { useTheme } from '@/theme/useTheme';

/**
 * The round tick. When it becomes checked it "pops": shrinks, then springs past full
 * size and settles, with a little twist.
 *
 * It only pops on a *change*, not on first render. Otherwise opening a list with ten
 * ticked items would set off ten pops at once.
 *
 * Purely visual: the row around it is the accessible checkbox.
 */
export function Checkbox({ checked, size = 26 }: { checked: boolean; size?: number }) {
  const t = useTheme();
  const reduceMotion = useReducedMotion();
  const scale = useSharedValue(1);
  const rotate = useSharedValue(0);
  const first = useRef(true);

  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    if (!checked || reduceMotion) return;
    const pop = t.motion.spring.pop;
    scale.set(withSequence(withTiming(0.6, { duration: 0 }), withSpring(1, pop)));
    rotate.set(withSequence(withTiming(-20, { duration: 0 }), withSpring(0, pop)));
  }, [checked, reduceMotion, rotate, scale, t.motion.spring.pop]);

  const animated = useAnimatedStyle(() => ({
    transform: [{ scale: scale.get() }, { rotate: `${rotate.get()}deg` }],
  }));

  return (
    <Animated.View
      style={[
        {
          width: size,
          height: size,
          borderRadius: size / 2,
          borderWidth: 2,
          borderColor: checked ? t.colors.action : t.colors.border,
          backgroundColor: checked ? t.colors.action : 'transparent',
          alignItems: 'center',
          justifyContent: 'center',
        },
        animated,
      ]}
    >
      {checked ? (
        <Text
          aria-hidden
          style={{ color: t.colors.onAction, fontFamily: t.fonts.bold, fontSize: size * 0.55 }}
        >
          ✓
        </Text>
      ) : null}
    </Animated.View>
  );
}
