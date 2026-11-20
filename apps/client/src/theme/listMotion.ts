import { Platform } from 'react-native';
import { FadeInUp, FadeOut, LinearTransition, ReduceMotion } from 'react-native-reanimated';

import { motion } from './tokens';

// Phones only: on the web, Reanimated leaves rows stuck at position: absolute after they
// enter or move, so they overlap or vanish. The web build is a preview; it skips these.
const native = Platform.OS !== 'web';

/**
 * How rows come and go in a list: fade and a short slide up in, a quicker fade out, and
 * the rows around them glide to their new places. Wrap the list in
 * `<LayoutAnimationConfig skipEntering>` so opening a screen doesn't animate every row.
 */
export const rowEntering = native
  ? FadeInUp.duration(motion.duration.base)
      .withInitialValues({ opacity: 0, transform: [{ translateY: motion.slide }] })
      .reduceMotion(ReduceMotion.System)
  : undefined;

export const rowExiting = native
  ? FadeOut.duration(motion.duration.fast).reduceMotion(ReduceMotion.System)
  : undefined;

export const rowLayout = native
  ? LinearTransition.duration(motion.duration.base).reduceMotion(ReduceMotion.System)
  : undefined;
