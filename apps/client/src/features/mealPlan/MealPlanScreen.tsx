import { router } from 'expo-router';
import { CalendarDays, Check, Ellipsis, Plus, RefreshCw, Trash2, Undo2 } from 'lucide-react-native';
import { Image } from 'expo-image';
import { useState } from 'react';
import { View } from 'react-native';
import { useReducedMotion } from 'react-native-reanimated';

import { Icon } from '@/components/Icon';
import { PageHeader } from '@/components/PageHeader';
import { PressableScale } from '@/components/PressableScale';
import { Segmented } from '@/components/Segmented';
import { Sheet } from '@/components/Sheet';
import { Button, ErrorText, Loading, Screen, Text } from '@/components/ui';
import { mealTap, useMealPlan, useMealPlanActions } from '@/lib/api/mealPlan';
import { sectionTints } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

import { PlanSheet, startPlan } from './PlanSheet';
import {
  addDays,
  canPick,
  dayParts,
  mondayOf,
  shortWeekRange,
  weekDays,
  weekRange,
  type Day,
  type PlannedMeal,
} from './week';

type SheetAsk = { title: string; week: string; days?: string[] };

/**
 * The Plan tab (ADR 0026): this week or next, one row per day. ••• on a dinner opens
 * the recipe, Cooked, Swap and Remove. Swap and Add open Dinner Ideas for that day,
 * planned straight away by code (ADR 0025). Update plan opens the Plan my week sheet.
 *
 * Only this week and next: a plan covers today and the next 13 days. "Today" is the
 * server's, never the phone's clock (a wrong time zone would show the wrong day).
 */
export function MealPlanScreen() {
  const t = useTheme();
  const [next, setNext] = useState(false);
  const thisWeek = useMealPlan(null);
  const today = thisWeek.data?.today;
  const nextMonday = today ? addDays(mondayOf(today), 7) : null;
  const nextWeek = useMealPlan(nextMonday, next && nextMonday !== null);
  const week = next ? nextWeek : thisWeek;
  const [menu, setMenu] = useState<PlannedMeal | null>(null);
  const [ask, setAsk] = useState<SheetAsk | null>(null);

  const meals = week.data?.meals ?? [];

  return (
    <Screen edges={['top', 'left', 'right']}>
      <PageHeader icon={CalendarDays} section="plan" title="Plan my week" />
      {today && nextMonday ? (
        <Segmented
          label="Week"
          value={next ? 'next' : 'this'}
          onChange={(v) => setNext(v === 'next')}
          options={[
            { value: 'this', label: shortWeekRange(mondayOf(today)) },
            { value: 'next', label: shortWeekRange(nextMonday) },
          ]}
        />
      ) : null}

      {week.isPending || !today ? (
        <Loading />
      ) : week.isError ? (
        <>
          <ErrorText message={week.error.message} />
          <Button title="Try again" onPress={() => week.refetch()} />
        </>
      ) : (
        <>
          {meals.length === 0 ? (
            <EmptyWeek
              next={next}
              onPlan={() =>
                setAsk({ title: next ? 'Plan next week' : 'Plan my week', week: week.data.start })
              }
            />
          ) : (
            <>
              <View
                accessibilityLabel={weekRange(week.data.start)}
                style={{
                  backgroundColor: t.colors.surface,
                  borderRadius: t.radius.lg,
                  boxShadow: t.shadow.card,
                  overflow: 'hidden',
                }}
              >
                {weekDays(week.data.start, meals).map((day, i) => (
                  <DayRow key={day.date} day={day} today={today} first={i === 0} onMore={setMenu} />
                ))}
              </View>
              <Button
                title="Update plan"
                onPress={() =>
                  setAsk({ title: next ? 'Edit next week' : 'Edit my week', week: week.data.start })
                }
              />
            </>
          )}
        </>
      )}

      {menu && today ? <MealMenu meal={menu} today={today} onClose={() => setMenu(null)} /> : null}
      {ask ? (
        <PlanSheet
          title={ask.title}
          week={ask.week}
          days={ask.days}
          onClose={() => setAsk(null)}
          onPick={startPlan}
        />
      ) : null}
    </Screen>
  );
}

function EmptyWeek({ next, onPlan }: { next: boolean; onPlan: () => void }) {
  const t = useTheme();
  const reduceMotion = useReducedMotion();
  return (
    <View
      style={{
        alignItems: 'center',
        gap: 10,
        paddingVertical: 28,
        paddingHorizontal: 20,
        borderRadius: t.radius.lg,
        backgroundColor: t.colors.surface,
        boxShadow: t.shadow.card,
      }}
    >
      <Image
        aria-hidden
        source={require('../../../assets/images/chef-blink.webp')}
        style={{ width: 72, height: 72 }}
        contentFit="contain"
        autoplay={!reduceMotion}
      />
      <Text variant="heading" role="heading" aria-level={2} style={{ textAlign: 'center' }}>
        {next ? 'Next week is open' : 'No plan for this week yet'}
      </Text>
      <Text muted style={{ textAlign: 'center', fontSize: 14, lineHeight: 20 }}>
        Sweep can plan it from what&apos;s in your Kitchen, then adds only what&apos;s missing to
        the list.
      </Text>
      <View>
        <Button title={next ? 'Plan next week' : 'Plan my week'} compact onPress={onPlan} />
      </View>
    </View>
  );
}

function DayRow({
  day,
  today,
  first,
  onMore,
}: {
  day: Day;
  today: string;
  first: boolean;
  onMore: (meal: PlannedMeal) => void;
}) {
  const t = useTheme();
  const isToday = day.date === today;
  const { weekday, day: num } = dayParts(day.date);
  const meal = day.meal;
  const cooked = meal?.cooked_at != null;
  const sub = meal
    ? cooked
      ? '✓ Cooked'
      : [isToday ? 'Tonight' : null, meal.total_minutes ? `${meal.total_minutes} min` : null]
          .filter(Boolean)
          .join(' · ') || `Serves ${meal.servings}`
    : null;

  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.md,
        minHeight: 64,
        paddingVertical: t.space.sm,
        paddingLeft: t.space.sm,
        paddingRight: 6,
        borderTopWidth: first ? 0 : 1,
        borderTopColor: t.colors.border,
      }}
    >
      <View
        accessibilityLabel={isToday ? `Today, ${weekday} ${num}` : `${weekday} ${num}`}
        // minWidth, not width: bold "Today" at a larger text size needs more than 40.
        style={{ minWidth: 46, alignItems: 'center' }}
      >
        <Text
          numberOfLines={1}
          style={{
            fontSize: 11,
            lineHeight: 14,
            fontFamily: isToday ? t.fonts.bold : t.fonts.body,
            color: isToday ? sectionTints.plan.fg : t.colors.textMuted,
          }}
        >
          {isToday ? 'Today' : weekday}
        </Text>
        <Text
          style={{ fontSize: 17, lineHeight: 22, fontFamily: t.fonts.bold, color: t.colors.text }}
        >
          {num}
        </Text>
      </View>

      {meal ? (
        <>
          <PressableScale
            accessibilityRole="link"
            accessibilityLabel={`${meal.title}. ${sub}. See the recipe`}
            onPress={() => router.push(`/recipe/${meal.recipe_id}`)}
            style={{ flex: 1, gap: 2, minHeight: t.touchTarget, justifyContent: 'center' }}
          >
            <Text variant="label" numberOfLines={2}>
              {meal.title}
            </Text>
            <Text
              variant="caption"
              style={{
                color: cooked ? t.stock.in_stock.fg : t.colors.textMuted,
                fontFamily: cooked ? t.fonts.medium : t.fonts.body,
              }}
            >
              {sub}
            </Text>
          </PressableScale>
          <PressableScale
            accessibilityRole="button"
            accessibilityLabel={`More for ${meal.title} on ${weekday} ${num}`}
            onPress={() => onMore(meal)}
            style={{
              width: t.touchTarget,
              height: t.touchTarget,
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Icon icon={Ellipsis} color={t.colors.text} strong />
          </PressableScale>
        </>
      ) : (
        <>
          <Text style={{ flex: 1, fontFamily: t.fonts.medium, color: t.colors.textMuted }}>
            No dinner planned
          </Text>
          {canPick(day.date, today) ? (
            <Button
              title="Add"
              icon={Plus}
              accessibilityLabel={`Add a dinner on ${weekday} ${num}`}
              variant="secondary"
              compact
              tight
              onPress={() => openIdeas(day.date)}
            />
          ) : null}
        </>
      )}
    </View>
  );
}

/** Dinner Ideas for one day: picking one plans it there straight away (ADR 0025). */
function openIdeas(date: string) {
  router.push({ pathname: '/tonight', params: { date } });
}

/**
 * ••• on a day: the recipe, Cooked (with Undo, no time limit: WCAG 2.2.1), Swap and
 * Remove. A cooked dinner can't be swapped or removed: it already left the Kitchen.
 */
function MealMenu({
  meal,
  today,
  onClose,
}: {
  meal: PlannedMeal;
  today: string;
  onClose: () => void;
}) {
  const t = useTheme();
  const { cooked, undoCooked, remove } = useMealPlanActions();
  const isCooked = meal.cooked_at !== null;
  const busy = cooked.isPending || undoCooked.isPending || remove.isPending;
  const error = cooked.error ?? undoCooked.error ?? remove.error;
  const { weekday, day } = dayParts(meal.date);
  const done = { onSuccess: onClose };

  return (
    <Sheet label={`${meal.title}, ${weekday} ${day}`} title={meal.title} onClose={onClose}>
      <View style={{ gap: t.space.sm }}>
        <Text muted>
          {weekday} {day} · Serves {meal.servings}
          {isCooked ? ' · Cooked ✓' : ''}
        </Text>
        <Button
          title="View recipe"
          variant="strong"
          onPress={() => {
            onClose();
            router.push(`/recipe/${meal.recipe_id}`);
          }}
        />
        {isCooked ? (
          <Button
            title="Undo cooked"
            icon={Undo2}
            variant="secondary"
            loading={undoCooked.isPending}
            disabled={busy}
            onPress={() => undoCooked.mutate(mealTap(meal.id), done)}
          />
        ) : (
          <>
            <Button
              title="Mark cooked"
              icon={Check}
              accessibilityLabel={`Mark ${meal.title} as cooked`}
              variant="secondary"
              loading={cooked.isPending}
              disabled={busy}
              onPress={() => cooked.mutate(mealTap(meal.id), done)}
            />
            {canPick(meal.date, today) ? (
              <Button
                title="Swap for another"
                icon={RefreshCw}
                variant="secondary"
                disabled={busy}
                onPress={() => {
                  onClose();
                  openIdeas(meal.date);
                }}
              />
            ) : null}
            <Button
              title="Remove from plan"
              icon={Trash2}
              variant="danger"
              loading={remove.isPending}
              disabled={busy}
              onPress={() => remove.mutate(mealTap(meal.id), done)}
            />
          </>
        )}
        <View accessibilityLiveRegion="polite">
          <ErrorText message={error?.message} />
        </View>
      </View>
    </Sheet>
  );
}
