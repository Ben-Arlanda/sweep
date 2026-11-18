import { router } from 'expo-router';
import { useState } from 'react';
import { CalendarDays, ChefHat, Settings } from 'lucide-react-native';
import { Pressable, View } from 'react-native';

import { AvatarStack } from '@/components/Avatar';
import { Hero, HeroLabel } from '@/components/Hero';
import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { RecipeArt } from '@/components/RecipeArt';
import { Button, ErrorText, Highlight, Text } from '@/components/ui';
import { requestPlan } from '@/features/chat/starters';
import { formatDay } from '@/features/chat/format';
import { PlanSheet } from '@/features/mealPlan/PlanSheet';
import { addDays, mondayOf, type PlannedMeal } from '@/features/mealPlan/week';
import type { MeOut } from '@/lib/api/client';
import { useHousehold } from '@/lib/api/households';
import { mealTap, useMealPlan, useMealPlanActions } from '@/lib/api/mealPlan';
import { useTheme } from '@/theme/useTheme';

import { AskSweep } from './AskSweep';
import { homeState, needsNextWeek, usesLine, type HomeState } from './today';

/**
 * Home's hero (slice 6c): tonight's dinner when one is planned, otherwise the question
 * "What's cooking tonight?". Four states, worked out by `homeState`:
 *
 * - planned: the dinner, See the recipe and Cooked (no photo: dropped as too complex);
 * - cooked: "Cooked ✓" with Undo (no timer, WCAG 2.2.1), then tomorrow;
 * - free / empty: the question, the Ask Sweep box, Plan my week and Just tonight.
 */
export function TodayHero({ me }: { me: MeOut }) {
  const t = useTheme();
  const week = useMealPlan(null);
  const today = week.data?.today;
  const next = useMealPlan(
    today ? addDays(mondayOf(today), 7) : null,
    today !== undefined && needsNextWeek(today),
  );
  const [planning, setPlanning] = useState(false);

  // Until the week loads, the question (without a sentence that might be wrong).
  const state: HomeState | null = week.data
    ? homeState({ today: week.data.today, thisWeek: week.data.meals, nextWeek: next.data?.meals })
    : null;

  const sheet = planning ? (
    <PlanSheet
      onClose={() => setPlanning(false)}
      onPick={(mode, days, tweaks) => {
        requestPlan(mode, days, tweaks);
        router.push('/plan-week');
      }}
    />
  ) : null;

  if (state?.kind === 'planned' || state?.kind === 'cooked') {
    return (
      <DinnerHero me={me} state={state} onPlan={() => setPlanning(true)}>
        {sheet}
      </DinnerHero>
    );
  }
  return (
    <Hero
      top={<HouseholdRow me={me} />}
      title={
        <>
          What&apos;s <Highlight>cooking</Highlight> tonight?
        </>
      }
      subtitle={
        state?.kind === 'free'
          ? 'Nothing planned for tonight. Sweep can find something from your Kitchen, or plan the rest of the week.'
          : state?.kind === 'empty'
            ? "Nothing planned yet. Sweep can plan the week around your rules and what's in your Kitchen."
            : undefined
      }
    >
      <AskSweep />
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}>
        <View style={{ flexGrow: 1, flexBasis: 150 }}>
          <Button title="Plan my week" icon={CalendarDays} onPress={() => setPlanning(true)} />
        </View>
        <View style={{ flexGrow: 1, flexBasis: 150 }}>
          <Button
            title="Just tonight"
            icon={ChefHat}
            variant="secondary"
            onPress={() => router.push('/tonight')}
          />
        </View>
      </View>
      <ErrorText message={week.error?.message} />
      {sheet}
    </Hero>
  );
}

function HouseholdRow({ me }: { me: MeOut }) {
  const t = useTheme();
  const household = useHousehold(true);
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.md }}>
      <AvatarStack members={household.data?.members ?? [me.member]} size={40} />
      <View style={{ flex: 1 }}>
        <HeroLabel label="Household" value={me.household.name} />
      </View>
      <PressableScale
        accessibilityRole="link"
        accessibilityLabel="Household settings"
        onPress={() => router.push('/household')}
        style={{
          width: t.touchTarget,
          height: t.touchTarget,
          borderRadius: t.radius.pill,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: t.colors.heroField,
        }}
      >
        <Icon icon={Settings} color={t.colors.onHero} />
      </PressableScale>
    </View>
  );
}

function DinnerHero({
  me,
  state,
  onPlan,
  children,
}: {
  me: MeOut;
  state: Extract<HomeState, { kind: 'planned' | 'cooked' }>;
  onPlan: () => void;
  children?: React.ReactNode;
}) {
  const t = useTheme();
  const meal = state.tonight;
  const isCooked = state.kind === 'cooked';
  const { cooked, undoCooked } = useMealPlanActions();
  const busy = cooked.isPending || undoCooked.isPending;
  const error = cooked.error ?? undoCooked.error;
  // Lime on the dark hero; on the light (lime-soft) hero lime wouldn't be readable.
  const eyebrow = t.scheme === 'dark' ? t.colors.action : t.colors.onHero;

  return (
    <Hero
      top={
        <>
          <HouseholdRow me={me} />
          <Text
            variant="label"
            accessibilityLiveRegion="polite"
            style={{ color: eyebrow, textTransform: 'uppercase', letterSpacing: 0.8 }}
          >
            {isCooked ? 'Tonight · Cooked ✓' : `Tonight · ${formatDay(meal.date)}`}
          </Text>
        </>
      }
      title={meal.title}
      subtitle={usesLine(meal)}
      aside={<RecipeArt title={meal.title} width={84} />}
    >
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}>
        <Button
          title="See the recipe"
          variant={isCooked ? 'secondary' : 'primary'}
          compact
          onPress={() => router.push(`/recipe/${meal.recipe_id}`)}
        />
        {isCooked ? (
          <Button
            title="Undo"
            accessibilityLabel={`Undo cooked for ${meal.title}`}
            variant="ghost"
            compact
            loading={undoCooked.isPending}
            disabled={busy}
            onPress={() => undoCooked.mutate(mealTap(meal.id))}
          />
        ) : (
          <Button
            title="Cooked"
            accessibilityLabel={`Mark ${meal.title} as cooked`}
            variant="secondary"
            compact
            loading={cooked.isPending}
            disabled={busy}
            onPress={() => cooked.mutate(mealTap(meal.id))}
          />
        )}
      </View>
      <View accessibilityLiveRegion="polite">
        <ErrorText message={error?.message} />
      </View>
      {state.kind === 'cooked' ? <Tomorrow {...state.tomorrow} onPlan={onPlan} /> : null}
      {children}
    </Hero>
  );
}

/** After tonight is cooked: tomorrow's dinner, or a way to plan it. */
function Tomorrow({
  date,
  meal,
  onPlan,
}: {
  date: string;
  meal: PlannedMeal | null | undefined;
  onPlan: () => void;
}) {
  const t = useTheme();
  if (meal === undefined) return null; // next week still loading (Sundays)
  const when = `Tomorrow · ${formatDay(date)}`;
  return (
    <Pressable
      accessibilityRole={meal ? 'link' : 'button'}
      accessibilityLabel={
        meal ? `${when}: ${meal.title}. See the recipe` : `${when}: nothing planned yet. Plan it`
      }
      onPress={meal ? () => router.push(`/recipe/${meal.recipe_id}`) : onPlan}
      style={{
        flexDirection: 'row',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        columnGap: t.space.md,
        minHeight: t.touchTarget,
        borderTopWidth: 1,
        borderTopColor: t.colors.border,
        paddingTop: t.space.md,
      }}
    >
      <View style={{ flexShrink: 1 }}>
        <Text variant="caption" style={{ color: t.colors.onHeroMuted }}>
          {when}
        </Text>
        <Text variant="label" style={{ color: t.colors.onHero }}>
          {meal ? meal.title : 'Nothing planned yet'}
        </Text>
      </View>
      <Text variant="label" style={{ color: t.colors.onHero, textDecorationLine: 'underline' }}>
        {meal ? 'Recipe ›' : 'Plan it ›'}
      </Text>
    </Pressable>
  );
}
