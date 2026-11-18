import { router } from 'expo-router';
import { CalendarDays, ChefHat, Settings } from 'lucide-react-native';
import { useState } from 'react';
import { View } from 'react-native';

import { AvatarStack } from '@/components/Avatar';
import { Hero, HeroLabel } from '@/components/Hero';
import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { Button, ErrorText, Highlight } from '@/components/ui';
import { PlanSheet, startPlan } from '@/features/mealPlan/PlanSheet';
import { addDays, mondayOf } from '@/features/mealPlan/week';
import type { MeOut } from '@/lib/api/client';
import { useHousehold } from '@/lib/api/households';
import { useMealPlan } from '@/lib/api/mealPlan';
import { useTheme } from '@/theme/useTheme';

import { AskSweep } from './AskSweep';
import { homeCta, needsNextWeekForCta } from './today';

/**
 * Home's hero (ADR 0026): always "What's cooking today?", Ask Sweep, and two buttons.
 * Tonight's dinner and the week sit in cards below it, so the top never changes shape.
 * The lime button follows the plan (`homeCta`): Plan my week, Edit my week, then from
 * Friday Plan next week. It's never greyed out.
 */
export function TodayHero({ me }: { me: MeOut }) {
  const t = useTheme();
  const week = useMealPlan(null);
  const today = week.data?.today;
  const next = useMealPlan(
    today ? addDays(mondayOf(today), 7) : null,
    today !== undefined && needsNextWeekForCta(today),
  );
  const [planning, setPlanning] = useState(false);

  const cta = week.data
    ? homeCta({ today: week.data.today, thisWeek: week.data.meals, nextWeek: next.data?.meals })
    : null;

  return (
    <Hero
      top={<HouseholdRow me={me} />}
      title={
        <>
          What&apos;s <Highlight>cooking</Highlight> today?
        </>
      }
      subtitle="Your meals, kitchen and lists in one place."
    >
      <AskSweep />
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}>
        <View style={{ flexGrow: 1, flexBasis: 150 }}>
          <Button
            title={cta?.label ?? 'Plan my week'}
            icon={CalendarDays}
            disabled={!cta}
            onPress={() => setPlanning(true)}
          />
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
      {planning && cta ? (
        <PlanSheet
          title={cta.label}
          week={cta.week}
          onClose={() => setPlanning(false)}
          onPick={startPlan}
        />
      ) : null}
    </Hero>
  );
}

/** Who's in the Household, and the cog: Household settings live behind it now. */
function HouseholdRow({ me }: { me: MeOut }) {
  const t = useTheme();
  const household = useHousehold(true);
  const open = () => router.push('/household');
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.md }}>
      <PressableScale
        accessibilityRole="link"
        accessibilityLabel={`${me.household.name}: Household settings`}
        onPress={open}
        style={{ flex: 1, flexDirection: 'row', alignItems: 'center', gap: t.space.md }}
      >
        <AvatarStack members={household.data?.members ?? [me.member]} size={40} />
        <View style={{ flex: 1 }}>
          <HeroLabel label="Household" value={me.household.name} />
        </View>
      </PressableScale>
      <PressableScale
        accessibilityRole="link"
        accessibilityLabel="Household settings"
        onPress={open}
        style={{
          width: t.touchTarget,
          height: t.touchTarget,
          borderRadius: t.radius.pill,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: t.colors.heroField,
          boxShadow: t.shadow.card,
        }}
      >
        <Icon icon={Settings} color={t.colors.onHero} />
      </PressableScale>
    </View>
  );
}
