import { router, Stack } from 'expo-router';
import {
  ArrowLeftRight,
  Check,
  ChevronDown,
  ShoppingBasket,
  ShoppingCart,
  Sparkles,
} from 'lucide-react-native';
import { useEffect, useState, type Dispatch, type SetStateAction } from 'react';
import { ScrollView, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { RecipeArt, RecipeArtFor } from '@/components/RecipeArt';
import { Sheet } from '@/components/Sheet';
import { useToast } from '@/components/Toast';
import { Button, ErrorText, Field, SectionLabel, Text } from '@/components/ui';
import { amountOf, formatDay } from '@/features/chat/format';
import { decisionFor } from '@/features/chat/decision';
import { peekStart, takeStart } from '@/features/chat/starters';
import type { Proposal } from '@/features/chat/turn';
import { useQueries } from '@tanstack/react-query';

import { api, unwrap } from '@/lib/api/client';
import { useDecideProposal } from '@/lib/api/conversations';
import { useList, useListActions } from '@/lib/api/lists';
import { recipeKeys } from '@/lib/api/recipes';
import { useAlternatives } from '@/lib/api/planning';
import { sectionTints } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

import { GeneratingView } from './GeneratingView';
import { approveTicks, toAdd } from './quickAdd';
import { stepsFor, WEEK_STEPS } from './steps';
import { usePlanRun } from './usePlanRun';

const WEEKDAY = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const dayParts = (iso: string) => {
  const [y, m, d] = iso.split('-').map(Number);
  return { weekday: WEEKDAY[new Date(Date.UTC(y, m - 1, d)).getUTCDay()], day: d };
};
const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`;

/** "5 dinners, Mon – Fri, starting from what's in your Kitchen." */
function planLine(days: string[], mode: 'kitchen' | 'new') {
  const first = dayParts(days[0]).weekday;
  const last = dayParts(days[days.length - 1]).weekday;
  const span = days.length === 1 ? first : `${first} – ${last}`;
  const how =
    mode === 'kitchen' ? "starting from what's in your Kitchen" : 'with new recipes to shop for';
  return `${plural(days.length, 'dinner')}, ${span}, ${how}.`;
}

const REFINE_IDEAS = ['Make it quicker', 'More vegetarian', 'Use more of my Kitchen'];

/**
 * "Plan my week" as screens (slice 6e, ADR 0025): Generating, then the plan to review.
 * The same Conversation and Proposal as the chat underneath; the chat opens only when
 * Sweep answers without a plan.
 *
 * Review: swap any day for an alternative (code, instant), refine with Sweep (a chat
 * message, answered on this screen), add it to the week (approve), or start over (reject).
 */
export function WeekPlanScreen() {
  const t = useTheme();
  const run = usePlanRun();
  // Whether the sheet asked for a plan: known on the first render, taken in the effect.
  const [startPlan] = useState(() => peekStart()?.plan ?? null);
  const started = startPlan !== null;
  const [swapDay, setSwapDay] = useState<string | null>(null);
  const [refining, setRefining] = useState(false);
  // Things to buy already put on the list from here ("800 g canned tomatoes").
  const [listed, setListed] = useState<string[]>([]);
  const decide = useDecideProposal(run.conversationId);

  // The sheet's request, handed over once (a reload never re-sends a paid turn).
  useEffect(() => {
    const start = takeStart();
    if (start?.plan) void run.send(start.text, start.plan);
    // run.send is new every render; this runs once, on opening.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const proposal = run.proposal?.status === 'pending' ? run.proposal : null;

  function body() {
    if (started === false && !run.conversationId) {
      return (
        <View style={{ padding: t.space.lg, gap: t.space.md }}>
          <Text variant="title">Nothing is being planned</Text>
          <Text muted>Start from Home with Plan my week.</Text>
          <Button title="Back to Home" onPress={() => router.replace('/')} />
        </View>
      );
    }
    if (run.busy || (started && !run.turn)) {
      const refining = Boolean(proposal);
      return (
        <GeneratingView
          title={refining ? 'Updating your plan…' : 'Creating your meal plan…'}
          subtitle={
            refining
              ? 'Sweep is making your changes.'
              : startPlan
                ? planLine(startPlan.days, startPlan.mode)
                : 'Sweep is choosing dinners from your Kitchen and your Dietary Rules.'
          }
          steps={stepsFor(WEEK_STEPS, run.tools, Boolean(run.turn?.proposal))}
          onCancel={() => router.back()}
        />
      );
    }
    if (!proposal) {
      return (
        <View style={{ padding: t.space.lg, gap: t.space.md }}>
          {run.replyFor(null) ? <Note text={run.replyFor(null) ?? ''} /> : null}
          <ErrorText
            message={run.error ?? (run.replyFor(null) ? null : 'Sweep didn’t make a plan.')}
          />
          <Button title="Answer Sweep" onPress={() => setRefining(true)} />
          <Button
            title="Open the conversation"
            variant="secondary"
            onPress={() => router.push('/plan')}
          />
        </View>
      );
    }
    return (
      <Review
        proposal={proposal}
        note={run.replyFor(proposal.id) ?? proposal.summary}
        error={run.error ?? decide.error?.message ?? null}
        approving={decide.isPending}
        listed={listed}
        setListed={setListed}
        onSwap={setSwapDay}
        onRefine={() => setRefining(true)}
        onStartOver={() => {
          // Closes this plan without saving it; Home has Plan my week.
          if (proposal.id)
            decide.mutate({ proposalId: proposal.id, decision: { action: 'reject' } });
          router.dismissTo('/');
        }}
        onApprove={() => {
          const ticks = approveTicks(proposal, listed);
          const decision = decisionFor(proposal, ticks);
          const quickAdded = ticks.changedAdditions.length;
          if (!decision || !proposal.id) return;
          decide.mutate(
            { proposalId: proposal.id, decision },
            {
              onSuccess: (done) =>
                router.replace({
                  pathname: '/planned',
                  params: {
                    kind: 'week',
                    meals: String(done.outcome?.saved_meals ?? proposal.meals.length),
                    items: String(
                      (done.outcome?.added_items ?? proposal.list_additions.length - quickAdded) +
                        quickAdded,
                    ),
                  },
                }),
            },
          );
        }}
      />
    );
  }

  return (
    <SafeAreaView
      edges={['left', 'right', 'bottom']}
      style={{ flex: 1, backgroundColor: t.colors.background }}
    >
      <Stack.Screen
        options={{
          title: 'Your meal plan',
        }}
      />
      {body()}
      {swapDay && proposal ? (
        <SwapSheet
          proposal={proposal}
          date={swapDay}
          busy={decide.isPending}
          error={decide.error?.message ?? null}
          onClose={() => setSwapDay(null)}
          onSwap={(recipeId) => {
            if (!proposal.id) return;
            decide.mutate(
              {
                proposalId: proposal.id,
                decision: { action: 'swap', date: swapDay, recipe_id: recipeId },
              },
              { onSuccess: () => setSwapDay(null) },
            );
          }}
        />
      ) : null}
      {refining ? (
        <RefineSheet
          onClose={() => setRefining(false)}
          onSend={(text) => {
            setRefining(false);
            void run.send(text);
          }}
        />
      ) : null}
    </SafeAreaView>
  );
}

function Note({ text }: { text: string }) {
  const t = useTheme();
  return (
    <View
      accessibilityLiveRegion="polite"
      style={{
        flexDirection: 'row',
        gap: t.space.md,
        alignItems: 'flex-start',
        backgroundColor: t.colors.actionSoft,
        borderRadius: t.radius.lg,
        padding: t.space.lg,
      }}
    >
      <Icon icon={Sparkles} color={t.colors.onActionSoft} />
      <Text style={{ flex: 1, color: t.colors.onActionSoft }}>{text}</Text>
    </View>
  );
}

function Review({
  proposal,
  note,
  error,
  approving,
  listed,
  setListed,
  onSwap,
  onRefine,
  onStartOver,
  onApprove,
}: {
  proposal: Proposal;
  note: string;
  error: string | null;
  approving: boolean;
  listed: string[];
  setListed: Dispatch<SetStateAction<string[]>>;
  onSwap: (date: string) => void;
  onRefine: () => void;
  onStartOver: () => void;
  onApprove: () => void;
}) {
  const t = useTheme();
  const [showList, setShowList] = useState(false);
  const items = proposal.list_additions;
  const minutesOf = useMinutes(proposal.meals.map((m) => m.recipe_id));
  const onList = toAdd(proposal, listed).length === 0;
  const names = items.map((a) => a.name);
  const buySub = onList
    ? 'On your shopping list'
    : names.length > 3
      ? `${names.slice(0, 3).join(', ')} and ${names.length - 3} more`
      : names.join(', ');
  const first = proposal.meals[0]?.date;
  const last = proposal.meals[proposal.meals.length - 1]?.date;
  const card = {
    backgroundColor: t.colors.surface,
    borderRadius: t.radius.lg,
    boxShadow: t.shadow.card,
  } as const;
  return (
    <ScrollView
      contentContainerStyle={{
        padding: t.space.lg,
        gap: t.space.lg,
        width: '100%',
        maxWidth: 560,
        alignSelf: 'center',
      }}
    >
      <Text variant="title" role="heading" aria-level={1}>
        Here&apos;s your plan
      </Text>

      <View
        accessibilityLiveRegion="polite"
        style={{ ...card, padding: t.space.lg, gap: t.space.md }}
      >
        <AiBadge />
        <Text variant="heading">
          {plural(proposal.meals.length, 'dinner')} · {plural(items.length, 'thing')} to buy
        </Text>
        <Text
          style={{
            fontSize: 14,
            lineHeight: 20,
            paddingVertical: 10,
            paddingHorizontal: t.space.md,
            borderRadius: 10,
            backgroundColor: t.colors.background,
            overflow: 'hidden',
          }}
        >
          {note}
        </Text>
      </View>

      <View style={{ gap: t.space.sm }}>
        {first && last ? (
          <SectionLabel>
            {first === last ? formatDay(first) : `${shortDay(first)} – ${formatDay(last)}`}
          </SectionLabel>
        ) : null}
        <View style={{ ...card, overflow: 'hidden' }}>
          {proposal.meals.map((meal, i) => {
            const { weekday, day } = dayParts(meal.date);
            const meta = [
              minutesOf[meal.recipe_id] ? `${minutesOf[meal.recipe_id]} min` : null,
              `For ${meal.servings}`,
              meal.adaptation?.label,
              meal.replaces ? `replaces ${meal.replaces}` : null,
            ]
              .filter(Boolean)
              .join(' · ');
            return (
              <View
                key={meal.date}
                style={{
                  flexDirection: 'row',
                  alignItems: 'center',
                  gap: 10,
                  minHeight: 68,
                  paddingVertical: t.space.sm,
                  paddingLeft: t.space.sm,
                  paddingRight: 4,
                  borderTopWidth: i === 0 ? 0 : 1,
                  borderTopColor: t.colors.border,
                }}
              >
                <View style={{ width: 34, alignItems: 'center' }}>
                  <Text style={{ fontSize: 11, lineHeight: 14, color: t.colors.textMuted }}>
                    {weekday}
                  </Text>
                  <Text
                    style={{
                      fontSize: 17,
                      lineHeight: 22,
                      fontFamily: t.fonts.bold,
                      color: t.colors.text,
                    }}
                  >
                    {day}
                  </Text>
                </View>
                <RecipeArtFor
                  recipeId={meal.recipe_id}
                  adapted={!!meal.adaptation}
                  title={meal.title}
                  width={40}
                />
                <PressableScale
                  accessibilityRole="link"
                  accessibilityLabel={`${weekday} ${day}: ${meal.title}. ${meta}. See the recipe`}
                  onPress={() => router.push(`/recipe/${meal.recipe_id}`)}
                  style={{ flex: 1, gap: 2, minHeight: t.touchTarget, justifyContent: 'center' }}
                >
                  <Text variant="label" numberOfLines={2}>
                    {meal.title}
                  </Text>
                  <Text variant="caption" muted>
                    {meta}
                  </Text>
                </PressableScale>
                <PressableScale
                  accessibilityRole="button"
                  accessibilityLabel={`Swap ${meal.title} on ${weekday}`}
                  onPress={() => onSwap(meal.date)}
                  style={{
                    width: t.touchTarget,
                    height: t.touchTarget,
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Icon icon={ArrowLeftRight} size={20} color={t.colors.text} />
                </PressableScale>
              </View>
            );
          })}
        </View>
      </View>

      {items.length > 0 ? (
        <View style={{ ...card, overflow: 'hidden' }}>
          <PressableScale
            accessibilityRole="button"
            accessibilityState={{ expanded: showList }}
            accessibilityLabel={`${plural(items.length, 'thing')} to buy. ${buySub}`}
            onPress={() => setShowList((v) => !v)}
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              gap: t.space.sm,
              minHeight: 60,
              paddingHorizontal: 14,
            }}
          >
            <View
              style={{
                width: 32,
                height: 32,
                borderRadius: 10,
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: sectionTints.list.bg,
              }}
            >
              <Icon icon={ShoppingBasket} size={18} color={sectionTints.list.fg} />
            </View>
            <View style={{ flex: 1, gap: 2 }}>
              <Text variant="label">{plural(items.length, 'thing')} to buy</Text>
              <Text variant="caption" muted numberOfLines={1}>
                {buySub}
              </Text>
            </View>
            <View style={{ transform: [{ rotate: showList ? '180deg' : '0deg' }] }}>
              <Icon icon={ChevronDown} size={16} color={t.colors.textMuted} strong />
            </View>
          </PressableScale>
          {showList ? (
            <>
              {items.map((a, i) => (
                <View
                  key={i}
                  style={{
                    flexDirection: 'row',
                    alignItems: 'center',
                    gap: t.space.md,
                    minHeight: 48,
                    paddingHorizontal: 14,
                    borderTopWidth: 1,
                    borderTopColor: t.colors.border,
                  }}
                >
                  <Text style={{ flex: 1, fontFamily: t.fonts.medium }}>
                    {a.name}
                    {a.reason === 'unexplained' ? ' (not for any meal, left off)' : ''}
                  </Text>
                  {amountOf(a) ? (
                    <Text variant="caption" muted>
                      {amountOf(a)}
                    </Text>
                  ) : null}
                </View>
              ))}
              <View style={{ paddingHorizontal: 14, paddingTop: 4, paddingBottom: 14 }}>
                <AddToList proposal={proposal} listed={listed} setListed={setListed} />
              </View>
            </>
          ) : null}
        </View>
      ) : null}

      {proposal.dropped.length > 0 ? (
        <Text variant="caption" muted>
          Left out: {proposal.dropped.join('; ')}
        </Text>
      ) : null}
      <View accessibilityLiveRegion="polite">
        <ErrorText message={error} />
      </View>
      <View style={{ gap: 10 }}>
        <Button title="Refine with Sweep" icon={Sparkles} variant="secondary" onPress={onRefine} />
        <Button title="Add to my week" loading={approving} onPress={onApprove} />
        <Button title="Start a new plan" variant="outline" onPress={onStartOver} />
      </View>
    </ScrollView>
  );
}

/** Sweep's AI mark: a soft lime tag. */
function AiBadge() {
  const t = useTheme();
  return (
    <View
      style={{
        alignSelf: 'flex-start',
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        paddingVertical: 4,
        paddingLeft: 6,
        paddingRight: 8,
        borderRadius: 8,
        backgroundColor: t.colors.actionSoft,
      }}
    >
      <Icon icon={Sparkles} size={13} color={t.colors.onActionSoft} />
      <Text
        style={{
          fontFamily: t.fonts.bold,
          fontSize: 12,
          lineHeight: 16,
          color: t.colors.onActionSoft,
        }}
      >
        Suggested by Sweep
      </Text>
    </View>
  );
}

/** "Mon 24". */
function shortDay(iso: string) {
  const { weekday, day } = dayParts(iso);
  return `${weekday} ${day}`;
}

/** The plan's things to buy onto the Shopping List now, without approving the plan. */
function AddToList({
  proposal,
  listed,
  setListed,
}: {
  proposal: Proposal;
  listed: string[];
  setListed: Dispatch<SetStateAction<string[]>>;
}) {
  const toast = useToast();
  const list = useList();
  const { addItem, deleteItem } = useListActions(list.data?.id ?? '');
  const texts = toAdd(proposal, listed);
  const done = texts.length === 0;
  return (
    <Button
      title={done ? 'On your shopping list' : 'Add to shopping list now'}
      icon={done ? Check : ShoppingCart}
      accessibilityLabel={
        done ? 'On your shopping list' : `Add ${plural(texts.length, 'thing')} to shopping list`
      }
      variant="secondary"
      compact
      disabled={done || !list.data}
      onPress={() => {
        const ids = texts.map(addItem);
        setListed((before) => [...before, ...texts]);
        toast({
          kind: 'undo',
          text: 'Added to shopping list',
          detail: plural(texts.length, 'thing'),
          onUndo: () => {
            ids.forEach(deleteItem);
            setListed((before) => before.filter((text) => !texts.includes(text)));
          },
        });
      }}
    />
  );
}

/** Each planned recipe's time (cached recipe reads; the plan itself doesn't carry it). */
function useMinutes(ids: string[]): Record<string, number | null> {
  const found = useQueries({
    queries: ids.map((id) => ({
      queryKey: recipeKeys.one(id),
      queryFn: async () =>
        unwrap(await api.GET('/recipes/{recipe_id}', { params: { path: { recipe_id: id } } })),
      staleTime: 10 * 60_000,
    })),
  });
  return Object.fromEntries(ids.map((id, i) => [id, found[i]?.data?.total_minutes ?? null]));
}

function SwapSheet({
  proposal,
  date,
  busy,
  error,
  onClose,
  onSwap,
}: {
  proposal: Proposal;
  date: string;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onSwap: (recipeId: string) => void;
}) {
  const t = useTheme();
  const options = useAlternatives(proposal.id ?? null, date);
  const meal = proposal.meals.find((m) => m.date === date);
  const { weekday } = dayParts(date);
  return (
    <Sheet
      label={`Swap ${weekday}`}
      title={`Swap ${weekday}: ${meal?.title ?? ''}`}
      onClose={onClose}
    >
      <View style={{ gap: t.space.md }}>
        <Text variant="caption" muted>
          Other dinners that fit your Kitchen and Dietary Rules.
        </Text>
        <ErrorText message={options.error?.message ?? error} />
        {options.isPending ? <Text muted>Finding alternatives…</Text> : null}
        {options.data?.length === 0 ? <Text muted>No other dinners fit right now.</Text> : null}
        {options.data?.length ? (
          <View
            style={{
              backgroundColor: t.colors.surface,
              borderRadius: t.radius.lg,
              boxShadow: t.shadow.card,
              overflow: 'hidden',
            }}
          >
            {options.data.map((idea, i) => {
              const meta = [
                idea.total_minutes ? `${idea.total_minutes} min` : null,
                idea.missing.length ? `${idea.missing.length} to buy` : 'nothing to buy',
              ]
                .filter(Boolean)
                .join(' · ');
              return (
                <View
                  key={idea.id}
                  style={{
                    flexDirection: 'row',
                    alignItems: 'center',
                    gap: 10,
                    minHeight: 64,
                    paddingVertical: t.space.sm,
                    paddingLeft: 14,
                    paddingRight: t.space.sm,
                    borderTopWidth: i === 0 ? 0 : 1,
                    borderTopColor: t.colors.border,
                  }}
                >
                  <RecipeArt title={idea.title} image={idea.image} width={40} />
                  <PressableScale
                    accessibilityRole="link"
                    accessibilityLabel={`${idea.title}. ${meta}. See the recipe`}
                    onPress={() => {
                      onClose();
                      router.push({
                        pathname: '/recipe/[id]',
                        params: { id: idea.id, swap: proposal.id ?? '', date },
                      });
                    }}
                    style={{ flex: 1, gap: 2, minHeight: t.touchTarget, justifyContent: 'center' }}
                  >
                    <Text variant="label" numberOfLines={2}>
                      {idea.title}
                      {idea.favourite ? ' ♥' : ''}
                    </Text>
                    <Text variant="caption" muted>
                      {meta}
                    </Text>
                  </PressableScale>
                  <Button
                    title="Swap"
                    accessibilityLabel={`Swap to ${idea.title}`}
                    compact
                    tight
                    variant="secondary"
                    disabled={busy}
                    onPress={() => onSwap(idea.id)}
                  />
                </View>
              );
            })}
          </View>
        ) : null}
      </View>
    </Sheet>
  );
}

function RefineSheet({ onClose, onSend }: { onClose: () => void; onSend: (text: string) => void }) {
  const t = useTheme();
  const [text, setText] = useState('');
  return (
    <Sheet label="Refine with Sweep" title="Refine with Sweep" onClose={onClose}>
      <View style={{ gap: t.space.md }}>
        <Field
          label="What should Sweep change?"
          placeholder="Make Thursday vegetarian"
          value={text}
          onChangeText={setText}
          maxLength={2000}
          returnKeyType="send"
          onSubmitEditing={() => text.trim() && onSend(text)}
        />
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}>
          {REFINE_IDEAS.map((idea) => (
            <Button
              key={idea}
              title={idea}
              variant="secondary"
              compact
              onPress={() => onSend(idea)}
            />
          ))}
        </View>
        <Button title="Send to Sweep" disabled={!text.trim()} onPress={() => onSend(text)} />
      </View>
    </Sheet>
  );
}
