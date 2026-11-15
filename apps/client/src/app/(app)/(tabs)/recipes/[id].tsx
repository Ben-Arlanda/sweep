import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { FoodThumb } from '@/components/FoodThumb';
import { Tag } from '@/components/Pill';
import { Button, Card, ErrorText, Loading, Screen, SectionLabel, Text } from '@/components/ui';
import { addText, haveSummary, matchLine, type Have } from '@/features/recipes/kitchenMatch';
import { recipeMeta } from '@/features/recipes/RecipeRow';
import { useKitchen } from '@/lib/api/kitchen';
import { useList, useListActions } from '@/lib/api/lists';
import { isNotFound, useRecipe } from '@/lib/api/recipes';
import type { components } from '@/lib/api/schema';
import { ingredientEmoji, recipeEmoji } from '@/theme/foodEmoji';
import { tintFor } from '@/theme/tint';
import { useTheme } from '@/theme/useTheme';

type Line = components['schemas']['RecipeIngredientOut'];
type Kitchen = components['schemas']['KitchenOut'];
type List = components['schemas']['ShoppingListDetailOut'];

/**
 * One recipe, checked against the Kitchen: each ingredient says whether you have it.
 * That's the loop working: what you bought (Kitchen) meets what you could cook.
 *
 * Something you need shows "+ Need": one tap puts it on the Shopping List. Anything
 * already unticked on the list shows "On list", the same rule the planner uses.
 */
export default function RecipeScreen() {
  const t = useTheme();
  const { id } = useLocalSearchParams<{ id: string }>();
  const recipe = useRecipe(id);
  // The Kitchen is optional here: if it fails to load, the recipe still shows.
  const kitchen = useKitchen();
  // Optional too: without the list, "Need" is just a label, with no + to add it.
  const list = useList();

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
  const summary = kitchen.data ? haveSummary(r.ingredients, kitchen.data) : null;

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
          <IngredientRow key={i} line={line} kitchen={kitchen.data} list={list.data} />
        ))}
        {kitchen.isError ? (
          <Text variant="caption" muted>
            Couldn&apos;t check the Kitchen just now.
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
  onList: 'On list',
};

function IngredientRow({
  line,
  kitchen,
  list,
}: {
  line: Line;
  kitchen: Kitchen | undefined;
  list: List | undefined;
}) {
  const t = useTheme();
  // Between the tap and the list coming back from the server, the new item has no
  // Ingredient yet, so `matchLine` can't see it. Remember the tap so it says "On list"
  // straight away.
  const [added, setAdded] = useState(false);
  const match = kitchen ? matchLine(line, kitchen, list?.items) : null;
  const have: Have | null = added && match?.kind === 'need' ? { kind: 'onList' } : match;
  const name = line.ingredient?.name ?? line.raw_text;
  const label = have ? (have.kind === 'low' ? `Have ${have.have}` : HAVE_TEXT[have.kind]) : null;

  return (
    <View
      style={{
        minHeight: t.touchTarget,
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.md,
      }}
    >
      <View
        accessible
        // The status ("Have", "On list", "+ Need") is read from the tag beside it, which
        // sits in a live region, so it's announced when it changes.
        accessibilityLabel={[line.raw_text, line.optional ? 'optional' : null]
          .filter(Boolean)
          .join(', ')}
        style={{ flex: 1, flexDirection: 'row', alignItems: 'center', gap: t.space.md }}
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
      </View>
      {/* The live region reads "On list" out after a tap on +. */}
      <View accessibilityLiveRegion="polite" style={{ alignSelf: 'center' }}>
        {have?.kind === 'need' && list ? (
          <AddToList line={line} listId={list.id} onAdded={() => setAdded(true)} />
        ) : have && label ? (
          <View>
            <Tag
              kind={have.kind === 'need' ? 'need' : 'soft'}
              tint={have.kind === 'have' ? 'mint' : undefined}
            >
              {label}
            </Tag>
          </View>
        ) : null}
      </View>
    </View>
  );
}

/** "+ Need": puts this ingredient on the Shopping List (queued if offline, like any add). */
function AddToList({ line, listId, onAdded }: { line: Line; listId: string; onAdded: () => void }) {
  const t = useTheme();
  const { addItem } = useListActions(listId);
  const text = addText(line);
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Need. Add ${text} to the Shopping List`}
      onPress={() => {
        addItem(text);
        onAdded();
      }}
      // A 44pt target around the small pill (the pill alone is too small to tap).
      style={{ minHeight: t.touchTarget, minWidth: t.touchTarget, justifyContent: 'center' }}
    >
      <Tag kind="need">+ Need</Tag>
    </Pressable>
  );
}
