import { useEffect, useRef } from 'react';
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
 * The round tick. When it becomes checked it settles in from slightly smaller, and the
 * tick mark fades in: quick and calm, no bounce.
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
  const mark = useSharedValue(checked ? 1 : 0);
  const first = useRef(true);

  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    if (!checked || reduceMotion) {
      mark.set(checked ? 1 : 0);
      return;
    }
    scale.set(withSequence(withTiming(0.85, { duration: 0 }), withSpring(1, t.motion.spring.pop)));
    mark.set(
      withSequence(
        withTiming(0, { duration: 0 }),
        withTiming(1, { duration: t.motion.duration.fast }),
      ),
    );
  }, [checked, reduceMotion, mark, scale, t.motion.spring.pop, t.motion.duration.fast]);

  const animated = useAnimatedStyle(() => ({ transform: [{ scale: scale.get() }] }));
  const markStyle = useAnimatedStyle(() => ({ opacity: mark.get() }));

  return (
    <Animated.View
      style={[
        {
          width: size,
          height: size,
          borderRadius: size / 2,
          borderWidth: checked ? 2 : 1.5,
          // Empty ring at 3:1 so the control is visible (WCAG 1.4.11).
          borderColor: checked ? t.colors.action : t.colors.switchOff,
          backgroundColor: checked ? t.colors.action : 'transparent',
          alignItems: 'center',
          justifyContent: 'center',
        },
        animated,
      ]}
    >
      {checked ? (
        <Animated.Text
          aria-hidden
          style={[
            { color: t.colors.onAction, fontFamily: t.fonts.bold, fontSize: size * 0.55 },
            markStyle,
          ]}
        >
          ✓
        </Animated.Text>
      ) : null}
    </Animated.View>
  );
}
