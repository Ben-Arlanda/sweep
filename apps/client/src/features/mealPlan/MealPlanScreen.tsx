import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { Button, Card, ErrorText, Loading, Screen, Text } from '@/components/ui';
import { formatDay } from '@/features/chat/format';
import { requestPlan } from '@/features/chat/starters';
import { mealTap, useMealPlan, useMealPlanActions } from '@/lib/api/mealPlan';
import { useTheme } from '@/theme/useTheme';

import { PlanSheet } from './PlanSheet';
import { addDays, mondayOf, weekDays, type Day, type PlannedMeal } from './week';
import { WeekStrip, type StripMeal } from './WeekStrip';

/**
 * A Mon–Sun week of dinners (slice 5d): the week strip for a glance, then one row per
 * day so a gap is visible; ‹ › to move a week. Cooked takes the recipe out of the Kitchen; its undo stays on the row with no
 * time limit (a toast that vanishes after a few seconds fails WCAG 2.2.1).
 *
 * `start` null means "this week", which the server counts from today in Sydney. We
 * don't work out today on the phone: its clock or time zone may disagree.
 */
export function MealPlanScreen() {
  const t = useTheme();
  const [start, setStart] = useState<string | null>(null);
  const [planning, setPlanning] = useState(false);
  const week = useMealPlan(start);
  const thisWeek = useMealPlan(null).data?.start;

  function move(days: number) {
    if (!week.data) return;
    const next = addDays(week.data.start, days);
    setStart(next === thisWeek ? null : next);
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
        <WeekStrip monday={week.data.start} today={today} meals={stripMeals} />
      </Card>

      <Card>
        {days.map((day) => (
          <DayRow key={day.date} day={day} label={dayLabel(day.date, today)} />
        ))}
      </Card>

      {/* The sheet plans this week or next, so offer it there while a day is free. */}
      {canPlan(days, today) ? (
        <Button title="Plan free days with Sweep" onPress={() => setPlanning(true)} />
      ) : null}
      {planning ? (
        <PlanSheet
          week={week.data.start}
          onClose={() => setPlanning(false)}
          onPick={(mode, picked) => {
            requestPlan(mode, picked);
            router.push('/plan');
          }}
        />
      ) : null}
    </Screen>
  );
}

/** This week or next, with a free day from today on. */
function canPlan(days: Day[], today: string) {
  const monday = days[0].date;
  const inRange = monday === mondayOf(today) || monday === addDays(mondayOf(today), 7);
  return inRange && days.some((d) => d.date >= today && d.meal === null);
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
        onPress={() => router.push(`/recipes/${meal.recipe_id}`)}
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
