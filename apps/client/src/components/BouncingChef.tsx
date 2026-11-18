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

/**
 * Sweep's chef, bouncing and blinking while Sweep works (Generating screens). Squashes a
 * little as it lands and its shadow shrinks as it rises. The wink is an animated WebP
 * made from the designer's GIF (the lime chef, 2026-11-18), so it sits on any background. Stands still, eyes open,
 * when the phone asks for less motion. Decorative: the heading says what's happening.
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
            transformOrigin: 'bottom',
          },
          body,
        ]}
      >
        <Image
          source={require('../../assets/images/chef-blink.webp')}
          style={{ width: size, height: size }}
          contentFit="contain"
          autoplay={!reduceMotion}
        />
      </Animated.View>
      <Animated.View
        style={[
          {
            width: size * 0.6,
            height: 14,
            marginTop: 6,
            borderRadius: 999,
            backgroundColor: '#5d6155', // a soft grey: reads as a shadow under the lime chef
          },
          shadow,
        ]}
      />
    </View>
  );
}
