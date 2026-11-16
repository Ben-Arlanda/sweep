import { Link } from 'expo-router';
import { View } from 'react-native';

import { FoodThumb } from '@/components/FoodThumb';
import { PressableScale } from '@/components/PressableScale';
import { Text } from '@/components/ui';
import type { components } from '@/lib/api/schema';
import { recipeEmoji } from '@/theme/foodEmoji';
import { tintFor } from '@/theme/tint';
import { useTheme } from '@/theme/useTheme';

import { courseName } from './courses';
import { cuisineName, minutesText } from './kitchenMatch';

type Summary = components['schemas']['RecipeSummaryOut'];

export function recipeMeta(r: Pick<Summary, 'course' | 'total_minutes' | 'servings' | 'cuisine'>) {
  return [
    courseName(r.course),
    minutesText(r.total_minutes),
    `Serves ${r.servings}`,
    cuisineName(r.cuisine),
  ]
    .filter(Boolean)
    .join(' · ');
}

/**
 * One recipe in a list. The whole row is the link; its name is what's on screen.
 * `note` is a line under it, e.g. why a Dietary Rule can't be checked for it.
 */
export function RecipeRow({ recipe, note }: { recipe: Summary; note?: string | null }) {
  const t = useTheme();
  return (
    <Link href={{ pathname: '/recipes/[id]', params: { id: recipe.id } }} asChild>
      <PressableScale
        accessibilityRole="link"
        style={{
          minHeight: t.touchTarget + 12,
          flexDirection: 'row',
          alignItems: 'center',
          gap: t.space.md,
          backgroundColor: t.colors.surface,
          borderRadius: t.radius.md,
          paddingVertical: t.space.sm,
          paddingHorizontal: t.space.sm,
          boxShadow: t.shadow.card,
        }}
      >
        <FoodThumb emoji={recipeEmoji(recipe.title)} tint={tintFor(recipe.title)} size={44} />
        <View style={{ flex: 1, gap: 2 }}>
          <Text variant="label">{recipe.title}</Text>
          <Text variant="caption" muted>
            {recipeMeta(recipe)}
          </Text>
          {note ? <Text variant="caption">{note}</Text> : null}
        </View>
      </PressableScale>
    </Link>
  );
}
