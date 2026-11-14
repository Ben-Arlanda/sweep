import { Pressable, type PressableProps, type StyleProp, type ViewStyle } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated';

import { useTheme } from '@/theme/useTheme';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

/**
 * A Pressable that shrinks slightly while held, so every tap feels physical.
 *
 * The scale lives in a Reanimated "shared value": it's updated on the UI thread, so the
 * animation stays smooth even if JavaScript is busy (e.g. a list re-rendering after sync).
 */
export function PressableScale({
  style,
  onPressIn,
  onPressOut,
  ...props
}: Omit<PressableProps, 'style'> & { style?: StyleProp<ViewStyle> }) {
  const t = useTheme();
  const reduceMotion = useReducedMotion();
  const scale = useSharedValue(1);
  const animated = useAnimatedStyle(() => ({ transform: [{ scale: scale.get() }] }));

  return (
    <AnimatedPressable
      {...props}
      onPressIn={(e) => {
        if (!reduceMotion) scale.set(withSpring(t.motion.pressScale, t.motion.spring.press));
        onPressIn?.(e);
      }}
      onPressOut={(e) => {
        scale.set(reduceMotion ? 1 : withSpring(1, t.motion.spring.press));
        onPressOut?.(e);
      }}
      style={[style, animated]}
    />
  );
}
