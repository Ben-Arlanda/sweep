import { randomUUID } from 'expo-crypto';
import { router } from 'expo-router';
import {
  Heart,
  Leaf,
  Refrigerator,
  ShoppingCart,
  Sparkles,
  Zap,
  type LucideIcon,
} from 'lucide-react-native';
import { useState, type ReactNode } from 'react';
import { ActivityIndicator, Pressable, View } from 'react-native';

import { Icon } from '@/components/Icon';
import { Sheet } from '@/components/Sheet';
import { Button, ErrorText, Text } from '@/components/ui';
import { formatDay } from '@/features/chat/format';
import { requestPlan, type PlanMode, type PlanTweak } from '@/features/chat/starters';
import { usePreferences, useSavePlanWeekdays } from '@/lib/api/diet';
import { useMealPlan } from '@/lib/api/mealPlan';
import { useTheme } from '@/theme/useTheme';

import { addDays, mondayOf, nextWeekdays, pickDays, planWeekFor } from './week';
import { WeekStrip, type StripMeal } from './WeekStrip';

const TWEAKS: { label: string; value: PlanTweak; icon: LucideIcon }[] = [
  { label: 'Healthy', value: 'healthy', icon: Heart },
  { label: 'Under 30 min', value: 'quick', icon: Zap },
  { label: 'Vegetarian', value: 'vegetarian', icon: Leaf },
];

/** What every Plan my week sheet does with its answer: ask Sweep, then show the plan. */
export function startPlan(mode: PlanMode, days: string[], tweaks: PlanTweak[]) {
  requestPlan(mode, days, tweaks);
  router.push('/plan-week');
}

/**
 * "Plan my week" (slice 5d, ADR 0015): which days, then what kind of plan.
 *
 * Starts from the Household's usual weekdays in the week it opens on (this week, or
 * next week at the weekend), leaving out past days and days already planned. "How many
 * days" is just how many are ticked: tap a day to add or remove it.
 *
 * The canvas layout (slice 6e): days, Build my plan using, This week chips and
 * one Plan button. Planning remembers the usual days, then hands the mode
 * and days to `onPick`, which opens the plan screens.
 */
export function PlanSheet({
  onClose,
  onPick,
  week: openOn,
  title = 'Plan my week',
  days: startDays,
}: {
  onClose: () => void;
  onPick: (mode: PlanMode, days: string[], tweaks: PlanTweak[]) => void;
  /** A Monday to open on, e.g. the week the Plan tab shows. */
  week?: string;
  /** e.g. "Plan next week" from Home, or "Edit my week" from the Plan tab. */
  title?: string;
  /** Days to start ticked instead of the usual weekdays. */
  days?: string[];
}) {
  const t = useTheme();
  const today = useMealPlan(null).data?.today;
  const prefs = usePreferences();

  const [chosenWeek, setChosenWeek] = useState<string | null>(openOn ?? null);
  const monday = chosenWeek ?? (today ? planWeekFor(today) : null);
  const week = useMealPlan(monday);
  // null = not touched yet, so it follows the usual weekdays once they've loaded.
  const [touched, setTouched] = useState<string[] | null>(startDays ?? null);
  // "This week" chips (slice 6e): soft tastes for this plan only, never saved.
  const [tweaks, setTweaks] = useState<PlanTweak[]>([]);
  const [mode, setMode] = useState<PlanMode>('kitchen');
  const saveWeekdays = useSavePlanWeekdays();

  const ready = today && monday && week.data && prefs.data;
  const failed = week.error ?? prefs.error;

  return (
    <Sheet label={title} title={title} onClose={onClose}>
      {!ready ? (
        failed ? (
          <ErrorText message={failed.message} />
        ) : (
          <ActivityIndicator color={t.colors.textMuted} />
        )
      ) : (
        body()
      )}
    </Sheet>
  );

  // A plain function, not a component: a component declared in here would be a new
  // type every render, so React would remount it and keyboard focus would jump away
  // after every tap.
  function body() {
    if (!today || !monday || !week.data || !prefs.data) return null;
    const planned = week.data.meals.map((m) => m.date);
    const daysFor = (weekdays: number[]) => pickDays({ monday, weekdays, today, planned });
    const picked = touched ?? daysFor(prefs.data.plan_weekdays);
    const meals: Record<string, StripMeal> = Object.fromEntries(
      week.data.meals.map((m) => [m.date, { title: m.title, cooked: m.cooked_at !== null }]),
    );

    // Only this week and next: a plan covers today and the next 13 days.
    const first = mondayOf(today);
    const canBack = monday > first;
    const canForward = monday < addDays(first, 7);

    function moveWeek(to: string) {
      setChosenWeek(to);
      setTouched(null); // the new week starts from the usual days again
    }

    function toggle(date: string) {
      setTouched(
        picked.includes(date) ? picked.filter((d) => d !== date) : [...picked, date].sort(),
      );
    }

    const count = `${picked.length} ${picked.length === 1 ? 'dinner' : 'dinners'}`;

    function generate() {
      if (!today || !monday || !prefs.data || picked.length === 0) return;
      // Remember the usual days (only ones the Member could choose change the pattern).
      const weekdays = nextWeekdays({
        monday,
        today,
        planned,
        before: prefs.data.plan_weekdays,
        picked,
      });
      saveWeekdays.mutate({ key: randomUUID(), weekdays });
      onClose();
      onPick(mode, picked, tweaks);
    }

    return (
      <View style={{ gap: t.space.lg }}>
        <Text muted>Choose the days and how Sweep should plan your meals.</Text>

        <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.sm }}>
          <Button
            title="‹"
            accessibilityLabel="This week"
            variant="secondary"
            compact
            disabled={!canBack}
            onPress={() => moveWeek(first)}
          />
          <Text variant="label" style={{ flex: 1, textAlign: 'center' }}>
            {formatDay(monday)} – {formatDay(addDays(monday, 6))}
          </Text>
          <Button
            title="›"
            accessibilityLabel="Next week"
            variant="secondary"
            compact
            disabled={!canForward}
            onPress={() => moveWeek(addDays(first, 7))}
          />
        </View>

        <WeekStrip monday={monday} today={today} meals={meals} picked={picked} onToggle={toggle} />

        <Group label="Build my plan using">
          <Option
            role="radio"
            icon={Refrigerator}
            title="What's in my Kitchen"
            detail="Use what you have, buy less"
            selected={mode === 'kitchen'}
            onPress={() => setMode('kitchen')}
          />
          <Option
            role="radio"
            icon={ShoppingCart}
            title="New recipes"
            detail="A fresh week, Sweep builds the list"
            selected={mode === 'new'}
            onPress={() => setMode('new')}
          />
        </Group>

        <Group label="This week (optional)">
          <View style={{ flexDirection: 'row', gap: t.space.sm }}>
            {TWEAKS.map((tweak) => (
              <Option
                key={tweak.value}
                role="checkbox"
                icon={tweak.icon}
                title={tweak.label}
                compact
                selected={tweaks.includes(tweak.value)}
                onPress={() =>
                  setTweaks(
                    tweaks.includes(tweak.value)
                      ? tweaks.filter((v) => v !== tweak.value)
                      : [...tweaks, tweak.value],
                  )
                }
              />
            ))}
          </View>
        </Group>

        <Button
          title={picked.length ? `Plan ${count}` : 'Pick some days'}
          icon={Sparkles}
          disabled={picked.length === 0}
          onPress={generate}
        />
      </View>
    );
  }
}

function Group({ label, children }: { label: string; children: ReactNode }) {
  const t = useTheme();
  // Checkboxes in "This week" aren't a radio group: only name the group then.
  const radio = !label.startsWith('This week');
  return (
    <View
      accessibilityRole={radio ? 'radiogroup' : undefined}
      accessibilityLabel={label}
      style={{ gap: t.space.sm }}
    >
      <Text variant="label">{label}</Text>
      {children}
    </View>
  );
}

/** A choice card from the canvas: a radio (one of a group) or a checkbox (any number). */
function Option({
  role,
  title,
  detail,
  icon,
  selected,
  compact = false,
  onPress,
}: {
  role: 'radio' | 'checkbox';
  title: string;
  detail?: string;
  icon?: LucideIcon;
  selected: boolean;
  compact?: boolean;
  onPress: () => void;
}) {
  const t = useTheme();
  const fg = compact && selected ? t.colors.onSelected : t.colors.text;
  return (
    <Pressable
      accessibilityRole={role}
      aria-checked={selected}
      accessibilityState={{ checked: selected }}
      accessibilityLabel={detail ? `${title}, ${detail}` : title}
      onPress={onPress}
      style={{
        flex: 1,
        minHeight: compact ? 64 : 56,
        flexDirection: compact ? 'column' : 'row',
        alignItems: 'center',
        justifyContent: compact ? 'center' : 'flex-start',
        gap: compact ? 4 : t.space.md,
        paddingHorizontal: compact ? t.space.xs : t.space.md,
        paddingVertical: t.space.sm,
        borderRadius: compact ? t.radius.md : t.radius.lg,
        // Selected: a 2pt navy edge (and a filled radio), never colour alone.
        borderWidth: selected && !compact ? 2 : 1,
        borderColor: selected ? t.colors.selected : t.colors.border,
        backgroundColor: compact && selected ? t.colors.selected : t.colors.surface,
      }}
    >
      {icon ? <Icon icon={icon} size={compact ? 20 : 22} color={fg} /> : null}
      <View style={{ flexShrink: 1, alignItems: compact ? 'center' : 'flex-start' }}>
        <Text
          variant={compact ? 'caption' : 'label'}
          style={{ color: fg, textAlign: compact ? 'center' : 'left', fontWeight: '600' }}
        >
          {title}
        </Text>
        {detail ? (
          <Text variant="caption" muted>
            {detail}
          </Text>
        ) : null}
      </View>
      {compact ? null : (
        <View
          aria-hidden
          style={{
            marginLeft: 'auto',
            width: 20,
            height: 20,
            borderRadius: 10,
            borderWidth: selected ? 6 : 1.5,
            borderColor: selected ? t.colors.selected : t.colors.switchOff,
          }}
        />
      )}
    </Pressable>
  );
}
