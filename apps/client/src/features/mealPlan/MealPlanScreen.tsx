import { router } from 'expo-router';
import {
  CalendarDays,
  Check,
  ChevronLeft,
  ChevronRight,
  Ellipsis,
  Pencil,
  Plus,
  RefreshCw,
  Trash2,
  Undo2,
} from 'lucide-react-native';
import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { Icon } from '@/components/Icon';
import { PageHeader } from '@/components/PageHeader';
import { PressableScale } from '@/components/PressableScale';
import { RecipeArt } from '@/components/RecipeArt';
import { Sheet } from '@/components/Sheet';
import { Button, ErrorText, Loading, Screen, Text } from '@/components/ui';
import { mealTap, useMealPlan, useMealPlanActions } from '@/lib/api/mealPlan';
import { useTheme } from '@/theme/useTheme';

import { PlanSheet, startPlan } from './PlanSheet';
import {
  addDays,
  canPick,
  dayParts,
  mondayOf,
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
  const footer =
    week.data && meals.length > 0 ? (
      <Button
        title="Update plan"
        icon={Pencil}
        onPress={() =>
          setAsk({ title: next ? 'Edit next week' : 'Edit my week', week: week.data.start })
        }
      />
    ) : undefined;

  return (
    <Screen edges={['top', 'left', 'right']} footer={footer}>
      <PageHeader icon={CalendarDays} title="Plan my week" />
      <WeekToggle next={next} onChange={setNext} />

      {week.isPending || !today ? (
        <Loading />
      ) : week.isError ? (
        <>
          <ErrorText message={week.error.message} />
          <Button title="Try again" onPress={() => week.refetch()} />
        </>
      ) : (
        <>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.sm }}>
            <RoundButton
              label="This week"
              icon={ChevronLeft}
              disabled={!next}
              onPress={() => setNext(false)}
            />
            <View
              style={{
                flex: 1,
                flexDirection: 'row',
                alignItems: 'center',
                justifyContent: 'center',
                gap: t.space.sm,
              }}
            >
              <Icon icon={CalendarDays} size={18} color={t.colors.onBackground} />
              <Text
                variant="label"
                accessibilityLiveRegion="polite"
                style={{ color: t.colors.onBackground }}
              >
                {weekRange(week.data.start)}
              </Text>
            </View>
            <RoundButton
              label="Next week"
              icon={ChevronRight}
              disabled={next}
              onPress={() => setNext(true)}
            />
          </View>

          {meals.length === 0 ? (
            <EmptyWeek
              next={next}
              onPlan={() =>
                setAsk({ title: next ? 'Plan next week' : 'Plan my week', week: week.data.start })
              }
            />
          ) : (
            <View style={{ gap: t.space.sm }}>
              {weekDays(week.data.start, meals).map((day) => (
                <DayRow key={day.date} day={day} today={today} onMore={setMenu} />
              ))}
            </View>
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

/** This week / Next week: two tabs on a pill, the chosen one dark. */
function WeekToggle({ next, onChange }: { next: boolean; onChange: (next: boolean) => void }) {
  const t = useTheme();
  const tab = (label: string, selected: boolean, value: boolean) => (
    <Pressable
      key={label}
      accessibilityRole="tab"
      accessibilityState={{ selected }}
      onPress={() => onChange(value)}
      style={{
        flex: 1,
        minHeight: t.touchTarget,
        borderRadius: t.radius.pill,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: selected ? t.colors.selected : 'transparent',
      }}
    >
      <Text variant="label" style={{ color: selected ? t.colors.onSelected : t.colors.text }}>
        {label}
      </Text>
    </Pressable>
  );
  return (
    <View
      accessibilityRole="tablist"
      style={{
        flexDirection: 'row',
        gap: 4,
        padding: 4,
        borderRadius: t.radius.pill,
        backgroundColor: t.colors.surface,
        boxShadow: t.shadow.card,
      }}
    >
      {tab('This week', !next, false)}
      {tab('Next week', next, true)}
    </View>
  );
}

function RoundButton({
  label,
  icon,
  disabled,
  onPress,
}: {
  label: string;
  icon: typeof ChevronLeft;
  disabled: boolean;
  onPress: () => void;
}) {
  const t = useTheme();
  return (
    <PressableScale
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={onPress}
      style={{
        width: t.touchTarget,
        height: t.touchTarget,
        borderRadius: t.radius.pill,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.surface,
        boxShadow: t.shadow.card,
        opacity: disabled ? 0.4 : 1,
      }}
    >
      <Icon icon={icon} size={18} color={t.colors.text} strong />
    </PressableScale>
  );
}

function EmptyWeek({ next, onPlan }: { next: boolean; onPlan: () => void }) {
  const t = useTheme();
  return (
    <View
      style={{
        alignItems: 'center',
        gap: t.space.sm,
        padding: t.space.xl,
        borderRadius: t.radius.lg,
        backgroundColor: t.colors.surface,
        boxShadow: t.shadow.card,
      }}
    >
      <View
        aria-hidden
        style={{
          width: 64,
          height: 64,
          borderRadius: 32,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: t.colors.actionSoft,
        }}
      >
        <Icon icon={CalendarDays} size={30} color={t.colors.onActionSoft} />
      </View>
      <Text variant="heading" role="heading" aria-level={2} style={{ textAlign: 'center' }}>
        {next ? 'Nothing planned for next week' : 'No plan for this week yet'}
      </Text>
      <Text muted style={{ textAlign: 'center' }}>
        Sweep plans dinners around your Kitchen and Dietary Rules, then adds only what&apos;s
        missing to the list.
      </Text>
      <Button title={next ? 'Plan next week' : 'Plan my week'} onPress={onPlan} />
    </View>
  );
}

function DayRow({
  day,
  today,
  onMore,
}: {
  day: Day;
  today: string;
  onMore: (meal: PlannedMeal) => void;
}) {
  const t = useTheme();
  const isToday = day.date === today;
  const { weekday, day: num } = dayParts(day.date);
  const meal = day.meal;
  const cooked = meal?.cooked_at != null;
  const meta = meal
    ? [
        meal.total_minutes ? `${meal.total_minutes} min` : null,
        `Serves ${meal.servings}`,
        cooked ? 'Cooked ✓' : null,
      ]
        .filter(Boolean)
        .join(' · ')
    : '';

  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.sm,
        minHeight: 68,
        paddingVertical: t.space.xs,
        paddingLeft: t.space.sm,
        paddingRight: t.space.xs,
        borderRadius: t.radius.md,
        backgroundColor: isToday ? t.colors.actionSoft : t.colors.surface,
        boxShadow: t.shadow.card,
      }}
    >
      <View
        accessibilityLabel={isToday ? `Today, ${weekday} ${num}` : `${weekday} ${num}`}
        style={{
          width: 44,
          paddingVertical: t.space.xs,
          borderRadius: t.radius.sm,
          alignItems: 'center',
          backgroundColor: isToday ? t.colors.action : t.colors.background,
        }}
      >
        <Text variant="caption" style={{ color: isToday ? t.colors.onAction : t.colors.text }}>
          {weekday}
        </Text>
        <Text variant="label" style={{ color: isToday ? t.colors.onAction : t.colors.text }}>
          {num}
        </Text>
      </View>

      {meal ? (
        <>
          <PressableScale
            accessibilityRole="link"
            accessibilityLabel={`${meal.title}. ${meta}. See the recipe`}
            onPress={() => router.push(`/recipe/${meal.recipe_id}`)}
            style={{ flex: 1, flexDirection: 'row', alignItems: 'center', gap: t.space.sm }}
          >
            <RecipeArt title={meal.title} width={60} height={50} radius={12} emojiSize={28} />
            <View style={{ flex: 1 }}>
              <Text variant="label" numberOfLines={2}>
                {meal.title}
              </Text>
              <Text variant="caption" muted>
                {meta}
              </Text>
            </View>
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
          <Text muted style={{ flex: 1 }}>
            Nothing planned
          </Text>
          {canPick(day.date, today) ? (
            <Button
              title="Add"
              icon={Plus}
              accessibilityLabel={`Add a dinner on ${weekday} ${num}`}
              variant="secondary"
              compact
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
