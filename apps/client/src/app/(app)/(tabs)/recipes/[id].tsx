import { useQueryClient } from '@tanstack/react-query';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import {
  ArrowLeft,
  ArrowLeftRight,
  CalendarDays,
  CirclePlay,
  Info,
  Plus,
} from 'lucide-react-native';
import { randomUUID } from 'expo-crypto';
import { Fragment, useState } from 'react';
import { Linking, Pressable, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ConfirmDialog } from '@/components/ConfirmDialog';
import { UnderlineTabs } from '@/components/UnderlineTabs';
import { HeartButton } from '@/components/HeartButton';
import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { useToast } from '@/components/Toast';
import { RecipeArt } from '@/components/RecipeArt';
import { ServesStepper } from '@/components/ServesStepper';
import { Button, ErrorText, Loading, Screen, SectionLabel, Text } from '@/components/ui';
import { formatDay } from '@/features/chat/format';
import { dayParts } from '@/features/mealPlan/week';
import { hostOf } from '@/features/imports/ReviewScreen';
import { ruleBreakHint, ruleBreakText } from '@/features/imports/ruleBreaks';
import { CookMode } from '@/features/recipes/CookMode';
import { MethodViewPicker } from '@/features/recipes/MethodViewPicker';
import { PhotoButton } from '@/features/recipes/OwnPhoto';
import {
  addText,
  haveSummary,
  matchLine,
  minutesText,
  type Have,
} from '@/features/recipes/kitchenMatch';
import { swapLine, swapsOf } from '@/features/recipes/adaptations';
import { cookSteps, metaParts, viewsOf, type MethodView } from '@/features/recipes/method';
import { groupHeading, lineCaption, lineName } from '@/features/recipes/lines';
import { leftOutText, needsSeeMore, nutritionRows } from '@/features/recipes/nutrition';
import { scaleLine } from '@/features/recipes/scale';
import { useMethodView } from '@/features/recipes/methodView';
import { PickDaySheet } from '@/features/mealPlan/PickDaySheet';
import { RecipeRow } from '@/features/recipes/RecipeRow';
import { useRecipePath } from '@/features/recipes/recipePath';
import { conversationKeys, useDecideProposal } from '@/lib/api/conversations';
import { photoTap, useImportedRecipeActions, useImportedRecipes } from '@/lib/api/imports';
import type { PickedFile } from '@/lib/api/upload';
import { useKitchen } from '@/lib/api/kitchen';
import { useList, useListActions } from '@/lib/api/lists';
import { usePreferences } from '@/lib/api/diet';
import { useMealPlan, useMealServings } from '@/lib/api/mealPlan';
import { planTap, usePlanDay } from '@/lib/api/planning';
import { isNotFound, useAdaptations, useDeleteAdaptation, useRecipe } from '@/lib/api/recipes';
import type { components } from '@/lib/api/schema';
import { PageColors } from '@/theme/PageColors';
import { useTheme, type Theme } from '@/theme/useTheme';

type Line = components['schemas']['RecipeIngredientOut'];
type Recipe = components['schemas']['RecipeOut'];
type RecipeImage = components['schemas']['RecipeImageOut'];

/**
 * One recipe, checked against the Kitchen: each ingredient says whether you have it.
 * That's the loop working: what you bought (Kitchen) meets what you could cook.
 *
 * Something you need shows "Add to list": one tap puts it on the Shopping List. Anything
 * already unticked on the list shows "On list", the same rule the planner uses.
 *
 * The summary sits under the title, then Ingredients | Method | Nutrition tabs (slice 4h). Method shows the Detailed View (Recipe Stages) or the Quick
 * View, remembered on the device, and opens Cook Mode (ADR 0028). Tips, variations,
 * storage and Notes sit at the bottom of Method: a Recipe Adaptation's (ADR 0021) Swaps,
 * a parent's Adaptations, and where the recipe came from. Nutrition is per serve (ADR 0035).
 */
function RecipeContent() {
  const t = useTheme();
  // `plan`: opened from Dinner Ideas to plan it for that day (slice 6e).
  // `swap` + `date`: opened from a plan's swap list to swap that day to this (ADR 0025).
  // `serves`: the Dinner ideas setup's Serves, for the Planned Meal (slice 6f).
  // `meal`: opened from a Planned Meal; changing Serves saves to it (`cooked`: it can't).
  const { id, plan, swap, date, serves, meal, cooked } = useLocalSearchParams<{
    id: string;
    plan?: string;
    swap?: string;
    date?: string;
    serves?: string;
    meal?: string;
    cooked?: string;
  }>();
  const recipe = useRecipe(id);
  // The Kitchen is optional here: if it fails to load, the recipe still shows.
  const kitchen = useKitchen();
  // Optional too: without the list, "Need" is just a label, with no + to add it.
  const list = useList();
  const [tab, setTab] = useState<Tab>('ingredients');
  const [remembered, setView] = useMethodView();
  const [cooking, setCooking] = useState(false);
  const need = useNeedActions(list.data?.id ?? '');
  const household = usePreferences().data?.household_size ?? null;
  const [chosenServes, setServes] = useState<number | null>(null);
  const saveServes = useMealServings();

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
  const views = viewsOf(r);
  const view: MethodView = views.includes(remembered) ? remembered : views[0];
  // Detailed: one card per Recipe Stage. Quick: one per step.
  const cards: Card[] =
    view === 'detailed' && r.stages?.length
      ? r.stages.map((st) => ({ title: st.title, minutes: st.minutes, body: st.steps }))
      : (r.method ?? []).map((step) => ({ body: [step] }));
  const steps = cookSteps(r, view);
  // Serves: the plan's, else the Household's size, else the recipe's own.
  const servesNow =
    chosenServes ?? (Number(serves) > 0 ? Number(serves) : (household ?? r.servings));
  const lines = r.ingredients.map((line) => scaleLine(line, servesNow / r.servings));
  const changeServes = (n: number) => {
    setServes(n);
    if (meal) saveServes.mutate({ mealId: meal, servings: n, idempotencyKey: randomUUID() });
  };
  const summary = kitchen.data ? haveSummary(lines, kitchen.data) : null;
  const parentId = r.kind === 'adaptation' ? r.parent_recipe_id : null;
  const swaps = swapsOf(r.ingredients);
  const statusOf = (line: Line, i: number): Have | null => {
    const match = kitchen.data ? matchLine(line, kitchen.data, list.data?.items) : null;
    // Just tapped: the list hasn't come back with it linked yet, but it's on there.
    return match?.kind === 'need' && need.added.has(i) ? { kind: 'onList' } : match;
  };
  const missing = list.data
    ? lines
        .map((line, i) => ({ line, i }))
        .filter(({ line, i }) => statusOf(line, i)?.kind === 'need')
    : [];

  // From a Planned Meal it's already on the plan: Serves is the only thing to change.
  const actions = meal ? null : plan ? (
    <PlanForDay date={plan} recipeId={r.id} title={r.title} servings={servesNow} />
  ) : swap && date ? (
    <SwapToThis proposalId={swap} date={date} recipeId={r.id} />
  ) : r.course === 'main' ? (
    // Any main can be tonight's dinner, however you found it.
    <PlanForDay date={null} recipeId={r.id} title={r.title} servings={servesNow} />
  ) : null;

  return (
    <Screen
      edges={['left', 'right', 'bottom']}
      hero={
        <RecipePhoto
          title={r.title}
          image={r.image}
          ownRecipeId={r.kind === 'imported' ? r.id : null}
          heart={
            r.kind === 'adaptation' ? null : (
              <HeartButton recipeId={r.id} title={r.title} favourite={r.favourite ?? false} />
            )
          }
        />
      }
    >
      <View style={{ gap: 6 }}>
        <Text variant="title" accessibilityRole="header">
          {r.title}
        </Text>
        <MetaRow recipe={{ ...r, servings: servesNow }} />
      </View>
      {r.summary ? <Summary text={r.summary} /> : null}
      {swap && date ? <SwappingPill proposalId={swap} date={date} /> : null}
      {parentId ? <AdaptedFrom parentId={parentId} /> : null}

      {summary ? (
        <View
          accessibilityLiveRegion="polite"
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            gap: t.space.sm,
            paddingVertical: missing.length > 0 ? 4 : 10,
            paddingLeft: t.space.md,
            paddingRight: 4,
            borderRadius: 10,
            borderWidth: 1,
            borderColor: t.colors.border,
            backgroundColor: t.colors.fill,
          }}
        >
          <Text style={{ flex: 1, fontSize: 14, lineHeight: 20 }}>
            {summary.have === summary.total
              ? 'You have everything for this.'
              : `You have ${summary.have} of ${summary.total} ingredients.`}
          </Text>
          {missing.length > 0 ? (
            <Button
              title={`Add ${missing.length} to list`}
              accessibilityLabel={`Add ${missing.length} missing ingredients to the shopping list`}
              variant="secondary"
              compact
              tight
              onPress={() => need.add(missing)}
            />
          ) : null}
        </View>
      ) : null}
      {actions}

      <UnderlineTabs label="Recipe" value={tab} onChange={setTab} options={TABS} />

      {tab === 'ingredients' ? (
        <View style={{ gap: t.space.sm }}>
          <ServesRow
            value={servesNow}
            recipeServes={r.servings}
            cooked={!!meal && cooked === '1'}
            saved={saveServes.isSuccess}
            error={saveServes.error?.message}
            onChange={changeServes}
          />
          <View
            style={{
              backgroundColor: t.colors.surface,
              borderRadius: t.radius.lg,
              boxShadow: t.shadow.card,
              overflow: 'hidden',
            }}
          >
            {lines.map((line, i) => {
              const heading = groupHeading(lines, i, (l) => l.group_name ?? null);
              return (
                <Fragment key={i}>
                  {heading ? <GroupHeading name={heading} first={i === 0} /> : null}
                  <IngredientRow
                    first={i === 0 || heading !== null}
                    line={line}
                    have={statusOf(line, i)}
                    onAdd={list.data ? () => need.add([{ line, i }]) : undefined}
                  />
                </Fragment>
              );
            })}
          </View>
          {kitchen.isError ? (
            <Text variant="caption" muted>
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
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.md }}>
            {views.length > 1 ? (
              <View style={{ flex: 1, flexDirection: 'row' }}>
                <MethodViewPicker value={view} onChange={setView} />
              </View>
            ) : null}
            {steps.length > 0 ? (
              <PressableScale
                accessibilityRole="button"
                accessibilityLabel={`Cook Mode: ${r.title}, one step at a time`}
                onPress={() => setCooking(true)}
                style={{
                  // No Quick / Detailed menu (an added recipe): the button takes the row
                  flex: views.length > 1 ? undefined : 1,
                  flexDirection: 'row',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: t.space.sm,
                  minHeight: t.touchTarget,
                  paddingHorizontal: t.space.lg,
                  borderRadius: t.radius.pill,
                  borderWidth: 1,
                  borderColor: t.colors.border,
                  backgroundColor: t.colors.action,
                }}
              >
                <Icon icon={CirclePlay} size={18} color={t.colors.onAction} />
                <Text style={[t.type.label, { color: t.colors.onAction }]}>Cook Mode</Text>
              </PressableScale>
            ) : null}
          </View>
          {cards.length > 0 ? (
            cards.map((card, i) => (
              <MethodCard key={i} n={i + 1} total={cards.length} card={card} />
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
      {tab === 'method' ? <Extras recipe={r} /> : null}
      {tab === 'nutrition' ? <NutritionPanel nutrition={r.nutrition} /> : null}
      {cooking ? (
        <CookMode title={r.title} steps={steps} onClose={() => setCooking(false)} />
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

type Tab = 'ingredients' | 'method' | 'nutrition';

const TABS: { value: Tab; label: string }[] = [
  { value: 'ingredients', label: 'Ingredients' },
  { value: 'method', label: 'Method' },
  { value: 'nutrition', label: 'Nutrition' },
];

/** The recipe's description, folded to three lines when it's long. */
function Summary({ text }: { text: string }) {
  const t = useTheme();
  const long = needsSeeMore(text);
  const [open, setOpen] = useState(false);
  return (
    <View style={{ gap: 2 }}>
      <Text numberOfLines={long && !open ? 3 : undefined}>{text}</Text>
      {long ? (
        <Pressable
          accessibilityRole="button"
          accessibilityState={{ expanded: open }}
          onPress={() => setOpen((o) => !o)}
          hitSlop={8}
          style={{ alignSelf: 'flex-start', minHeight: 24, justifyContent: 'center' }}
        >
          <Text style={{ fontFamily: t.fonts.bold, textDecorationLine: 'underline' }}>
            {open ? 'See less' : 'See more'}
          </Text>
        </Pressable>
      ) : null}
    </View>
  );
}

/**
 * Nutrition per serve, like an Australian label: kJ (Cal) and % Daily Intake. What we
 * couldn't count is named; when the missing part is too big, no numbers at all (ADR 0035).
 */
function NutritionPanel({ nutrition }: { nutrition: Recipe['nutrition'] }) {
  const t = useTheme();
  const leftOut = leftOutText(nutrition.left_out);
  if (!nutrition.available || !nutrition.per_serve) {
    return (
      <View style={cardStyle(t)}>
        <Text variant="heading" role="heading" aria-level={2}>
          Nutrition isn&apos;t available
        </Text>
        <Text muted>
          {nutrition.left_out.length
            ? `We don't have nutrition data for ${nutrition.left_out.join(', ')} yet, and it's too big a part of this recipe to leave out.`
            : "We couldn't work out this recipe's nutrition from its ingredients."}
        </Text>
      </View>
    );
  }
  const rows = nutritionRows(nutrition.per_serve);
  const head = { fontSize: 13, fontFamily: t.fonts.bold, color: t.colors.textMuted };
  return (
    <View style={{ gap: t.space.sm }}>
      <View style={[cardStyle(t), { gap: 0 }]}>
        <Text variant="heading" role="heading" aria-level={2}>
          Nutrition per serve
        </Text>
        <View
          aria-hidden
          style={{ flexDirection: 'row', paddingTop: t.space.md, paddingBottom: t.space.xs }}
        >
          <Text style={[head, { flex: 1 }]}> </Text>
          <Text style={[head, { textAlign: 'right' }]}>Per serve</Text>
          <Text style={[head, { width: 64, textAlign: 'right' }]}>% DI*</Text>
        </View>
        {rows.map((row) => (
          <View
            key={row.label}
            accessible
            accessibilityLabel={`${row.label}${row.sub ? ' (of which)' : ''}, ${row.spoken}, ${row.percent}% of daily intake`}
            style={{
              flexDirection: 'row',
              alignItems: 'baseline',
              minHeight: 40,
              paddingVertical: t.space.sm,
              borderTopWidth: 1,
              borderTopColor: t.colors.border,
            }}
          >
            <Text
              style={{
                flex: 1,
                paddingLeft: row.sub ? t.space.lg : 0,
                fontFamily: row.sub ? t.fonts.body : t.fonts.medium,
                color: row.sub ? t.colors.textMuted : t.colors.text,
              }}
            >
              {row.label}
            </Text>
            <Text style={{ textAlign: 'right', fontVariant: ['tabular-nums'] }}>{row.amount}</Text>
            <Text
              style={{
                width: 64,
                textAlign: 'right',
                fontVariant: ['tabular-nums'],
                color: t.colors.textMuted,
              }}
            >
              {row.percent}%
            </Text>
          </View>
        ))}
      </View>
      {leftOut ? <Text variant="caption">{leftOut}</Text> : null}
      <Text variant="caption" muted>
        An estimate from the ingredients, so cooking and brands can change it. *Percentage Daily
        Intake is based on an average adult diet of 8,700 kJ. Nutrition data: FSANZ.
      </Text>
    </View>
  );
}

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

/** Serves, above the ingredients. On a Planned Meal it saves; a Cooked one keeps its number. */
function ServesRow({
  value,
  recipeServes,
  cooked,
  saved,
  error,
  onChange,
}: {
  value: number;
  recipeServes: number;
  cooked: boolean;
  saved: boolean;
  error?: string;
  onChange: (serves: number) => void;
}) {
  const t = useTheme();
  const hint = cooked
    ? `Cooked, so this meal keeps ${value} serves.`
    : value !== recipeServes
      ? `Amounts changed from the recipe's ${recipeServes} serves${saved ? '. Saved to your plan' : ''}.`
      : null;
  return (
    <View style={{ gap: 4 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Text variant="label" aria-hidden>
          Serves
        </Text>
        <ServesStepper value={value} onChange={onChange} disabled={cooked} />
      </View>
      <View accessibilityLiveRegion="polite">
        {hint ? (
          <Text variant="caption" style={{ color: t.colors.onBackgroundMuted }}>
            {hint}
          </Text>
        ) : null}
        <ErrorText message={error} />
      </View>
    </View>
  );
}

/** "Prep 20 min · Cook 1 h · Easy · Serves 4 · Main"; just the total when that's all we know. */
function MetaRow({ recipe }: { recipe: Recipe }) {
  return (
    <Text variant="caption" muted style={{ fontVariant: ['tabular-nums'] }}>
      {metaParts(recipe).join('  ·  ')}
    </Text>
  );
}

/** One numbered step: a white card with the number in a navy circle. */
type Card = { title?: string; minutes?: number | null; body: string[] };

/** "STEP 1 OF 6", a stage's title and minutes when it has them, then what to do. */
function MethodCard({ n, total, card }: { n: number; total: number; card: Card }) {
  const t = useTheme();
  return (
    <View style={[cardStyle(t), { padding: t.space.lg, gap: t.space.sm }]}>
      <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: t.space.sm }}>
        <Text
          variant="caption"
          muted
          style={{ flex: 1, textTransform: 'uppercase', letterSpacing: 0.6 }}
        >
          Step {n} of {total}
        </Text>
        {card.minutes ? (
          <Text variant="caption" muted style={{ fontVariant: ['tabular-nums'] }}>
            {minutesText(card.minutes)}
          </Text>
        ) : null}
      </View>
      {card.title ? (
        <Text variant="heading" role="heading" aria-level={3}>
          {card.title}
        </Text>
      ) : null}
      {card.body.map((line, i) => (
        <Text key={i} muted={!!card.title}>
          {line}
        </Text>
      ))}
    </View>
  );
}

/** Tips, variations and storage, at the bottom of Method. Each only when the recipe has it. */
function Extras({ recipe }: { recipe: Recipe }) {
  const t = useTheme();
  const lists = [
    { title: 'Tips', items: recipe.tips ?? [] },
    { title: 'Variations', items: recipe.variations ?? [] },
  ].filter((l) => l.items.length > 0);
  if (lists.length === 0 && !recipe.storage) return null;
  return (
    <View style={[cardStyle(t), { gap: t.space.lg }]}>
      {lists.map((l) => (
        <View key={l.title} style={{ gap: t.space.sm }}>
          <SectionLabel>{l.title}</SectionLabel>
          {l.items.map((item, i) => (
            <View key={i} style={{ flexDirection: 'row', gap: t.space.sm }}>
              <Text aria-hidden>•</Text>
              <Text style={{ flex: 1 }}>{item}</Text>
            </View>
          ))}
        </View>
      ))}
      {recipe.storage ? (
        <View style={{ gap: t.space.sm }}>
          <SectionLabel>Storage</SectionLabel>
          <Text>{recipe.storage}</Text>
        </View>
      ) : null}
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

/** An Ingredient Group's name ("Marinade slather") above its lines, inside the card. */
function GroupHeading({ name, first }: { name: string; first: boolean }) {
  const t = useTheme();
  return (
    <Text
      accessibilityRole="header"
      style={{
        fontFamily: t.fonts.bold,
        fontSize: 13,
        paddingHorizontal: 14,
        paddingTop: t.space.md,
        paddingBottom: t.space.xs,
        borderTopWidth: first ? 0 : 1,
        borderTopColor: t.colors.border,
      }}
    >
      {name}
    </Text>
  );
}

/**
 * One ingredient as a card: what it is, how much, and where it stands. "Add to list"
 * is the only one you can tap; the others just say how things are.
 */
function IngredientRow({
  line,
  first,
  have,
  onAdd,
}: {
  line: Line;
  first: boolean;
  have: Have | null;
  onAdd?: () => void;
}) {
  const t = useTheme();
  const name = line.ingredient?.name ?? line.raw_text;
  return (
    <View
      style={{
        minHeight: 56,
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.md,
        paddingVertical: t.space.sm,
        paddingLeft: 14,
        paddingRight: 6,
        borderTopWidth: first ? 0 : 1,
        borderTopColor: t.colors.border,
      }}
    >
      <View
        accessible
        // The status is read from the mark beside it, a live region, so changes are announced.
        accessibilityLabel={[line.raw_text, line.optional ? 'optional' : null]
          .filter(Boolean)
          .join(', ')}
        style={{ flex: 1, gap: 2 }}
      >
        <Text style={{ fontFamily: t.fonts.medium }}>{lineName(line)}</Text>
        <Text variant="caption" muted style={{ fontVariant: ['tabular-nums'] }}>
          {lineCaption(line)}
        </Text>
      </View>
      <View accessibilityLiveRegion="polite">
        {have ? <StatusMark have={have} name={name} onAdd={onAdd} /> : null}
      </View>
    </View>
  );
}

/** In kitchen (green tick), On list, Have / Check (muted), or an Add button when needed. */
function StatusMark({ have, name, onAdd }: { have: Have; name: string; onAdd?: () => void }) {
  const t = useTheme();
  if (have.kind === 'need') {
    if (!onAdd) {
      return (
        <Text variant="caption" style={{ color: t.colors.danger, paddingRight: 8 }}>
          Need
        </Text>
      );
    }
    return (
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`Add ${name} to the shopping list`}
        onPress={onAdd}
        style={({ pressed }) => ({
          flexDirection: 'row',
          alignItems: 'center',
          gap: 4,
          minHeight: t.touchTarget,
          paddingHorizontal: t.space.sm,
          borderRadius: t.radius.md,
          borderWidth: 1,
          borderColor: t.colors.border,
          backgroundColor: pressed ? t.colors.fill : t.colors.surface,
        })}
      >
        <Icon icon={Plus} size={14} color={t.colors.text} />
        <Text variant="label" style={{ fontSize: 13 }}>
          Add to list
        </Text>
      </Pressable>
    );
  }
  const mark = {
    have: { text: '✓ In kitchen', fg: t.stock.in_stock.fg },
    onList: { text: 'On list', fg: t.colors.textMuted },
    low: { text: have.kind === 'low' ? `Have ${have.have}` : '', fg: t.colors.textMuted },
    check: { text: 'Check', fg: t.colors.textMuted },
  }[have.kind];
  return (
    <Text style={{ fontFamily: t.fonts.medium, fontSize: 13, color: mark.fg, paddingRight: 8 }}>
      {mark.text}
    </Text>
  );
}

/**
 * The full-width picture at the top, under the status bar, with round Back and heart
 * buttons floating on it (the stack's header bar is hidden on this screen).
 */
function RecipePhoto({
  title,
  image,
  ownRecipeId,
  heart,
}: {
  title: string;
  image?: RecipeImage | null;
  /** A Member's own recipe: they can add, change or remove its photo (ADR 0031). */
  ownRecipeId: string | null;
  heart: React.ReactNode;
}) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const toast = useToast();
  const { photo } = useImportedRecipeActions();
  const change = (file: PickedFile | null) => {
    if (!ownRecipeId) return;
    photo.mutate(photoTap(ownRecipeId, file), {
      onError: (error) => toast({ tag: 'Recipes', text: error.message }),
    });
  };
  const float = {
    position: 'absolute' as const,
    top: insets.top + t.space.sm,
  };
  return (
    <View>
      <Stack.Screen options={{ headerShown: false }} />
      <RecipeArt
        title={title}
        image={image}
        hero
        width="100%"
        height={260 + insets.top}
        radius={0}
        iconSize={64}
      />
      {image?.author ? <PhotoCredit image={image} /> : null}
      <PressableScale
        accessibilityRole="button"
        accessibilityLabel="Back"
        onPress={() => (router.canGoBack() ? router.back() : router.replace('/recipes'))}
        style={{
          ...float,
          left: Math.max(insets.left, t.space.lg),
          width: t.touchTarget,
          height: t.touchTarget,
          borderRadius: t.touchTarget / 2,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'rgba(255, 255, 255, 0.92)',
        }}
      >
        <Icon icon={ArrowLeft} color={t.colors.text} strong />
      </PressableScale>
      {heart ? (
        <View style={{ ...float, right: Math.max(insets.right, t.space.lg) }}>{heart}</View>
      ) : null}
      {/* After Back and the heart, so a screen reader meets them first. */}
      {ownRecipeId ? (
        <PhotoButton
          hasPhoto={!!image}
          busy={photo.isPending}
          onPicked={change}
          onRemove={() => change(null)}
          style={{ position: 'absolute', left: t.space.lg, bottom: t.space.md }}
        />
      ) : null}
    </View>
  );
}

/**
 * A tiny "i" on a stock photo; tapped, it shows the photographer's name, linked to their
 * Unsplash profile (ADR 0029). The icon is 12px, its tap area the 24px WCAG minimum.
 */
function PhotoCredit({ image }: { image: RecipeImage }) {
  const t = useTheme();
  const [open, setOpen] = useState(false);
  const { author, author_url: authorUrl } = image;
  if (!author || !authorUrl) return null;
  return (
    <View
      style={{
        position: 'absolute',
        right: 4,
        bottom: 4,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 2,
      }}
    >
      {open ? (
        <Text
          accessibilityRole="link"
          accessibilityLabel={`Photo by ${author}`}
          onPress={() => Linking.openURL(authorUrl)}
          numberOfLines={1}
          style={{
            maxWidth: 220,
            paddingHorizontal: 6,
            paddingVertical: 2,
            borderRadius: t.radius.sm,
            overflow: 'hidden',
            backgroundColor: 'rgba(0, 0, 0, 0.45)',
            color: '#fff',
            fontSize: 11,
          }}
        >
          {author}
        </Text>
      ) : null}
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={open ? 'Hide photo credit' : 'Photo credit'}
        onPress={() => setOpen((o) => !o)}
        style={{ width: 24, height: 24, alignItems: 'center', justifyContent: 'center' }}
      >
        <View
          style={{
            width: 14,
            height: 14,
            borderRadius: 7,
            backgroundColor: 'rgba(0, 0, 0, 0.35)',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Icon icon={Info} size={12} color="#fff" />
        </View>
      </Pressable>
    </View>
  );
}

/** "Sun 22": no month, because only this week and next can be planned. */
function dayLabel(iso: string): string {
  const { weekday, day } = dayParts(iso);
  return `${weekday} ${day}`;
}

/** The recipe page (from any tab): its own photo header, no stack header bar. */
export default function RecipeScreen() {
  return (
    <PageColors page="recipes">
      <RecipeContent />
    </PageColors>
  );
}
