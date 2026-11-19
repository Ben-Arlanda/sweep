import { Image } from 'expo-image';
import { router } from 'expo-router';
import { CalendarDays, ChefHat, CircleUserRound, type LucideIcon } from 'lucide-react-native';
import { useState } from 'react';
import { View } from 'react-native';

import { Hero } from '@/components/Hero';
import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { ErrorText, Text } from '@/components/ui';
import { PlanSheet, startPlan } from '@/features/mealPlan/PlanSheet';
import { addDays, mondayOf } from '@/features/mealPlan/week';
import type { MeOut } from '@/lib/api/client';
import { mealTap, useMealPlan, useMealPlanActions } from '@/lib/api/mealPlan';
import { sectionTints } from '@/theme/tokens';
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

/**
 * Home's header: the logo and account button, a hidden page heading, Ask Sweep, and
 * buttons for Just tonight and planning the week. Tonight's dinner and the week sit in
 * cards below it, so the top never changes shape.
 */
export function TodayHero({ me, flow }: { me: MeOut; flow: PlanFlow }) {
  const t = useTheme();
  const { cta } = flow;
  return (
    <Hero top={<LogoRow />}>
      {/* No visible greeting; screen readers still get a heading for the page. */}
      <Text accessibilityRole="header" aria-level={1} style={hidden}>
        {`Home, ${me.household.name}`}
      </Text>
      <AskSweep />
      <View style={{ flexDirection: 'row', gap: t.space.sm }}>
        <QuickAction
          icon={ChefHat}
          tint="recipes"
          label="Just tonight"
          onPress={() => router.push('/tonight')}
        />
        {/* Edit plan lives on the meal plan card; this button is for planning a week. */}
        {cta && cta.label !== 'Edit plan' ? (
          <QuickAction icon={CalendarDays} tint="plan" label={cta.label} onPress={flow.plan} />
        ) : null}
      </View>
      <ErrorText message={flow.error} />
      {flow.sheets}
    </Hero>
  );
}

/** A big quick action under Ask Sweep: a white card with a tinted icon tile, never lime. */
function QuickAction({
  icon,
  tint,
  label,
  onPress,
}: {
  icon: LucideIcon;
  tint: keyof typeof sectionTints;
  label: string;
  onPress: () => void;
}) {
  const t = useTheme();
  return (
    <PressableScale
      accessibilityRole="button"
      onPress={onPress}
      style={{
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        minHeight: 52,
        paddingHorizontal: 8,
        borderRadius: t.radius.lg,
        backgroundColor: t.colors.surface,
        boxShadow: t.shadow.card,
      }}
    >
      <View
        style={{
          width: 32,
          height: 32,
          borderRadius: 9,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: sectionTints[tint].bg,
        }}
      >
        <Icon icon={icon} size={18} color={sectionTints[tint].fg} />
      </View>
      <Text variant="label" style={{ flexShrink: 1, fontSize: 14, lineHeight: 18 }}>
        {label}
      </Text>
    </PressableScale>
  );
}

/** Shown to screen readers only: a 1pt box that is fully transparent. */
const hidden = {
  position: 'absolute',
  width: 1,
  height: 1,
  overflow: 'hidden',
  opacity: 0,
} as const;

/** The Sweep logo, and the person button for Household settings. */
function LogoRow() {
  const t = useTheme();
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        minHeight: t.touchTarget,
        // A hairline under the row, out to the screen edges (past the hero's padding).
        marginHorizontal: -t.space.lg,
        paddingHorizontal: t.space.lg,
        paddingBottom: t.space.sm,
        borderBottomWidth: 1,
        borderBottomColor: t.colors.border,
      }}
    >
      <Image
        aria-hidden
        source={require('../../../assets/images/sweep-logo.png')}
        style={{ width: 32, height: 32 }}
        contentFit="contain"
      />
      <PressableScale
        accessibilityRole="link"
        accessibilityLabel="Household settings"
        onPress={() => router.push('/household')}
        style={{
          width: t.touchTarget,
          height: t.touchTarget,
          borderRadius: t.radius.md,
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Icon icon={CircleUserRound} size={26} color={t.colors.text} />
      </PressableScale>
    </View>
  );
}
