import { Heart } from 'lucide-react-native';

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
  return (
    <PressableScale
      accessibilityRole="button"
      accessibilityLabel={`Favourite ${title}`}
      accessibilityState={{ selected: on }}
      aria-pressed={on}
      onPress={() => toggle.mutate({ recipeId, on: !on })}
      style={{
        width: Math.max(size, t.touchTarget),
        height: Math.max(size, t.touchTarget),
        borderRadius: t.radius.pill,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.surface,
      }}
    >
      <Icon
        icon={Heart}
        size={22}
        color={on ? t.colors.danger : t.colors.text}
        fill={on ? t.colors.danger : 'transparent'}
      />
    </PressableScale>
  );
}
