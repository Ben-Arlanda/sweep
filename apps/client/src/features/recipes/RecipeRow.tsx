import { Link } from 'expo-router';
import { View } from 'react-native';

import { HeartButton } from '@/components/HeartButton';
import { PressableScale } from '@/components/PressableScale';
import { RecipeArt } from '@/components/RecipeArt';
import { Text } from '@/components/ui';
import type { components } from '@/lib/api/schema';
import { useTheme } from '@/theme/useTheme';

import { courseName } from './courses';
import { cuisineName, minutesText } from './kitchenMatch';
import { useRecipePath } from './recipePath';

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
 * One recipe in a list, with its heart (slice 6e). The row is the link; its name is
 * what's on screen.
 * `note` is a line under it, e.g. why a Dietary Rule can't be checked for it.
 * `brief` shows only time and serves under the title.
 */
export function RecipeRow({
  recipe,
  note,
  brief = false,
}: {
  recipe: Summary;
  note?: string | null;
  brief?: boolean;
}) {
  const t = useTheme();
  const pathname = useRecipePath();
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.xs,
        backgroundColor: t.colors.surface,
        borderRadius: t.radius.md,
        paddingRight: t.space.xs,
        boxShadow: t.shadow.card,
      }}
    >
      <Link href={{ pathname, params: { id: recipe.id } }} asChild>
        <PressableScale
          accessibilityRole="link"
          style={{
            flex: 1,
            minHeight: t.touchTarget + 12,
            flexDirection: 'row',
            alignItems: 'center',
            gap: t.space.md,
            paddingVertical: t.space.sm,
            paddingLeft: t.space.sm,
          }}
        >
          <RecipeArt title={recipe.title} width={44} />
          <View style={{ flex: 1, gap: 2 }}>
            <Text variant="label">{recipe.title}</Text>
            <Text variant="caption" muted>
              {brief
                ? [minutesText(recipe.total_minutes), `Serves ${recipe.servings}`]
                    .filter(Boolean)
                    .join(' · ')
                : recipeMeta(recipe)}
            </Text>
            {note ? <Text variant="caption">{note}</Text> : null}
          </View>
        </PressableScale>
      </Link>
      {/* Beside the link, not inside it: a button inside a link can't be reached on its own. */}
      <HeartButton
        recipeId={recipe.id}
        title={recipe.title}
        favourite={recipe.favourite ?? false}
      />
    </View>
  );
}
