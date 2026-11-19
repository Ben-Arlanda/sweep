import { useQueryClient } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import {
  ArrowLeftRight,
  CalendarDays,
  ChefHat,
  CirclePlus,
  Clock,
  Package,
  ShoppingCart,
  Users,
  type LucideIcon,
} from 'lucide-react-native';
import { randomUUID } from 'expo-crypto';
import { useState } from 'react';
import { Linking, Pressable, View } from 'react-native';

import { ConfirmDialog } from '@/components/ConfirmDialog';
import { FoodThumb } from '@/components/FoodThumb';
import { Segmented } from '@/components/Segmented';
import { HeartButton } from '@/components/HeartButton';
import { Icon } from '@/components/Icon';
import { Tag } from '@/components/Pill';
import { useToast } from '@/components/Toast';
import { RecipeArt } from '@/components/RecipeArt';
import { Button, ErrorText, Loading, Screen, SectionLabel, Text } from '@/components/ui';
import { formatDay } from '@/features/chat/format';
import { dayParts } from '@/features/mealPlan/week';
import { hostOf } from '@/features/imports/ReviewScreen';
import { ruleBreakHint, ruleBreakText } from '@/features/imports/ruleBreaks';
import { courseName, type Course } from '@/features/recipes/courses';
import {
  addText,
  haveSummary,
  matchLine,
  minutesText,
  type Have,
} from '@/features/recipes/kitchenMatch';
import { swapLine, swapsOf } from '@/features/recipes/adaptations';
import { PickDaySheet } from '@/features/mealPlan/PickDaySheet';
import { RecipeRow } from '@/features/recipes/RecipeRow';
import { useRecipePath } from '@/features/recipes/recipePath';
import { conversationKeys, useDecideProposal } from '@/lib/api/conversations';
import { useImportedRecipeActions, useImportedRecipes } from '@/lib/api/imports';
import { useKitchen } from '@/lib/api/kitchen';
import { useList, useListActions } from '@/lib/api/lists';
import { useMealPlan } from '@/lib/api/mealPlan';
import { planTap, usePlanDay } from '@/lib/api/planning';
import { isNotFound, useAdaptations, useDeleteAdaptation, useRecipe } from '@/lib/api/recipes';
import type { components } from '@/lib/api/schema';
import { ingredientEmoji } from '@/theme/foodEmoji';
import { tintFor } from '@/theme/tint';
import { PageColors } from '@/theme/PageColors';
import { useTheme, type Theme } from '@/theme/useTheme';

type Line = components['schemas']['RecipeIngredientOut'];

/**
 * One recipe, checked against the Kitchen: each ingredient says whether you have it.
 * That's the loop working: what you bought (Kitchen) meets what you could cook.
 *
 * Something you need shows "Add to list": one tap puts it on the Shopping List. Anything
 * already unticked on the list shows "On list", the same rule the planner uses.
 *
 * Laid out as Ingredients | Method tabs (slice 6e, premium redesign). Notes sit at the
 * bottom of Method: a Recipe Adaptation's (ADR 0021) Swaps, a parent's Adaptations, and
 * where the recipe came from.
 */
function RecipeContent() {
  const t = useTheme();
  // `plan`: opened from Dinner Ideas to plan it for that day (slice 6e).
  // `swap` + `date`: opened from a plan's swap list to swap that day to this (ADR 0025).
  // `serves`: the Dinner ideas setup's Serves, for the Planned Meal (slice 6f).
  const { id, plan, swap, date, serves } = useLocalSearchParams<{
    id: string;
    plan?: string;
    swap?: string;
    date?: string;
    serves?: string;
  }>();
  const recipe = useRecipe(id);
  // The Kitchen is optional here: if it fails to load, the recipe still shows.
  const kitchen = useKitchen();
  // Optional too: without the list, "Need" is just a label, with no + to add it.
  const list = useList();
  const [tab, setTab] = useState<Tab>('ingredients');
  const need = useNeedActions(list.data?.id ?? '');

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
  const summary = kitchen.data ? haveSummary(r.ingredients, kitchen.data) : null;
  const parentId = r.kind === 'adaptation' ? r.parent_recipe_id : null;
  const swaps = swapsOf(r.ingredients);
  const statusOf = (line: Line, i: number): Have | null => {
    const match = kitchen.data ? matchLine(line, kitchen.data, list.data?.items) : null;
    // Just tapped: the list hasn't come back with it linked yet, but it's on there.
    return match?.kind === 'need' && need.added.has(i) ? { kind: 'onList' } : match;
  };
  const missing = list.data
    ? r.ingredients
        .map((line, i) => ({ line, i }))
        .filter(({ line, i }) => statusOf(line, i)?.kind === 'need')
    : [];

  return (
    <Screen
      footer={
        plan ? (
          <PlanForDay
            date={plan}
            recipeId={r.id}
            title={r.title}
            servings={Number(serves) > 0 ? Number(serves) : null}
          />
        ) : swap && date ? (
          <SwapToThis proposalId={swap} date={date} recipeId={r.id} />
        ) : r.course === 'main' ? (
          // Any main can be tonight's dinner, however you found it.
          <PlanForDay
            date={null}
            recipeId={r.id}
            title={r.title}
            servings={Number(serves) > 0 ? Number(serves) : null}
          />
        ) : null
      }
    >
      {/* The picture slot (RecipeArt) with the heart and what it uses from the Kitchen. */}
      <View>
        <RecipeArt title={r.title} width="100%" height={200} radius={t.radius.xl} emojiSize={88} />
        {r.kind === 'adaptation' ? null : (
          <View style={{ position: 'absolute', top: t.space.md, right: t.space.md }}>
            <HeartButton recipeId={r.id} title={r.title} favourite={r.favourite ?? false} />
          </View>
        )}
        {summary && summary.have > 0 ? (
          <View style={{ position: 'absolute', left: t.space.md, bottom: t.space.md }}>
            <Tag kind={summary.have === summary.total ? 'action' : 'soft'}>
              {summary.have === summary.total
                ? '✓ You have everything'
                : `✓ Uses ${summary.have} Kitchen ${summary.have === 1 ? 'item' : 'items'}`}
            </Tag>
          </View>
        ) : null}
      </View>

      <View style={{ gap: t.space.sm }}>
        <Text variant="title" accessibilityRole="header" style={{ color: t.colors.onBackground }}>
          {r.title}
        </Text>
        {r.summary ? <Text>{r.summary}</Text> : null}
        <MetaRow recipe={r} />
        {swap && date ? <SwappingPill proposalId={swap} date={date} /> : null}
        {parentId ? <AdaptedFrom parentId={parentId} /> : null}
      </View>

      <Segmented
        label="Recipe"
        value={tab}
        onChange={setTab}
        options={[
          { value: 'ingredients', label: 'Ingredients' },
          { value: 'method', label: 'Method' },
        ]}
      />

      {tab === 'ingredients' ? (
        <View style={{ gap: t.space.sm }}>
          <View
            style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}
          >
            <Text
              variant="heading"
              role="heading"
              aria-level={2}
              style={{ color: t.colors.onBackground }}
            >
              Ingredients ({r.ingredients.length})
            </Text>
            {missing.length > 0 ? (
              <Button
                title={`Add ${missing.length} missing`}
                accessibilityLabel={`Add ${missing.length} missing ingredients to the shopping list`}
                icon={ShoppingCart}
                variant="secondary"
                compact
                onPress={() => need.add(missing)}
              />
            ) : null}
          </View>
          {r.ingredients.map((line, i) => (
            <IngredientRow
              key={i}
              line={line}
              have={statusOf(line, i)}
              onAdd={list.data ? () => need.add([{ line, i }]) : undefined}
            />
          ))}
          {kitchen.isError ? (
            <Text variant="caption" style={{ color: t.colors.onBackgroundMuted }}>
              Couldn&apos;t check the Kitchen just now.
            </Text>
          ) : null}
        </View>
      ) : null}

      {tab === 'method' ? (
        <View style={{ gap: t.space.sm + 2 }}>
          {swaps.length > 0 ? (
            <Text variant="caption" style={{ color: t.colors.onBackgroundMuted }}>
              The method is the original recipe&apos;s, so it may still mention what was swapped
              (see Notes below).
            </Text>
          ) : null}
          {r.method ? (
            r.method.map((step, i) => (
              <View
                key={i}
                style={[
                  cardStyle(t),
                  { flexDirection: 'row', alignItems: 'flex-start', padding: 14 },
                ]}
              >
                <View
                  style={{
                    width: 26,
                    height: 26,
                    borderRadius: 13,
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: t.colors.selected,
                  }}
                >
                  <Text
                    style={{ fontFamily: t.fonts.bold, fontSize: 13, color: t.colors.onSelected }}
                  >
                    {i + 1}
                  </Text>
                </View>
                <Text style={{ flex: 1 }}>{step}</Text>
              </View>
            ))
          ) : r.source_url ? (
            <Pressable
              accessibilityRole="link"
              onPress={() => Linking.openURL(r.source_url as string)}
              style={{ minHeight: t.touchTarget, justifyContent: 'center' }}
            >
              <Text style={{ textDecorationLine: 'underline' }}>
                Method on {hostOf(r.source_url)}
              </Text>
            </Pressable>
          ) : (
            <Text muted>No method saved for this recipe.</Text>
          )}
        </View>
      ) : null}

      {tab === 'method' ? (
        <View style={[cardStyle(t), { gap: t.space.lg }]}>
          <Text variant="heading" role="heading" aria-level={2}>
            Notes
          </Text>
          {swaps.length > 0 ? (
            <View style={{ gap: t.space.sm }}>
              <SectionLabel>Swaps</SectionLabel>
              {swaps.map((swap) => (
                <Text key={swap.replaces}>{swapLine(swap)}</Text>
              ))}
            </View>
          ) : null}
          {r.kind === 'adaptation' ? null : <Adaptations parentId={r.id} />}
          {r.kind === 'imported' ? <YoursActions id={r.id} title={r.title} /> : null}
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
        </View>
      ) : null}
    </Screen>
  );
}

/** Method steps and Notes: white cards with a hairline edge. */
function cardStyle(t: Theme) {
  return {
    gap: t.space.md,
    padding: t.space.lg,
    borderRadius: t.radius.lg,
    backgroundColor: t.colors.surface,
    boxShadow: t.shadow.card,
  };
}

type Tab = 'ingredients' | 'method';

/**
 * "Add to list" and "Add 2 missing": onto the Shopping List (queued if offline), then
 * the same "Added to shopping list" toast as the Kitchen, with Undo.
 */
function useNeedActions(listId: string) {
  const toast = useToast();
  const { addItem, deleteItem } = useListActions(listId);
  const [added, setAdded] = useState<Set<number>>(new Set());
  function add(lines: { line: Line; i: number }[]) {
    const ids = lines.map(({ line }) => addItem(addText(line)));
    const which = lines.map(({ i }) => i);
    setAdded((before) => new Set([...before, ...which]));
    toast({
      kind: 'undo',
      text: 'Added to shopping list',
      detail: lines.length === 1 ? lineName(lines[0].line) : `${lines.length} ingredients`,
      onUndo: () => {
        ids.forEach(deleteItem);
        setAdded((before) => new Set([...before].filter((i) => !which.includes(i))));
      },
    });
  }
  return { added, add };
}

/** "25 min · Serves 4 · Main", each with its icon, as on the plan screens. */
function MetaRow({
  recipe,
}: {
  recipe: { total_minutes: number | null; servings: number; course: Course };
}) {
  const t = useTheme();
  const parts: { icon: LucideIcon; text: string }[] = [
    ...(recipe.total_minutes
      ? [{ icon: Clock, text: minutesText(recipe.total_minutes) ?? '' }]
      : []),
    { icon: Users, text: `Serves ${recipe.servings}` },
    { icon: ChefHat, text: courseName(recipe.course) },
  ];
  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', columnGap: t.space.lg, rowGap: 4 }}>
      {parts.map((p) => (
        <View key={p.text} style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
          <Icon icon={p.icon} size={17} color={t.colors.onBackground} />
          <Text variant="label" style={{ color: t.colors.onBackground }}>
            {p.text}
          </Text>
        </View>
      ))}
    </View>
  );
}

/** Opened from a plan's swap list: which day and dinner this would replace. */
function SwappingPill({ proposalId, date }: { proposalId: string; date: string }) {
  const t = useTheme();
  const replacing = useSwapTarget(proposalId, date);
  return (
    <View
      style={{
        alignSelf: 'flex-start',
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.xs,
        paddingHorizontal: t.space.md,
        paddingVertical: 6,
        borderRadius: t.radius.pill,
        backgroundColor: t.colors.surface,
        borderWidth: 1,
        borderColor: t.colors.border,
      }}
    >
      <Icon icon={ArrowLeftRight} size={16} color={t.colors.text} />
      <Text variant="caption">
        Swapping {formatDay(date)}
        {replacing ? ` · ${replacing}` : ''}
      </Text>
    </View>
  );
}

/** The plan this swap is for, read from the open Conversation's cached plan. */
function useSwapTarget(proposalId: string, date: string): string | null {
  const queryClient = useQueryClient();
  const found = queryClient
    .getQueriesData<{
      proposal: { id?: string | null; meals: { date: string; title: string }[] } | null;
    }>({
      queryKey: conversationKeys.all,
    })
    .map(([, data]) => data?.proposal)
    .find((p) => p?.id === proposalId);
  return found?.meals.find((m) => m.date === date)?.title ?? null;
}

/** "Swap to this meal": the swap answer to the waiting plan, then back to it. */
function SwapToThis({
  proposalId,
  date,
  recipeId,
}: {
  proposalId: string;
  date: string;
  recipeId: string;
}) {
  const decide = useDecideProposal(null);
  const queryClient = useQueryClient();
  return (
    <>
      <Button
        title="Swap to this meal"
        icon={ArrowLeftRight}
        loading={decide.isPending}
        onPress={() =>
          decide.mutate(
            { proposalId, decision: { action: 'swap', date, recipe_id: recipeId } },
            {
              onSuccess: async () => {
                await queryClient.invalidateQueries({ queryKey: conversationKeys.all });
                router.back();
              },
            },
          )
        }
      />
      <View accessibilityLiveRegion="polite">
        <ErrorText message={decide.error?.message} />
      </View>
    </>
  );
}

/** Opened from Dinner Ideas: plan this recipe for the day straight away (no Proposal). */
/** "Cook tonight" or "Another day" (a sheet of this week and next): planned directly. */
function PlanForDay({
  date,
  recipeId,
  title,
  servings,
}: {
  /** The day it was opened for (Dinner Ideas); null: tonight. */
  date: string | null;
  recipeId: string;
  title: string;
  servings: number | null;
}) {
  const t = useTheme();
  const planDay = usePlanDay();
  const today = useMealPlan(null).data?.today;
  const day = date ?? today;
  const [picking, setPicking] = useState(false);
  function plan(day: string) {
    planDay.mutate(planTap(day, recipeId, servings), {
      onSuccess: () => {
        setPicking(false);
        router.replace({
          pathname: '/planned',
          params: { kind: 'tonight', title, ...(day === today ? {} : { when: formatDay(day) }) },
        });
      },
    });
  }
  return (
    <View style={{ gap: 4 }}>
      <View style={{ flexDirection: 'row', gap: t.space.sm }}>
        <View style={{ flex: 1 }}>
          <Button
            title={!day || day === today ? 'Cook tonight' : `Plan for ${dayLabel(day)}`}
            disabled={!day}
            loading={planDay.isPending && !picking}
            onPress={() => day && plan(day)}
          />
        </View>
        <View style={{ flex: 1 }}>
          <Button
            title="Another day"
            icon={CalendarDays}
            variant="secondary"
            onPress={() => setPicking(true)}
          />
        </View>
      </View>
      <View accessibilityLiveRegion="polite">
        <ErrorText message={planDay.error?.message} />
      </View>
      {picking && today ? (
        <PickDaySheet
          today={today}
          busy={planDay.isPending}
          error={planDay.error?.message ?? null}
          onPick={plan}
          onClose={() => setPicking(false)}
        />
      ) : null}
    </View>
  );
}

/** "Adapted from Mum's ragu", a link back. Waits quietly if the parent is still loading. */
function AdaptedFrom({ parentId }: { parentId: string }) {
  const t = useTheme();
  const parent = useRecipe(parentId);
  const pathname = useRecipePath();
  if (!parent.data) return null;
  return (
    <Pressable
      accessibilityRole="link"
      onPress={() => router.push({ pathname, params: { id: parentId } })}
      style={{ minHeight: t.touchTarget, justifyContent: 'center' }}
    >
      <Text style={{ textDecorationLine: 'underline', color: t.colors.onBackground }}>
        Adapted from {parent.data.title}
      </Text>
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
  const pathname = useRecipePath();
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
              router.replace({ pathname, params: { id: parentId } });
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

/** "Chicken breast": the Ingredient's name, capitalised; the line as written if unlinked. */
function lineName(line: Line) {
  const name = line.ingredient?.name;
  return name ? name.charAt(0).toUpperCase() + name.slice(1) : line.raw_text;
}

/** "600 g", or the whole line when it has no amount we understood. */
function lineAmount(line: Line) {
  if (!line.ingredient) return null;
  if (line.quantity === null) return line.raw_text;
  return [line.quantity, line.unit].filter(Boolean).join(' ');
}

/**
 * One ingredient as a card: what it is, how much, and where it stands. "Add to list"
 * is the only one you can tap; the others just say how things are.
 */
function IngredientRow({
  line,
  have,
  onAdd,
}: {
  line: Line;
  have: Have | null;
  onAdd?: () => void;
}) {
  const t = useTheme();
  const name = line.ingredient?.name ?? line.raw_text;
  return (
    <View
      style={{
        minHeight: t.touchTarget + 16,
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.md,
        backgroundColor: t.colors.surface,
        borderRadius: t.radius.md,
        borderWidth: 1,
        borderColor: t.colors.border,
        paddingVertical: t.space.sm,
        paddingLeft: t.space.sm,
        paddingRight: t.space.sm,
      }}
    >
      <View
        accessible
        // The status is read from the pill beside it, a live region, so changes are announced.
        accessibilityLabel={[line.raw_text, line.optional ? 'optional' : null]
          .filter(Boolean)
          .join(', ')}
        style={{ flex: 1, flexDirection: 'row', alignItems: 'center', gap: t.space.md }}
      >
        <FoodThumb emoji={ingredientEmoji(line.ingredient)} tint={tintFor(name)} size={44} />
        <View style={{ flex: 1 }}>
          <Text variant="label">{lineName(line)}</Text>
          <Text variant="caption" muted>
            {[lineAmount(line), line.optional ? 'optional' : null].filter(Boolean).join(' · ')}
          </Text>
        </View>
      </View>
      <View accessibilityLiveRegion="polite">
        {have ? <StatusPill have={have} name={name} onAdd={onAdd} /> : null}
      </View>
    </View>
  );
}

/** In kitchen (lime), Add to list (red, tappable), On list (grey), or Low / Check. */
function StatusPill({ have, name, onAdd }: { have: Have; name: string; onAdd?: () => void }) {
  const t = useTheme();
  const look = {
    have: { icon: Package, text: 'In kitchen', bg: t.colors.actionSoft, fg: t.colors.onActionSoft },
    need: { icon: CirclePlus, text: 'Add to list', bg: t.colors.dangerSoft, fg: t.colors.danger },
    onList: { icon: ShoppingCart, text: 'On list', bg: t.colors.border, fg: t.colors.text },
    low: {
      icon: Package,
      text: have.kind === 'low' ? `Have ${have.have}` : '',
      bg: t.colors.border,
      fg: t.colors.text,
    },
    check: { icon: Package, text: 'Check', bg: t.colors.border, fg: t.colors.text },
  }[have.kind];
  const pill = (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.xs,
        backgroundColor: look.bg,
        borderRadius: t.radius.pill,
        paddingHorizontal: t.space.md,
        minHeight: 36,
      }}
    >
      <Icon icon={look.icon} color={look.fg} size={18} />
      <Text variant="label" style={{ color: look.fg }}>
        {look.text}
      </Text>
    </View>
  );
  if (have.kind !== 'need' || !onAdd) return pill;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Add ${name} to the shopping list`}
      onPress={onAdd}
      // A 44pt target around the 36pt pill.
      style={{ minHeight: t.touchTarget, justifyContent: 'center' }}
    >
      {pill}
    </Pressable>
  );
}

/** "Sun 22": no month, because only this week and next can be planned. */
function dayLabel(iso: string): string {
  const { weekday, day } = dayParts(iso);
  return `${weekday} ${day}`;
}

/** The recipe page on the Recipes purple, header bar included (from any tab). */
export default function RecipeScreen() {
  return (
    <PageColors page="recipes" header>
      <RecipeContent />
    </PageColors>
  );
}
