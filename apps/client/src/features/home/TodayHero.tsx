import { Image } from 'expo-image';
import { router } from 'expo-router';
import { Settings } from 'lucide-react-native';
import { useState } from 'react';
import { View } from 'react-native';
import { useReducedMotion } from 'react-native-reanimated';

import { Hero } from '@/components/Hero';
import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { ErrorText, Text } from '@/components/ui';
import { PlanSheet, startPlan } from '@/features/mealPlan/PlanSheet';
import { addDays, mondayOf } from '@/features/mealPlan/week';
import type { MeOut } from '@/lib/api/client';
import { mealTap, useMealPlan, useMealPlanActions } from '@/lib/api/mealPlan';
import { useTheme } from '@/theme/useTheme';

import { AskSweep } from './AskSweep';
import { EditPlanSheet } from './EditPlanSheet';
import { homeCta, needsNextWeekForCta } from './today';

/**
 * Home's plan button and its sheets (ADR 0026). `cta` follows the plan: Plan my week, Edit
 * plan, then from Friday Plan next week. Edit plan opens a menu: Edit this week (the Plan
 * tab) or Start fresh (clear from today, after asking, then plan again). The hero shows
 * the Plan chips; Edit plan sits on the meal plan card, so both share this one flow.
 */
export function usePlanFlow() {
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

  const sheets = (
    <>
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
    </>
  );

  return {
    cta,
    /** Plan my week / Plan next week: straight to the plan sheet. */
    plan: () => setOpen('plan'),
    /** Edit plan: the Edit this week / Start fresh menu. */
    edit: () => setOpen('menu'),
    error: week.error?.message ?? remove.error?.message,
    sheets,
  };
}

export type PlanFlow = ReturnType<typeof usePlanFlow>;

/** "Good morning" before noon, "Good afternoon" until 5, then "Good evening". */
export function greeting(hour: number): string {
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

/**
 * Home's header: the chef and Household row, the date and a greeting, Ask Sweep, and
 * chips for Just tonight and planning the week. Tonight's dinner and the week sit in
 * cards below it, so the top never changes shape.
 */
export function TodayHero({ me, flow }: { me: MeOut; flow: PlanFlow }) {
  const t = useTheme();
  const now = new Date();
  const { cta } = flow;
  return (
    <Hero top={<HouseholdRow me={me} />}>
      <View style={{ gap: t.space.xs }}>
        <Text variant="caption" muted>
          {now.toLocaleDateString('en-AU', { weekday: 'long', day: 'numeric', month: 'long' })}
        </Text>
        <Text variant="title" accessibilityRole="header">
          {greeting(now.getHours())}
        </Text>
      </View>
      <AskSweep />
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}>
        <Chip label="Just tonight" onPress={() => router.push('/tonight')} />
        {/* Edit plan lives on the meal plan card; the chip is for planning a week. */}
        {cta && cta.label !== 'Edit plan' ? <Chip label={cta.label} onPress={flow.plan} /> : null}
      </View>
      <ErrorText message={flow.error} />
      {flow.sheets}
    </Hero>
  );
}

/** A quick action chip under Ask Sweep: white with a hairline, never lime. */
function Chip({ label, onPress }: { label: string; onPress: () => void }) {
  const t = useTheme();
  return (
    <PressableScale
      accessibilityRole="button"
      onPress={onPress}
      style={{ minHeight: t.touchTarget, justifyContent: 'center' }}
    >
      <View
        style={{
          minHeight: 36,
          paddingHorizontal: t.space.md,
          borderRadius: t.radius.pill,
          borderWidth: 1,
          borderColor: t.colors.border,
          backgroundColor: t.colors.surface,
          justifyContent: 'center',
        }}
      >
        <Text style={{ fontFamily: t.fonts.medium, fontSize: 14, lineHeight: 18 }}>{label}</Text>
      </View>
    </PressableScale>
  );
}

/** The sweep chef, the Household's name, and the cog for Household settings. */
function HouseholdRow({ me }: { me: MeOut }) {
  const t = useTheme();
  const reduceMotion = useReducedMotion();
  const open = () => router.push('/household');
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.sm }}>
      <PressableScale
        accessibilityRole="link"
        accessibilityLabel={`${me.household.name}: Household settings`}
        onPress={open}
        style={{
          flex: 1,
          flexDirection: 'row',
          alignItems: 'center',
          gap: t.space.sm + 2,
          minHeight: t.touchTarget,
        }}
      >
        <Image
          aria-hidden
          source={require('../../../assets/images/chef-blink.webp')}
          style={{ width: 34, height: 34 }}
          contentFit="contain"
          autoplay={!reduceMotion}
        />
        <Text style={{ flex: 1, fontFamily: t.fonts.medium }}>{me.household.name}</Text>
      </PressableScale>
      <PressableScale
        accessibilityRole="link"
        accessibilityLabel="Household settings"
        onPress={open}
        style={{
          width: t.touchTarget,
          height: t.touchTarget,
          borderRadius: t.radius.md,
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Icon icon={Settings} color={t.colors.text} />
      </PressableScale>
    </View>
  );
}
