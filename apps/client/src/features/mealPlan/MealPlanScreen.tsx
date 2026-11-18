import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { Button, Card, ErrorText, Loading, Screen, Text } from '@/components/ui';
import { formatDay } from '@/features/chat/format';
import { requestPlan } from '@/features/chat/starters';
import { mealTap, useMealPlan, useMealPlanActions } from '@/lib/api/mealPlan';
import { useTheme } from '@/theme/useTheme';

import { PlanChoices } from './PlanChoices';
import { addDays, canPick, mondayOf, weekDays, type Day, type PlannedMeal } from './week';
import { WeekStrip, type StripMeal } from './WeekStrip';

/**
 * A Mon–Sun week of dinners (slice 5d). The week strip on top is also where you plan:
 * tap days from today on (a planned one to replace it), then pick the kind of plan.
 * Below, one row per day so a gap is visible; ‹ › to move a week. Cooked takes the
 * recipe out of the Kitchen; its undo stays on the row with no time limit (a toast
 * that vanishes after a few seconds fails WCAG 2.2.1).
 *
 * `start` null means "this week", which the server counts from today in Sydney. We
 * don't work out today on the phone: its clock or time zone may disagree.
 */
export function MealPlanScreen() {
  const t = useTheme();
  const [start, setStart] = useState<string | null>(null);
  const [picked, setPicked] = useState<string[]>([]);
  const week = useMealPlan(start);
  const thisWeek = useMealPlan(null).data?.start;

  function move(days: number) {
    if (!week.data) return;
    const next = addDays(week.data.start, days);
    setStart(next === thisWeek ? null : next);
    setPicked([]); // ticks belong to the week they were made in
  }

  if (week.isPending) return <Loading />;
  if (week.isError) {
    return (
      <Screen>
        <ErrorText message={week.error.message} />
        <Button title="Try again" onPress={() => week.refetch()} />
      </Screen>
    );
  }

  const { today } = week.data;
  const days = weekDays(week.data.start, week.data.meals);
  const range = `${formatDay(week.data.start)} – ${formatDay(week.data.end)}`;
  const isThisWeek = start === null;
  const stripMeals: Record<string, StripMeal> = Object.fromEntries(
    week.data.meals.map((m) => [m.date, { title: m.title, cooked: m.cooked_at !== null }]),
  );
  const planned = week.data.meals.map((m) => m.date);
  // A plan covers today and the next 13 days, so this week and next can be planned.
  const plannable =
    week.data.start === mondayOf(today) || week.data.start === addDays(mondayOf(today), 7);
  const pickable = plannable && days.some((d) => canPick(d.date, today));

  function toggle(date: string) {
    setPicked((now) =>
      now.includes(date) ? now.filter((d) => d !== date) : [...now, date].sort(),
    );
  }

  return (
    <Screen>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.sm }}>
        <Button
          title="‹"
          accessibilityLabel="Previous week"
          variant="secondary"
          compact
          onPress={() => move(-7)}
        />
        <Text
          variant="heading"
          role="heading"
          aria-level={2}
          style={{ flex: 1, textAlign: 'center' }}
        >
          {isThisWeek ? 'This week' : range}
        </Text>
        <Button
          title="›"
          accessibilityLabel="Next week"
          variant="secondary"
          compact
          onPress={() => move(7)}
        />
      </View>
      {isThisWeek ? null : (
        <Button title="Back to this week" variant="ghost" onPress={() => setStart(null)} />
      )}

      <Card>
        <Text variant="caption" muted>
          {range} · {week.data.meals.length} of 7 planned
        </Text>
        <WeekStrip
          monday={week.data.start}
          today={today}
          meals={stripMeals}
          picked={pickable ? picked : undefined}
          onToggle={pickable ? toggle : undefined}
        />
        <Text variant="caption" muted accessibilityLiveRegion="polite">
          {planHint(picked.length, plannable, pickable, week.data.start < mondayOf(today))}
        </Text>
        {picked.length > 0 ? (
          <PlanChoices
            monday={week.data.start}
            today={today}
            planned={planned}
            picked={picked}
            onPick={(mode, days) => {
              setPicked([]);
              requestPlan(mode, days);
              router.push('/plan-week');
            }}
          />
        ) : null}
      </Card>

      <Card>
        {days.map((day) => (
          <DayRow key={day.date} day={day} label={dayLabel(day.date, today)} />
        ))}
      </Card>
    </Screen>
  );
}

/** What the line under the strip says, so it's clear the days can be tapped. */
function planHint(count: number, plannable: boolean, pickable: boolean, past: boolean) {
  if (past) return 'This week has gone.';
  if (!plannable) return 'Sweep plans up to two weeks ahead.';
  if (!pickable) return 'Nothing left to plan this week. Use › for next week.';
  if (count === 0) return 'Tap days to plan them with Sweep. Tap a ✓ day to replace its dinner.';
  return `${count} ${count === 1 ? 'day' : 'days'} picked. What kind of plan?`;
}

/** "Today" and "Tomorrow" come from the server's today, not the phone's clock. */
function dayLabel(date: string, today: string) {
  if (date === today) return 'Today';
  if (date === addDays(today, 1)) return 'Tomorrow';
  return formatDay(date);
}

function DayRow({ day, label }: { day: Day; label: string }) {
  const t = useTheme();
  return (
    <View
      style={{
        flexDirection: 'row',
        flexWrap: 'wrap', // wraps at 320px wide instead of squeezing (WCAG reflow)
        alignItems: 'center',
        columnGap: t.space.md,
        rowGap: t.space.xs,
        minHeight: t.touchTarget,
      }}
    >
      <Text variant="label" style={{ minWidth: 92 }}>
        {label}
      </Text>
      {day.meal ? <Meal meal={day.meal} /> : <Text muted>Nothing planned</Text>}
    </View>
  );
}

function Meal({ meal }: { meal: PlannedMeal }) {
  const t = useTheme();
  const { cooked, undoCooked, remove } = useMealPlanActions();
  const isCooked = meal.cooked_at !== null;
  const busy = cooked.isPending || undoCooked.isPending || remove.isPending;
  const error = cooked.error ?? undoCooked.error ?? remove.error;

  return (
    <View style={{ flex: 1, minWidth: 180, gap: t.space.xs }}>
      <Pressable
        accessibilityRole="link"
        accessibilityLabel={`${meal.title}, serves ${meal.servings}${isCooked ? ', cooked' : ''}`}
        onPress={() => router.push(`/recipe/${meal.recipe_id}`)}
        style={{ minHeight: t.touchTarget, justifyContent: 'center' }}
      >
        <Text style={{ textDecorationLine: 'underline' }}>{meal.title}</Text>
        <Text variant="caption" muted>
          Serves {meal.servings}
          {isCooked ? ' · Cooked ✓' : ''}
        </Text>
      </Pressable>

      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}>
        {isCooked ? (
          <Button
            title="Undo"
            accessibilityLabel={`Undo cooked for ${meal.title}`}
            variant="secondary"
            compact
            loading={undoCooked.isPending}
            disabled={busy}
            onPress={() => undoCooked.mutate(mealTap(meal.id))}
          />
        ) : (
          <>
            <Button
              title="Cooked"
              accessibilityLabel={`Mark ${meal.title} as cooked`}
              variant="secondary"
              compact
              loading={cooked.isPending}
              disabled={busy}
              onPress={() => cooked.mutate(mealTap(meal.id))}
            />
            <Button
              title="Remove"
              accessibilityLabel={`Remove ${meal.title} from the plan`}
              variant="ghost"
              compact
              loading={remove.isPending}
              disabled={busy}
              onPress={() => remove.mutate(mealTap(meal.id))}
            />
          </>
        )}
      </View>
      <View accessibilityLiveRegion="polite">
        <ErrorText message={error?.message} />
      </View>
    </View>
  );
}
