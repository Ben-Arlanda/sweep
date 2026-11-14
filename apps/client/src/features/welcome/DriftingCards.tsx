import { useEffect } from 'react';
import { Text, View } from 'react-native';
import Animated, {
  Easing,
  FadeIn,
  ReduceMotion,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withDelay,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';

import { tints, type TintName } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

type CardSpec = {
  emoji: string;
  title: string;
  caption: string;
  tint: TintName;
  /** Position inside the cloud, as fractions of its width and height. */
  x: number;
  y: number;
  tilt: number;
  /** Cards "further away" are smaller, faded and blurred, which gives the depth. */
  far?: boolean;
};

// The same four cards as the website hero: one per part of the loop.
const CARDS: CardSpec[] = [
  { emoji: '📅', title: 'This week', caption: '7 dinners planned', tint: 'sky', x: 0.5, y: 0.62, tilt: -5, far: true },
  { emoji: '🧺', title: 'Weekly shop', caption: '4 to buy · Alice & Bob', tint: 'butter', x: 0.02, y: 0.02, tilt: -7 },
  { emoji: '🥫', title: 'Cabinet', caption: 'Chicken added just now', tint: 'mint', x: 0.46, y: 0.12, tilt: 6 },
  { emoji: '🌮', title: 'Tonight: tacos', caption: 'You have everything', tint: 'blush', x: 0.1, y: 0.5, tilt: 4 },
];

const CARD_WIDTH = 158;
const DRIFT_MS = 3500;

/**
 * The landing screen's floating cards. Each one fades in, tilted, then bobs gently up and
 * down on its own timing so they never move in step. Decorative: screen readers skip it,
 * because the headline underneath says the same thing in words.
 */
export function DriftingCards({ height = 300 }: { height?: number }) {
  return (
    <View
      aria-hidden
      importantForAccessibility="no-hide-descendants"
      style={{ height, width: '100%', maxWidth: 400, alignSelf: 'center' }}
    >
      {CARDS.map((card, i) => (
        <DriftingCard key={card.title} card={card} index={i} cloudHeight={height} />
      ))}
    </View>
  );
}

function DriftingCard({
  card,
  index,
  cloudHeight,
}: {
  card: CardSpec;
  index: number;
  cloudHeight: number;
}) {
  const t = useTheme();
  const reduceMotion = useReducedMotion();
  const lift = useSharedValue(0);
  // The cards sit on the always-dark hero, so they keep their light pastels in dark mode.
  const tint = tints.light[card.tint];

  useEffect(() => {
    if (reduceMotion) return;
    // Up 12, back down, forever. Each card starts at a different moment.
    lift.set(
      withDelay(
        index * 600,
        withRepeat(
          withSequence(
            withTiming(-12, { duration: DRIFT_MS, easing: Easing.inOut(Easing.sin) }),
            withTiming(0, { duration: DRIFT_MS, easing: Easing.inOut(Easing.sin) }),
          ),
          -1,
        ),
      ),
    );
  }, [index, lift, reduceMotion]);

  const drift = useAnimatedStyle(() => ({
    transform: [{ translateY: lift.get() }, { rotate: `${card.tilt}deg` }],
  }));

  return (
    <Animated.View
      entering={FadeIn.delay(150 + index * 120)
        .duration(t.motion.duration.slow * 2)
        .reduceMotion(ReduceMotion.System)}
      style={{
        position: 'absolute',
        left: `${card.x * 100}%`,
        top: card.y * cloudHeight,
        opacity: card.far ? 0.55 : 1,
      }}
    >
      <Animated.View
        style={[
          {
            width: card.far ? CARD_WIDTH * 0.9 : CARD_WIDTH,
            backgroundColor: tint.bg,
            borderRadius: t.radius.lg,
            borderWidth: 3,
            borderColor: '#ffffff',
            padding: t.space.md,
            gap: 2,
            boxShadow: '0px 20px 40px -20px rgba(0, 0, 0, 0.6)',
            filter: card.far ? [{ blur: 2 }] : undefined,
          },
          drift,
        ]}
      >
        <Text style={{ fontSize: 28 }}>{card.emoji}</Text>
        <Text style={[t.type.heading, { fontSize: 16, lineHeight: 19, color: tint.text }]}>
          {card.title}
        </Text>
        <Text style={[t.type.caption, { fontSize: 12, lineHeight: 16, color: tint.text }]}>
          {card.caption}
        </Text>
      </Animated.View>
    </Animated.View>
  );
}
