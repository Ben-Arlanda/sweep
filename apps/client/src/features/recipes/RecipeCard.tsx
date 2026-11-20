import { Link } from 'expo-router';
import { View } from 'react-native';

import { HeartButton } from '@/components/HeartButton';
import { PressableScale } from '@/components/PressableScale';
import { RecipeArt } from '@/components/RecipeArt';
import { Text } from '@/components/ui';
import type { components } from '@/lib/api/schema';
import { useTheme } from '@/theme/useTheme';

import { minutesText } from './kitchenMatch';
import { useRecipePath } from './recipePath';

type Summary = components['schemas']['RecipeSummaryOut'];

/**
 * One recipe in a two-across grid (All recipes): picture, heart, title, time and serves.
 * The heart sits beside the link, not inside it, so it can be reached on its own.
 */
export function RecipeCard({ recipe }: { recipe: Summary }) {
  const t = useTheme();
  const pathname = useRecipePath();
  const meta = [minutesText(recipe.total_minutes), `Serves ${recipe.servings}`]
    .filter(Boolean)
    .join(' · ');
  return (
    <View
      style={{
        flexGrow: 1,
        flexBasis: 140,
        backgroundColor: t.colors.surface,
        borderRadius: t.radius.lg,
        overflow: 'hidden',
        boxShadow: t.shadow.card,
      }}
    >
      <Link href={{ pathname, params: { id: recipe.id } }} asChild>
        <PressableScale accessibilityRole="link" accessibilityLabel={`${recipe.title}. ${meta}`}>
          <RecipeArt
            title={recipe.title}
            image={recipe.image}
            width="100%"
            height={96}
            radius={0}
            emojiSize={44}
          />
          <View
            style={{
              paddingTop: 10,
              paddingHorizontal: t.space.md,
              paddingBottom: t.space.md,
              gap: 3,
            }}
          >
            <Text variant="label" numberOfLines={2}>
              {recipe.title}
            </Text>
            <Text variant="caption" muted style={{ fontVariant: ['tabular-nums'] }}>
              {meta}
            </Text>
          </View>
        </PressableScale>
      </Link>
      <View style={{ position: 'absolute', top: t.space.xs, right: t.space.xs }}>
        <HeartButton
          recipeId={recipe.id}
          title={recipe.title}
          favourite={recipe.favourite ?? false}
        />
      </View>
    </View>
  );
}
