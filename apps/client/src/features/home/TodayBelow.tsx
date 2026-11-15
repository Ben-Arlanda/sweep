import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Link, type Href } from 'expo-router';
import type { ReactNode } from 'react';
import { View } from 'react-native';

import { PressableScale } from '@/components/PressableScale';
import { ErrorText, Text } from '@/components/ui';
import { WeekStrip, type StripMeal } from '@/features/mealPlan/WeekStrip';
import { useList } from '@/lib/api/lists';
import { useMealPlan } from '@/lib/api/mealPlan';
import { useTheme } from '@/theme/useTheme';

/**
 * Under Home's hero (slice 6c): this week at a glance (a link to the Meal Plan) and how
 * much is on the Shopping List. Each only shows when it has something to say.
 */
export function TodayBelow() {
  const week = useMealPlan(null);
  const list = useList();
  const toBuy = list.data?.items.filter((item) => !item.checked).length ?? 0;
  const meals = week.data?.meals ?? [];

  return (
    <>
      {week.data && meals.length > 0 ? (
        <Row
          href="/meal-plan"
          label={`This week: ${meals.length} of 7 dinners planned. Open the Meal Plan`}
        >
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 8 }}>
            <Text variant="heading">This week</Text>
            <Text muted>{meals.length} of 7 planned ›</Text>
          </View>
          <WeekStrip
            monday={week.data.start}
            today={week.data.today}
            meals={Object.fromEntries(
              meals.map((m): [string, StripMeal] => [
                m.date,
                { title: m.title, cooked: m.cooked_at !== null },
              ]),
            )}
          />
        </Row>
      ) : null}

      {toBuy > 0 ? (
        <Row href="/lists" label={`${toBuy} to buy on the Shopping List`}>
          <ToBuy count={toBuy} />
        </Row>
      ) : null}

      <ErrorText message={list.error?.message} />
    </>
  );
}

function ToBuy({ count }: { count: number }) {
  const t = useTheme();
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.md }}>
      <View
        aria-hidden
        style={{
          width: 40,
          height: 40,
          borderRadius: t.radius.md,
          backgroundColor: t.tints.mint.bg,
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <MaterialCommunityIcons name="basket-outline" size={22} color={t.tints.mint.onPill} />
      </View>
      <View style={{ flex: 1 }}>
        <Text variant="heading">{count} to buy</Text>
        <Text muted>Shopping List</Text>
      </View>
      <MaterialCommunityIcons
        name="chevron-right"
        size={22}
        color={t.colors.textMuted}
        aria-hidden
      />
    </View>
  );
}

/** A tappable card: one link, named by `label` (its visible text is shorter). */
function Row({ href, label, children }: { href: Href; label: string; children: ReactNode }) {
  const t = useTheme();
  return (
    <Link href={href} asChild>
      <PressableScale
        accessibilityRole="link"
        accessibilityLabel={label}
        style={{
          backgroundColor: t.colors.surface,
          borderWidth: 1,
          borderColor: t.colors.border,
          borderRadius: t.radius.lg,
          padding: t.space.md,
          gap: t.space.sm,
          minHeight: 64,
          justifyContent: 'center',
        }}
      >
        {children}
      </PressableScale>
    </Link>
  );
}
