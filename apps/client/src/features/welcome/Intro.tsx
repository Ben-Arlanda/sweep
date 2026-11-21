import { useEffect } from 'react';
import { StyleSheet } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withDelay,
  withSequence,
  withTiming,
} from 'react-native-reanimated';

import { useTheme } from '@/theme/useTheme';

const LOGO = 120;
// Grow in, settle, hold, then zoom through the camera and reveal the welcome screen.
const GROW = 700;
const SETTLE = 250;
const HOLD = 350;
const ZOOM = 550;
export const INTRO_MS = GROW + SETTLE + HOLD + ZOOM;

/**
 * The brand intro before the welcome screen: the app's page colour, then the logo grows
 * from tiny, settles with a lime ripple, and zooms past the viewer as the page fades away.
 * With "reduce motion" on it simply shows the logo, then fades.
 */
export function Intro({ onDone }: { onDone: () => void }) {
  const t = useTheme();
  const reduceMotion = useReducedMotion();
  const scale = useSharedValue(reduceMotion ? 1 : 0.08);
  const logoOpacity = useSharedValue(reduceMotion ? 1 : 0);
  const ripple = useSharedValue(0);
  const cover = useSharedValue(1);

  useEffect(() => {
    if (reduceMotion) {
      cover.set(withDelay(600, withTiming(0, { duration: 250 })));
      const done = setTimeout(onDone, 850);
      return () => clearTimeout(done);
    }
    const out = Easing.out(Easing.cubic);
    scale.set(
      withSequence(
        withTiming(1.12, { duration: GROW, easing: out }),
        withTiming(1, { duration: SETTLE, easing: Easing.inOut(Easing.quad) }),
        withDelay(HOLD, withTiming(9, { duration: ZOOM, easing: Easing.in(Easing.cubic) })),
      ),
    );
    logoOpacity.set(
      withSequence(
        withTiming(1, { duration: GROW * 0.6 }),
        withDelay(GROW * 0.4 + SETTLE + HOLD + ZOOM * 0.4, withTiming(0, { duration: ZOOM * 0.6 })),
      ),
    );
    ripple.set(withDelay(GROW, withTiming(1, { duration: 700, easing: out })));
    cover.set(
      withDelay(GROW + SETTLE + HOLD + ZOOM * 0.3, withTiming(0, { duration: ZOOM * 0.7 })),
    );
    const done = setTimeout(onDone, INTRO_MS + 50);
    return () => clearTimeout(done);
  }, [reduceMotion, onDone, scale, logoOpacity, ripple, cover]);

  const coverStyle = useAnimatedStyle(() => ({ opacity: cover.get() }));
  const logoStyle = useAnimatedStyle(() => ({
    opacity: logoOpacity.get(),
    transform: [{ scale: scale.get() }],
  }));
  const rippleStyle = useAnimatedStyle(() => ({
    opacity: (1 - ripple.get()) * 0.6 * (ripple.get() > 0 ? 1 : 0),
    transform: [{ scale: 0.9 + ripple.get() * 1.4 }],
  }));

  return (
    <Animated.View
      aria-hidden
      pointerEvents="none"
      style={[
        StyleSheet.absoluteFill,
        {
          backgroundColor: t.colors.background,
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 10,
        },
        coverStyle,
      ]}
    >
      <Animated.View
        style={[
          {
            position: 'absolute',
            width: LOGO,
            height: LOGO,
            borderRadius: LOGO / 2,
            borderWidth: 3,
            borderColor: t.colors.action,
          },
          rippleStyle,
        ]}
      />
      <Animated.Image
        source={require('../../../assets/images/sweep-logo-512.png')}
        style={[{ width: LOGO, height: LOGO }, logoStyle]}
      />
    </Animated.View>
  );
}
