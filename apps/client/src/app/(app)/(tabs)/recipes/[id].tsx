import { router, useLocalSearchParams } from 'expo-router';
import { randomUUID } from 'expo-crypto';
import { useState } from 'react';
import { Linking, Pressable, View } from 'react-native';

import { ConfirmDialog } from '@/components/ConfirmDialog';
import { FoodThumb } from '@/components/FoodThumb';
import { Tag } from '@/components/Pill';
import { Button, Card, ErrorText, Loading, Screen, SectionLabel, Text } from '@/components/ui';
import { hostOf } from '@/features/imports/ReviewScreen';
import { ruleBreakHint, ruleBreakText } from '@/features/imports/ruleBreaks';
import { addText, haveSummary, matchLine, type Have } from '@/features/recipes/kitchenMatch';
import { swapLine, swapsOf } from '@/features/recipes/adaptations';
import { RecipeRow, recipeMeta } from '@/features/recipes/RecipeRow';
import { useImportedRecipeActions, useImportedRecipes } from '@/lib/api/imports';
import { useKitchen } from '@/lib/api/kitchen';
import { useList, useListActions } from '@/lib/api/lists';
import { isNotFound, useAdaptations, useDeleteAdaptation, useRecipe } from '@/lib/api/recipes';
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
 *
 * A Recipe Adaptation (ADR 0021) links back to its parent and lists its Swaps above the
 * method, which is the parent's, unchanged. A parent lists its Household's Adaptations.
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
  const parentId = r.kind === 'adaptation' ? r.parent_recipe_id : null;
  const swaps = swapsOf(r.ingredients);

  return (
    <Screen>
      <Card tint={tint} style={{ gap: t.space.sm }}>
        <FoodThumb emoji={recipeEmoji(r.title)} tint={tint} size={56} onWhite />
        <Text variant="title" accessibilityRole="header">
          {r.title}
        </Text>
        <Text>{r.summary}</Text>
        <Text variant="label">{recipeMeta(r)}</Text>
        {parentId ? <AdaptedFrom parentId={parentId} /> : null}
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

      {r.kind === 'adaptation' ? null : <Adaptations parentId={r.id} />}

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

      {r.kind === 'imported' ? <YoursActions id={r.id} title={r.title} /> : null}

      {swaps.length > 0 ? (
        <View style={{ gap: t.space.sm }}>
          <SectionLabel>Swaps</SectionLabel>
          {swaps.map((swap) => (
            <Text key={swap.replaces}>{swapLine(swap)}</Text>
          ))}
          <Text variant="caption" muted>
            The method is the original recipe&apos;s, so it may still mention what was swapped.
          </Text>
        </View>
      ) : null}

      {!r.method && r.source_url ? (
        <View style={{ gap: t.space.sm }}>
          <SectionLabel>Method</SectionLabel>
          <Pressable
            accessibilityRole="link"
            onPress={() => Linking.openURL(r.source_url as string)}
            style={{ minHeight: t.touchTarget, justifyContent: 'center' }}
          >
            <Text style={{ textDecorationLine: 'underline' }}>
              Method on {hostOf(r.source_url)}
            </Text>
          </Pressable>
        </View>
      ) : null}

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
        {r.kind === 'imported'
          ? "Your Household's recipe. Only your Household can see it."
          : r.kind === 'adaptation'
            ? "Your Household's version. Only your Household can see it."
            : r.licence === 'Sweep original'
              ? 'A Sweep recipe.'
              : `From ${r.attribution}.`}
      </Text>

      {parentId ? <DeleteAdaptation id={r.id} title={r.title} parentId={parentId} /> : null}
    </Screen>
  );
}

/** "Adapted from Mum's ragu", a link back. Waits quietly if the parent is still loading. */
function AdaptedFrom({ parentId }: { parentId: string }) {
  const t = useTheme();
  const parent = useRecipe(parentId);
  if (!parent.data) return null;
  return (
    <Pressable
      accessibilityRole="link"
      onPress={() => router.push({ pathname: '/recipes/[id]', params: { id: parentId } })}
      style={{ minHeight: t.touchTarget, justifyContent: 'center' }}
    >
      <Text style={{ textDecorationLine: 'underline' }}>Adapted from {parent.data.title}</Text>
    </Pressable>
  );
}

/** The Household's Adaptations of this recipe, each with its Swaps. Hidden when there are none. */
function Adaptations({ parentId }: { parentId: string }) {
  const t = useTheme();
  const kept = useAdaptations(parentId);
  if (!kept.data?.length) return null;
  return (
    <View style={{ gap: t.space.sm }}>
      <SectionLabel>Adaptations</SectionLabel>
      {kept.data.map((a) => (
        <RecipeRow key={a.id} recipe={a} note={a.swaps.map(swapLine).join('; ')} />
      ))}
    </View>
  );
}

/** Any Member may delete an Adaptation. It asks first: meals planned with it go too. */
function DeleteAdaptation({
  id,
  title,
  parentId,
}: {
  id: string;
  title: string;
  parentId: string;
}) {
  const remove = useDeleteAdaptation();
  const [asking, setAsking] = useState(false);
  return (
    <View>
      <Button
        title="Delete this version"
        variant="danger"
        compact
        accessibilityLabel={`Delete ${title}`}
        onPress={() => setAsking(true)}
      />
      {asking ? (
        <ConfirmDialog
          title={`Delete ${title}?`}
          message="It goes for everyone in your Household, and so do any meals planned with it. The original recipe stays."
          confirm="Delete version"
          busy={remove.isPending}
          onCancel={() => setAsking(false)}
          onConfirm={async () => {
            try {
              await remove.mutateAsync({ id, idempotencyKey: randomUUID() });
              setAsking(false);
              router.replace({ pathname: '/recipes/[id]', params: { id: parentId } });
            } catch {
              setAsking(false);
            }
          }}
        />
      ) : null}
      <ErrorText message={remove.error?.message} />
    </View>
  );
}

/**
 * An Imported Recipe: why a Dietary Rule can't be checked (if so), and Edit / Delete.
 * Any Member can do either. Delete asks first: its Planned Meals go with it.
 */
function YoursActions({ id, title }: { id: string; title: string }) {
  const t = useTheme();
  const mine = useImportedRecipes();
  const { remove } = useImportedRecipeActions();
  const [asking, setAsking] = useState(false);
  const ruleBreaks = mine.data?.find((m) => m.id === id)?.rule_breaks ?? [];
  return (
    <View style={{ gap: t.space.sm }}>
      {ruleBreakText(ruleBreaks) ? <Text>{ruleBreakText(ruleBreaks)}</Text> : null}
      {ruleBreakHint(ruleBreaks) ? (
        <Text variant="caption" muted>
          {ruleBreakHint(ruleBreaks)}
        </Text>
      ) : null}
      <View style={{ flexDirection: 'row', gap: t.space.sm }}>
        <Button
          title="Edit"
          variant="secondary"
          compact
          accessibilityLabel={`Edit ${title}`}
          onPress={() => router.push({ pathname: '/recipes/review', params: { edit: id } })}
        />
        <Button
          title="Delete"
          variant="danger"
          compact
          accessibilityLabel={`Delete ${title}`}
          onPress={() => setAsking(true)}
        />
      </View>
      {asking ? (
        <ConfirmDialog
          title={`Delete ${title}?`}
          message="It goes for everyone in your Household, and so do any meals planned with it."
          confirm="Delete recipe"
          busy={remove.isPending}
          onCancel={() => setAsking(false)}
          onConfirm={async () => {
            try {
              await remove.mutateAsync({ id, idempotencyKey: randomUUID() });
              setAsking(false);
              router.replace('/recipes');
            } catch {
              setAsking(false);
            }
          }}
        />
      ) : null}
      <ErrorText message={remove.error?.message} />
    </View>
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
