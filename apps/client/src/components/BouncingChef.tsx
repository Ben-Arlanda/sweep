import { Image } from 'expo-image';
import { useEffect } from 'react';
import { View } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';

const BOUNCE_MS = 550; // up, then down: about one bounce a second
// The picture's own background, so it sits on a matching circle in either theme.
const CHEF_PAPER = '#fcf7f3';

/**
 * Sweep's chef, bouncing while Sweep works (Generating screens). Squashes a little as it
 * lands and its shadow shrinks as it rises. Stands still when the phone asks for less
 * motion. Decorative: the heading beside it says what's happening.
 */
export function BouncingChef({ size = 180 }: { size?: number }) {
  const reduceMotion = useReducedMotion();
  const lift = useSharedValue(0); // 0 = on the ground, 1 = at the top

  useEffect(() => {
    if (reduceMotion) return;
    lift.set(
      withRepeat(
        withSequence(
          withTiming(1, { duration: BOUNCE_MS, easing: Easing.out(Easing.quad) }),
          withTiming(0, { duration: BOUNCE_MS, easing: Easing.in(Easing.quad) }),
        ),
        -1,
      ),
    );
  }, [lift, reduceMotion]);

  const body = useAnimatedStyle(() => {
    const up = lift.get();
    // Squash near the ground, stretch on the way up.
    const squash = up < 0.15 ? 1 - (0.15 - up) * 0.6 : 1;
    return {
      transform: [{ translateY: -up * size * 0.28 }, { scaleY: squash }, { scaleX: 2 - squash }],
    };
  });
  const shadow = useAnimatedStyle(() => ({
    transform: [{ scaleX: 1 - lift.get() * 0.45 }],
    opacity: 0.3 - lift.get() * 0.18,
  }));

  return (
    <View
      aria-hidden
      importantForAccessibility="no-hide-descendants"
      style={{ alignItems: 'center', justifyContent: 'flex-end', height: size * 1.35 }}
    >
      <Animated.View
        style={[
          {
            width: size,
            height: size,
            borderRadius: size / 2,
            backgroundColor: CHEF_PAPER,
            overflow: 'hidden',
            transformOrigin: 'bottom',
          },
          body,
        ]}
      >
        <Image
          source={require('../../assets/images/chef.png')}
          style={{ width: size, height: size }}
          contentFit="cover"
        />
      </Animated.View>
      <Animated.View
        style={[
          {
            width: size * 0.6,
            height: 14,
            marginTop: 6,
            borderRadius: 999,
            backgroundColor: '#8a7a50',
          },
          shadow,
        ]}
      />
    </View>
  );
}
