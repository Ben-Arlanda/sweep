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
import { useTheme } from '@/theme/useTheme';

import { hasPlan, homeState, usesLine } from './today';

/**
 * Under Home's hero (ADR 0026): tonight's card, or "Your meal plan" once the week is
 * planned; then three quick tiles and recipe ideas from the Kitchen.
 */
export function TodayBelow() {
  const week = useMealPlan(null);
  const data = week.data;
  return (
    <>
      {!data ? null : hasPlan(data.today, data.meals) ? (
        <MealPlanCard monday={data.start} today={data.today} meals={data.meals} />
      ) : (
        <TonightCard today={data.today} meals={data.meals} />
      )}
      <QuickTiles />
      <RecipeIdeas />
    </>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  const t = useTheme();
  return (
    <View
      style={{
        backgroundColor: t.colors.surface,
        borderRadius: t.radius.lg,
        padding: t.space.md,
        gap: t.space.md,
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
        title={isCooked ? 'Undo' : 'Cooked'}
        accessibilityLabel={
          isCooked ? `Undo cooked for ${meal.title}` : `Mark ${meal.title} as cooked`
        }
        variant={isCooked ? 'ghost' : 'dark'}
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
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.md }}>
          <View style={{ flex: 1, gap: 2 }}>
            <Text variant="caption" muted>
              Tonight
            </Text>
            <Text variant="heading" role="heading" aria-level={2}>
              No meal planned
            </Text>
            <Text variant="caption" muted>
              Get a dinner idea in seconds.
            </Text>
          </View>
          <ChefPicture />
        </View>
        <View>
          <Button
            title="Find dinner ideas"
            icon={Sparkles}
            variant="dark"
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

/** The new chef, winking (still when the phone asks for less motion). Decorative. */
function ChefPicture() {
  const reduceMotion = useReducedMotion();
  return (
    <Image
      aria-hidden
      source={require('../../../assets/images/chef-blink.webp')}
      style={{ width: 84, height: 84 }}
      contentFit="contain"
      autoplay={!reduceMotion}
    />
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
}: {
  monday: string;
  today: string;
  meals: PlannedMeal[];
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
    <Card>
      <PressableScale
        accessibilityRole="link"
        accessibilityLabel={`Your meal plan, ${weekRange(monday)}, ${meals.length} dinners. Open the Plan tab`}
        onPress={() => router.push('/meal-plan')}
        style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.md, minHeight: 44 }}
      >
        <Icon icon={CalendarDays} size={28} color={t.colors.text} />
        <View style={{ flex: 1 }}>
          <Text variant="heading" role="heading" aria-level={2}>
            Your meal plan
          </Text>
          <Text variant="caption" muted>
            {weekRange(monday)} · {meals.length} {meals.length === 1 ? 'dinner' : 'dinners'}
          </Text>
        </View>
        <Icon icon={ChevronRight} color={t.colors.text} strong />
      </PressableScale>

      <View accessibilityRole="tablist" style={{ flexDirection: 'row', gap: 4 }}>
        {days.map((d) => {
          const p = dayParts(d.date);
          const on = d.date === selected;
          return (
            <PressableScale
              key={d.date}
              accessibilityRole="tab"
              accessibilityState={{ selected: on }}
              accessibilityLabel={`${p.weekday} ${p.day}${d.date === today ? ', tonight' : ''}: ${d.meal ? d.meal.title : 'nothing planned'}`}
              onPress={() => setSelected(d.date)}
              style={{
                flex: 1,
                alignItems: 'center',
                gap: 4,
                paddingVertical: 6,
                borderRadius: t.radius.md,
                borderWidth: 1,
                borderColor: on ? t.colors.action : t.colors.border,
                backgroundColor: on ? t.colors.action : t.colors.surface,
              }}
            >
              <Text
                variant="caption"
                style={{ color: on ? t.colors.onAction : t.colors.text, fontWeight: '700' }}
              >
                {p.weekday}
              </Text>
              {d.meal ? (
                <RecipeArt title={d.meal.title} width={34} radius={17} emojiSize={18} />
              ) : (
                <View
                  style={{
                    width: 34,
                    height: 34,
                    borderRadius: 17,
                    backgroundColor: t.colors.border,
                  }}
                />
              )}
            </PressableScale>
          );
        })}
      </View>

      <View
        accessibilityLiveRegion="polite"
        style={{
          borderWidth: 1,
          borderColor: t.colors.border,
          borderRadius: t.radius.md,
          padding: t.space.sm,
          gap: t.space.sm,
        }}
      >
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.md }}>
          {day.meal ? (
            <RecipeArt title={day.meal.title} width={52} radius={14} emojiSize={26} />
          ) : null}
          <View style={{ flex: 1 }}>
            <Text variant="caption" style={{ color: t.colors.tabSelected, fontWeight: '700' }}>
              {eyebrow}
            </Text>
            <Text variant="label">{day.meal ? day.meal.title : 'Nothing planned'}</Text>
            {day.meal ? <MealMeta meal={day.meal} /> : null}
          </View>
        </View>
        {/* Each button gets an equal share of the row, so the margins either side match. */}
        <View style={{ flexDirection: 'row', gap: t.space.sm }}>
          {day.meal ? (
            <View style={{ flex: 1 }}>
              <Button
                title="See the recipe"
                variant="secondary"
                onPress={() => day.meal && router.push(`/recipe/${day.meal.recipe_id}`)}
              />
            </View>
          ) : canPick(day.date, today) ? (
            <View style={{ flex: 1 }}>
              <Button
                title="Add a dinner"
                variant="secondary"
                onPress={() => router.push({ pathname: '/tonight', params: { date: day.date } })}
              />
            </View>
          ) : null}
          {day.meal && isToday ? (
            <View style={{ flex: 1 }}>
              <CookedButton meal={day.meal} />
            </View>
          ) : null}
        </View>
      </View>
    </Card>
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
        title={toBuy === undefined ? 'Shopping' : toBuy === 0 ? 'Nothing' : `${toBuy} to buy`}
        hint={toBuy === 0 ? 'to buy' : 'Shopping list'}
        href="/lists"
      />
      <Tile icon={Refrigerator} title="Update" hint="kitchen" href="/kitchen" />
      <Tile
        icon={Bookmark}
        title="Saved"
        hint="recipes"
        href={{ pathname: '/recipes/all', params: { favourites: '1' } }}
      />
    </View>
  );
}

function Tile({
  icon,
  title,
  hint,
  href,
}: {
  icon: LucideIcon;
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
        alignItems: 'center',
        gap: 2,
        paddingVertical: t.space.md,
        paddingHorizontal: t.space.xs,
        borderRadius: t.radius.lg,
        backgroundColor: t.colors.surface,
        boxShadow: t.shadow.card,
      }}
    >
      <Icon icon={icon} size={26} color={t.colors.text} />
      <Text variant="label" style={{ textAlign: 'center', marginTop: 4 }}>
        {title}
      </Text>
      <Text variant="caption" muted style={{ textAlign: 'center' }}>
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
            style={{ color: t.colors.onBackground }}
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
