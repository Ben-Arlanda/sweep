import { router, useLocalSearchParams } from 'expo-router';
import { View } from 'react-native';

import { FoodThumb } from '@/components/FoodThumb';
import { Tag } from '@/components/Pill';
import { Button, Card, ErrorText, Loading, Screen, SectionLabel, Text } from '@/components/ui';
import { haveSummary, matchLine, type Have } from '@/features/recipes/cabinetMatch';
import { recipeMeta } from '@/features/recipes/RecipeRow';
import { useCabinet } from '@/lib/api/cabinet';
import { isNotFound, useRecipe } from '@/lib/api/recipes';
import type { components } from '@/lib/api/schema';
import { ingredientEmoji, recipeEmoji } from '@/theme/foodEmoji';
import { tintFor } from '@/theme/tint';
import { useTheme } from '@/theme/useTheme';

type Line = components['schemas']['RecipeIngredientOut'];
type Cabinet = components['schemas']['CabinetOut'];

/**
 * One recipe, checked against the Cabinet: each ingredient says whether you have it.
 * That's the loop working: what you bought (Cabinet) meets what you could cook.
 */
export default function RecipeScreen() {
  const t = useTheme();
  const { id } = useLocalSearchParams<{ id: string }>();
  const recipe = useRecipe(id);
  // The Cabinet is optional here: if it fails to load, the recipe still shows.
  const cabinet = useCabinet();

  if (recipe.isPending) return <Loading />;
  if (recipe.isError && isNotFound(recipe.error)) {
    return (
      <Screen>
        <Text variant="title" accessibilityRole="header">
          Recipe not found
        </Text>
        <Text>It may have been removed, or the link is incomplete.</Text>
        <Button title="Browse recipes" onPress={() => router.replace('/recipes')} />
      </Screen>
    );
  }
  if (recipe.isError) {
    return (
      <Screen>
        <ErrorText message={recipe.error.message} />
        <Button title="Try again" onPress={() => recipe.refetch()} />
      </Screen>
    );
  }

  const r = recipe.data;
  const tint = tintFor(r.title);
  const summary = cabinet.data ? haveSummary(r.ingredients, cabinet.data) : null;

  return (
    <Screen>
      <Card tint={tint} style={{ gap: t.space.sm }}>
        <FoodThumb emoji={recipeEmoji(r.title)} tint={tint} size={56} onWhite />
        <Text variant="title" accessibilityRole="header">
          {r.title}
        </Text>
        <Text>{r.summary}</Text>
        <Text variant="label">{recipeMeta(r)}</Text>
        {summary && summary.total > 0 ? (
          <View style={{ marginTop: t.space.xs }}>
            <Tag kind={summary.have === summary.total ? 'action' : 'soft'}>
              {summary.have === summary.total
                ? 'You have everything'
                : `You have ${summary.have} of ${summary.total}`}
            </Tag>
          </View>
        ) : null}
      </Card>

      <View style={{ gap: t.space.sm }}>
        <SectionLabel>Ingredients</SectionLabel>
        {r.ingredients.map((line, i) => (
          <IngredientRow key={i} line={line} cabinet={cabinet.data} />
        ))}
        {cabinet.isError ? (
          <Text variant="caption" muted>
            Couldn&apos;t check the Cabinet just now.
          </Text>
        ) : null}
      </View>

      {r.method ? (
        <View style={{ gap: t.space.sm }}>
          <SectionLabel>Method</SectionLabel>
          {r.method.map((step, i) => (
            <View key={i} style={{ flexDirection: 'row', gap: t.space.md }}>
              <Text variant="heading" style={{ minWidth: 24 }}>
                {i + 1}
              </Text>
              <Text style={{ flex: 1 }}>{step}</Text>
            </View>
          ))}
        </View>
      ) : null}

      <Text variant="caption" muted>
        {r.licence === 'Sweep original' ? 'A Sweep recipe.' : `From ${r.attribution}.`}
      </Text>
    </Screen>
  );
}

const HAVE_TEXT: Record<Have['kind'], string> = {
  have: 'Have',
  low: 'Low',
  check: 'Check',
  need: 'Need',
};

function IngredientRow({ line, cabinet }: { line: Line; cabinet: Cabinet | undefined }) {
  const t = useTheme();
  const have = cabinet ? matchLine(line, cabinet) : null;
  const name = line.ingredient?.name ?? line.raw_text;
  const label = have
    ? have.kind === 'low'
      ? `Have ${have.have}`
      : HAVE_TEXT[have.kind]
    : null;

  return (
    <View
      accessible
      accessibilityLabel={[line.raw_text, line.optional ? 'optional' : null, label]
        .filter(Boolean)
        .join(', ')}
      style={{
        minHeight: t.touchTarget,
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.md,
      }}
    >
      <FoodThumb emoji={ingredientEmoji(line.ingredient)} tint={tintFor(name)} size={36} />
      <View style={{ flex: 1 }}>
        <Text>{line.raw_text}</Text>
        {line.optional ? (
          <Text variant="caption" muted>
            Optional
          </Text>
        ) : null}
      </View>
      {have && label ? (
        <View style={{ alignSelf: 'center' }}>
          <Tag
          kind={have.kind === 'need' ? 'need' : 'soft'}
          tint={have.kind === 'have' ? 'mint' : undefined}
        >
          {label}
          </Tag>
        </View>
      ) : null}
    </View>
  );
}
