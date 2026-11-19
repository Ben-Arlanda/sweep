import { Image } from 'expo-image';
import { router, type Href } from 'expo-router';
import {
  Bookmark,
  CalendarDays,
  ChevronRight,
  Clock,
  Refrigerator,
  ShoppingBasket,
  Sparkles,
  Undo2,
  type LucideIcon,
} from 'lucide-react-native';
import { useState } from 'react';
import { View } from 'react-native';
import { useReducedMotion } from 'react-native-reanimated';

import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { RecipeArt } from '@/components/RecipeArt';
import { Button, ErrorText, Loading, Text } from '@/components/ui';
import { canPick, dayParts, weekDays, weekRange, type PlannedMeal } from '@/features/mealPlan/week';
import { IdeaTile, KITCHEN_FIRST } from '@/features/recipes/IdeaTile';
import { useList } from '@/lib/api/lists';
import { mealTap, useMealPlan, useMealPlanActions } from '@/lib/api/mealPlan';
import { useDinnerIdeas } from '@/lib/api/planning';
import { sectionTints } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

import { hasPlan, homeState, usesLine } from './today';

/**
 * Under Home's hero (ADR 0026): tonight's card, or "Your meal plan" once the week is
 * planned; then three quick tiles and recipe ideas from the Kitchen.
 */
export function TodayBelow({ onEditPlan }: { onEditPlan: () => void }) {
  const week = useMealPlan(null);
  const data = week.data;
  return (
    <>
      {!data ? null : hasPlan(data.today, data.meals) ? (
        <MealPlanCard
          monday={data.start}
          today={data.today}
          meals={data.meals}
          onEdit={onEditPlan}
        />
      ) : (
        <TonightCard today={data.today} meals={data.meals} />
      )}
      <QuickTiles />
      <RecipeIdeas />
    </>
  );
}

function Card({ children, flush }: { children: React.ReactNode; flush?: boolean }) {
  const t = useTheme();
  return (
    <View
      style={{
        backgroundColor: t.colors.surface,
        borderRadius: t.radius.lg,
        padding: flush ? 0 : t.space.lg,
        gap: flush ? 0 : t.space.md,
        overflow: flush ? 'hidden' : undefined,
        boxShadow: t.shadow.card,
      }}
    >
      {children}
    </View>
  );
}

/** "25 min · Serves 4", with a clock. */
function MealMeta({ meal }: { meal: PlannedMeal }) {
  const t = useTheme();
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
      {meal.total_minutes ? <Icon icon={Clock} size={14} color={t.colors.textMuted} /> : null}
      <Text variant="caption" muted>
        {meal.total_minutes ? `${meal.total_minutes} min · ` : ''}Serves {meal.servings}
      </Text>
    </View>
  );
}

/** Cooked takes the recipe out of the Kitchen; Undo stays with no time limit (WCAG 2.2.1). */
function CookedButton({ meal }: { meal: PlannedMeal }) {
  const { cooked, undoCooked } = useMealPlanActions();
  const isCooked = meal.cooked_at !== null;
  const busy = cooked.isPending || undoCooked.isPending;
  const error = cooked.error ?? undoCooked.error;
  return (
    <>
      <Button
        title={isCooked ? 'Undo' : 'Mark cooked'}
        tight
        icon={isCooked ? Undo2 : undefined}
        accessibilityLabel={
          isCooked ? `Undo cooked for ${meal.title}` : `Mark ${meal.title} as cooked`
        }
        variant={isCooked ? 'outline' : 'secondary'}
        loading={busy}
        disabled={busy}
        onPress={() => (isCooked ? undoCooked : cooked).mutate(mealTap(meal.id))}
      />
      {error ? <ErrorText message={error.message} /> : null}
    </>
  );
}

/** Tonight, before there's a plan: nothing yet, tonight's dinner, or cooked. */
function TonightCard({ today, meals }: { today: string; meals: PlannedMeal[] }) {
  const t = useTheme();
  const state = homeState({ today, thisWeek: meals });

  if (state.kind === 'free' || state.kind === 'empty') {
    return (
      <Card>
        <View style={{ gap: 4 }}>
          <Text variant="caption" muted style={{ fontFamily: t.fonts.medium }}>
            Tonight
          </Text>
          <Text variant="heading" role="heading" aria-level={2}>
            No meal planned
          </Text>
          <Text variant="caption" muted>
            Get a dinner idea in seconds.
          </Text>
        </View>
        <View>
          <Button
            title="Find dinner ideas"
            icon={Sparkles}
            onPress={() => router.push('/tonight')}
          />
        </View>
      </Card>
    );
  }

  const meal = state.tonight;
  const isCooked = state.kind === 'cooked';
  return (
    <Card>
      <PressableScale
        accessibilityRole="link"
        accessibilityLabel={`Tonight: ${meal.title}${isCooked ? ', cooked' : ''}. See the recipe`}
        onPress={() => router.push(`/recipe/${meal.recipe_id}`)}
        style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.md }}
      >
        <View style={{ flex: 1, gap: 2 }}>
          <Text
            variant="caption"
            accessibilityLiveRegion="polite"
            style={{ color: isCooked ? t.colors.tabSelected : t.colors.textMuted }}
          >
            {isCooked ? 'Tonight · Cooked ✓' : 'Tonight'}
          </Text>
          <Text variant="heading" role="heading" aria-level={2}>
            {meal.title}
          </Text>
          {isCooked ? (
            <Text variant="caption" muted>
              {usesLine(meal)}
            </Text>
          ) : (
            <MealMeta meal={meal} />
          )}
        </View>
        <RecipeArt title={meal.title} width={112} height={84} radius={16} emojiSize={44} />
      </PressableScale>
      <View>
        <CookedButton meal={meal} />
      </View>
    </Card>
  );
}

/**
 * The week, once there's a plan: tap a day to see its dinner underneath. Today starts
 * selected and is the one you can mark Cooked.
 */
function MealPlanCard({
  monday,
  today,
  meals,
  onEdit,
}: {
  monday: string;
  today: string;
  meals: PlannedMeal[];
  onEdit: () => void;
}) {
  const t = useTheme();
  const [selected, setSelected] = useState(today);
  const days = weekDays(monday, meals);
  const day = days.find((d) => d.date === selected) ?? days[0];
  const parts = dayParts(day.date);
  const isToday = day.date === today;
  const eyebrow = isToday
    ? day.meal?.cooked_at
      ? 'Tonight · Cooked ✓'
      : `Tonight · ${parts.weekday} ${parts.day}`
    : `${parts.weekday} ${parts.day}`;

  return (
    <View style={{ gap: t.space.sm + 2 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.md }}>
        <PressableScale
          accessibilityRole="link"
          accessibilityLabel={`Your meal plan, ${weekRange(monday)}, ${meals.length} dinners. Open the Plan tab`}
          onPress={() => router.push('/meal-plan')}
          style={{ flex: 1, minHeight: t.touchTarget, justifyContent: 'center', gap: 2 }}
        >
          <Text
            variant="label"
            role="heading"
            aria-level={2}
            style={{ fontSize: 17, lineHeight: 22 }}
          >
            Your meal plan
          </Text>
          <Text variant="caption" muted style={{ fontVariant: ['tabular-nums'] }}>
            {weekRange(monday)} · {meals.length} {meals.length === 1 ? 'dinner' : 'dinners'}
          </Text>
        </PressableScale>
        <PressableScale
          accessibilityRole="button"
          onPress={onEdit}
          style={{ minHeight: t.touchTarget, justifyContent: 'center', paddingLeft: t.space.md }}
        >
          <Text variant="label">Edit plan</Text>
        </PressableScale>
      </View>

      <Card flush>
        <View
          accessibilityRole="tablist"
          style={{
            flexDirection: 'row',
            gap: 4,
            padding: t.space.sm,
            borderBottomWidth: 1,
            borderBottomColor: t.colors.border,
          }}
        >
          {days.map((d) => {
            const p = dayParts(d.date);
            const on = d.date === selected;
            const isTodayTab = d.date === today;
            return (
              <PressableScale
                key={d.date}
                accessibilityRole="tab"
                accessibilityState={{ selected: on }}
                accessibilityLabel={`${p.weekday} ${p.day}${isTodayTab ? ', tonight' : ''}: ${d.meal ? d.meal.title : 'nothing planned'}`}
                onPress={() => setSelected(d.date)}
                style={{
                  flex: 1,
                  minWidth: 0,
                  height: 58,
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 1,
                  borderRadius: 10,
                  backgroundColor: on ? t.colors.selected : 'transparent',
                }}
              >
                <Text
                  style={{
                    fontSize: 11,
                    lineHeight: 14,
                    fontFamily: isTodayTab ? t.fonts.bold : t.fonts.body,
                    color: on ? t.colors.onSelectedMuted : t.colors.textMuted,
                  }}
                >
                  {p.weekday}
                </Text>
                <Text
                  style={{
                    fontSize: 15,
                    lineHeight: 20,
                    fontFamily: t.fonts.bold,
                    fontVariant: ['tabular-nums'],
                    color: on ? t.colors.onSelected : t.colors.text,
                    // Today is underlined too, so it isn't told apart by weight alone.
                    textDecorationLine: isTodayTab && !on ? 'underline' : 'none',
                  }}
                >
                  {p.day}
                </Text>
                {/* A dot under days with a dinner planned. */}
                <View
                  style={{
                    width: 4,
                    height: 4,
                    borderRadius: 2,
                    backgroundColor: d.meal
                      ? on
                        ? t.colors.action
                        : t.colors.textMuted
                      : 'transparent',
                  }}
                />
              </PressableScale>
            );
          })}
        </View>

        <View accessibilityLiveRegion="polite">
          {day.meal ? (
            <RecipeArt title={day.meal.title} width="100%" height={132} radius={0} emojiSize={56} />
          ) : null}
          <View style={{ padding: t.space.lg, paddingTop: 14, gap: t.space.md }}>
            <View style={{ gap: 4 }}>
              <Text variant="caption" muted style={{ fontFamily: t.fonts.medium }}>
                {eyebrow}
              </Text>
              <Text variant="heading" style={day.meal ? null : { color: t.colors.textMuted }}>
                {day.meal ? day.meal.title : 'Nothing planned'}
              </Text>
              {day.meal ? <MealMeta meal={day.meal} /> : null}
            </View>
            {/* Side by side in equal shares; only on the narrowest phones does each take
                its own full row. */}
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}>
              {day.meal ? (
                <View style={{ flexGrow: 1, flexBasis: 140 }}>
                  <Button
                    title="View recipe"
                    tight
                    // Lime only for tonight's dinner: the one thing to do next.
                    variant={isToday && !day.meal.cooked_at ? 'primary' : 'secondary'}
                    onPress={() => day.meal && router.push(`/recipe/${day.meal.recipe_id}`)}
                  />
                </View>
              ) : canPick(day.date, today) ? (
                <View style={{ flexGrow: 1, flexBasis: 140 }}>
                  <Button
                    title="Add a dinner"
                    tight
                    variant="secondary"
                    onPress={() =>
                      router.push({ pathname: '/tonight', params: { date: day.date } })
                    }
                  />
                </View>
              ) : null}
              {day.meal && isToday ? (
                <View style={{ flexGrow: 1, flexBasis: 140 }}>
                  <CookedButton meal={day.meal} />
                </View>
              ) : null}
            </View>
          </View>
        </View>
      </Card>
    </View>
  );
}

/** To buy, Update kitchen, Saved recipes: the three places Home sends you most. */
function QuickTiles() {
  const t = useTheme();
  const list = useList();
  const toBuy = list.data?.items.filter((item) => !item.checked).length;
  return (
    <View style={{ flexDirection: 'row', gap: t.space.sm }}>
      <Tile
        icon={ShoppingBasket}
        tint="list"
        title={toBuy === undefined ? 'Shopping' : toBuy === 0 ? 'Nothing' : `${toBuy} to buy`}
        hint={toBuy === 0 ? 'to buy' : 'Shopping list'}
        href="/lists"
      />
      <Tile icon={Refrigerator} tint="kitchen" title="Update" hint="kitchen" href="/kitchen" />
      <Tile
        icon={Bookmark}
        tint="recipes"
        title="Saved"
        hint="recipes"
        href={{ pathname: '/recipes/all', params: { favourites: '1' } }}
      />
    </View>
  );
}

function Tile({
  icon,
  tint,
  title,
  hint,
  href,
}: {
  icon: LucideIcon;
  tint: keyof typeof sectionTints;
  title: string;
  hint: string;
  href: Href;
}) {
  const t = useTheme();
  return (
    <PressableScale
      accessibilityRole="link"
      accessibilityLabel={`${title} ${hint}`}
      onPress={() => router.push(href)}
      style={{
        flex: 1,
        minWidth: 0,
        gap: 2,
        padding: t.space.md,
        borderRadius: t.radius.lg,
        backgroundColor: t.colors.surface,
        boxShadow: t.shadow.card,
      }}
    >
      <View
        style={{
          width: 32,
          height: 32,
          borderRadius: 10,
          marginBottom: t.space.sm,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: sectionTints[tint].bg,
        }}
      >
        <Icon icon={icon} size={18} color={sectionTints[tint].fg} />
      </View>
      <Text variant="label" numberOfLines={1} style={{ fontVariant: ['tabular-nums'] }}>
        {title}
      </Text>
      <Text variant="caption" muted numberOfLines={1}>
        {hint}
      </Text>
    </PressableScale>
  );
}

/** Two Kitchen Matches, the same as Recipes › Recommended. Optional: hidden on errors. */
function RecipeIdeas() {
  const t = useTheme();
  const ideas = useDinnerIdeas(KITCHEN_FIRST, 'all', 2);
  if (ideas.isError) return null;
  return (
    <View style={{ gap: t.space.sm }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <View style={{ flex: 1 }}>
          <Text
            variant="heading"
            role="heading"
            aria-level={2}
            style={{ color: t.colors.onBackground, fontSize: 17, lineHeight: 22 }}
          >
            Recipe ideas for you
          </Text>
          <Text variant="caption" style={{ color: t.colors.onBackgroundMuted }}>
            Quick and easy ideas based on your Kitchen.
          </Text>
        </View>
        <PressableScale
          accessibilityRole="link"
          accessibilityLabel="See all recipes"
          onPress={() => router.push('/recipes')}
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            gap: 2,
            minHeight: t.touchTarget,
            paddingLeft: t.space.sm,
          }}
        >
          <Text variant="label" style={{ color: t.colors.onBackground }}>
            See all
          </Text>
          <Icon icon={ChevronRight} size={16} color={t.colors.onBackground} strong />
        </PressableScale>
      </View>
      {ideas.isPending ? <Loading /> : null}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}>
        {ideas.data?.map((idea) => (
          <IdeaTile key={idea.id} idea={idea} path="/recipe/[id]" />
        ))}
      </View>
    </View>
  );
}
