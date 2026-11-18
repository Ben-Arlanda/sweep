import { Image } from 'expo-image';
import { router } from 'expo-router';
import { CalendarDays, ChefHat, Pencil, Settings } from 'lucide-react-native';
import { useState } from 'react';
import { View } from 'react-native';
import { useReducedMotion } from 'react-native-reanimated';

import { Hero, HeroLabel } from '@/components/Hero';
import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { Button, ErrorText } from '@/components/ui';
import { PlanSheet, startPlan } from '@/features/mealPlan/PlanSheet';
import { addDays, mondayOf } from '@/features/mealPlan/week';
import type { MeOut } from '@/lib/api/client';
import { mealTap, useMealPlan, useMealPlanActions } from '@/lib/api/mealPlan';
import { useTheme } from '@/theme/useTheme';

import { AskSweep } from './AskSweep';
import { EditPlanSheet } from './EditPlanSheet';
import { homeCta, needsNextWeekForCta } from './today';

/**
 * Home's hero (ADR 0026): the chef and Household row, Ask Sweep, and two buttons.
 * Tonight's dinner and the week sit in cards below it, so the top never changes shape.
 * The lime button follows the plan (`homeCta`): Plan my week, Edit plan, then from
 * Friday Plan next week. It's never greyed out. Edit plan opens a menu: Edit this week
 * (the Plan tab) or Start fresh (clear from today, after asking, then plan again).
 */
export function TodayHero({ me }: { me: MeOut }) {
  const t = useTheme();
  const week = useMealPlan(null);
  const today = week.data?.today;
  const next = useMealPlan(
    today ? addDays(mondayOf(today), 7) : null,
    today !== undefined && needsNextWeekForCta(today),
  );
  // Which step is open: the Edit plan menu, the Start fresh question, or the plan sheet.
  const [open, setOpen] = useState<'menu' | 'confirm' | 'plan' | null>(null);
  const { remove } = useMealPlanActions();
  const [clearing, setClearing] = useState(false);
  // Start fresh plans the week it cleared, even if the button's week has moved on since.
  const [freshWeek, setFreshWeek] = useState<string | null>(null);

  const cta = week.data
    ? homeCta({ today: week.data.today, thisWeek: week.data.meals, nextWeek: next.data?.meals })
    : null;
  // Start fresh clears what can still change: uncooked dinners from today on.
  const clearable =
    week.data?.meals.filter((m) => m.cooked_at === null && m.date >= week.data.today) ?? [];

  async function startFresh() {
    setClearing(true);
    try {
      await Promise.all(clearable.map((m) => remove.mutateAsync(mealTap(m.id))));
      setFreshWeek(week.data?.start ?? null);
      setOpen('plan');
    } catch {
      setOpen(null); // remove.error says what went wrong
    } finally {
      setClearing(false);
    }
  }

  return (
    <Hero top={<HouseholdRow me={me} />}>
      <AskSweep />
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}>
        <View style={{ flexGrow: 1, flexBasis: 150 }}>
          <Button
            title={cta?.label ?? 'Plan my week'}
            icon={cta?.label === 'Edit plan' ? Pencil : CalendarDays}
            disabled={!cta}
            onPress={() => setOpen(cta?.label === 'Edit plan' ? 'menu' : 'plan')}
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
      <ErrorText message={week.error?.message ?? remove.error?.message} />
      {open === 'menu' ? (
        <EditPlanSheet
          onClose={() => setOpen(null)}
          onEdit={() => {
            setOpen(null);
            router.push('/meal-plan');
          }}
          onStartFresh={() => {
            if (clearable.length) return setOpen('confirm');
            setFreshWeek(week.data?.start ?? null); // nothing to clear: straight to planning
            setOpen('plan');
          }}
        />
      ) : null}
      {open === 'confirm' ? (
        <ConfirmDialog
          title="Start fresh?"
          message={`This removes the ${clearable.length} ${clearable.length === 1 ? 'dinner' : 'dinners'} planned from today on, then you plan the week again. Cooked dinners stay.`}
          confirm="Clear and plan again"
          busy={clearing}
          onConfirm={() => void startFresh()}
          onCancel={() => setOpen(null)}
        />
      ) : null}
      {open === 'plan' && cta ? (
        <PlanSheet
          title={!freshWeek && cta.label === 'Plan next week' ? 'Plan next week' : 'Plan my week'}
          week={freshWeek ?? cta.week}
          onClose={() => {
            setOpen(null);
            setFreshWeek(null);
          }}
          onPick={startPlan}
        />
      ) : null}
    </Hero>
  );
}

/** The sweep chef, the Household's name, and the cog for Household settings. */
function HouseholdRow({ me }: { me: MeOut }) {
  const t = useTheme();
  const reduceMotion = useReducedMotion();
  const open = () => router.push('/household');
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.md }}>
      <PressableScale
        accessibilityRole="link"
        accessibilityLabel={`${me.household.name}: Household settings`}
        onPress={open}
        style={{ flex: 1, flexDirection: 'row', alignItems: 'center', gap: t.space.md }}
      >
        <Image
          aria-hidden
          source={require('../../../assets/images/chef-blink.webp')}
          style={{ width: 52, height: 52 }}
          contentFit="contain"
          autoplay={!reduceMotion}
        />
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
        <Icon icon={Settings} color={t.colors.text} />
      </PressableScale>
    </View>
  );
}
