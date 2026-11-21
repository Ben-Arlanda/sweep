import { useEffect } from 'react';
import {
  cancelAnimation,
  Easing,
  useReducedMotion,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';

/** Where a still page rests: every piece of every mock is showing at this point. */
export const REST = 0.6;

/**
 * One clock per onboarding page: a value running 0 → 1 every `ms`, over and over, while
 * the page is on screen. Each piece of the mock reads it to know when to show. Holds still
 * at REST when the page is off screen or the phone asks for less motion.
 */
export function useLoop(active: boolean, ms = 6000) {
  const reduceMotion = useReducedMotion();
  const p = useSharedValue(REST);

  useEffect(() => {
    if (!active || reduceMotion) {
      cancelAnimation(p);
      p.set(REST);
      return;
    }
    p.set(0);
    p.set(withRepeat(withTiming(1, { duration: ms, easing: Easing.linear }), -1, false));
    return () => cancelAnimation(p);
  }, [active, reduceMotion, ms, p]);

  return p;
}
