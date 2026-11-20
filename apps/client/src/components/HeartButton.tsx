import { Heart } from 'lucide-react-native';
import Animated, {
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withSequence,
  withSpring,
  withTiming,
} from 'react-native-reanimated';

import { haptic } from '@/lib/haptics';
import { useFavourite } from '@/lib/api/planning';
import { useTheme } from '@/theme/useTheme';

import { Icon } from './Icon';
import { PressableScale } from './PressableScale';

/**
 * The heart on a recipe (slice 6e): a Favourite for the whole Household, which Sweep
 * puts first among equals when planning. A toggle button, so screen readers hear
 * "Favourite, selected" and not just "heart".
 */
export function HeartButton({
  recipeId,
  title,
  favourite,
  size = 44,
}: {
  recipeId: string;
  title: string;
  favourite: boolean;
  size?: number;
}) {
  const t = useTheme();
  const toggle = useFavourite();
  const on = toggle.isPending ? (toggle.variables?.on ?? favourite) : favourite;
  const reduceMotion = useReducedMotion();
  const scale = useSharedValue(1);
  const beat = useAnimatedStyle(() => ({ transform: [{ scale: scale.get() }] }));

  function press() {
    haptic.tap();
    if (!reduceMotion) {
      // Hearting lands from smaller; un-hearting is a smaller, quieter dip.
      const from = on ? 0.9 : 0.75;
      scale.set(
        withSequence(withTiming(from, { duration: 0 }), withSpring(1, t.motion.spring.pop)),
      );
    }
    toggle.mutate({ recipeId, on: !on });
  }
  return (
    <PressableScale
      accessibilityRole="button"
      accessibilityLabel={`Favourite ${title}`}
      accessibilityState={{ selected: on }}
      aria-pressed={on}
      onPress={press}
      style={{
        width: Math.max(size, t.touchTarget),
        height: Math.max(size, t.touchTarget),
        borderRadius: t.radius.pill,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.surface,
      }}
    >
      <Animated.View style={beat}>
        <Icon
          icon={Heart}
          size={22}
          color={on ? t.colors.danger : t.colors.text}
          fill={on ? t.colors.danger : 'transparent'}
        />
      </Animated.View>
    </PressableScale>
  );
}
