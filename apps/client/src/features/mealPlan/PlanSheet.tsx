import { useState } from 'react';
import { ActivityIndicator, Pressable, View } from 'react-native';

import { ChoiceChips } from '@/components/ChoiceChips';
import { Sheet } from '@/components/Sheet';
import { Button, ErrorText, Text } from '@/components/ui';
import { formatDay } from '@/features/chat/format';
import type { PlanMode, PlanTweak } from '@/features/chat/starters';
import { usePreferences } from '@/lib/api/diet';
import { useMealPlan } from '@/lib/api/mealPlan';
import { useTheme } from '@/theme/useTheme';

import { PlanChoices } from './PlanChoices';
import { addDays, mondayOf, pickDays, planWeekFor } from './week';
import { WeekStrip, type StripMeal } from './WeekStrip';

const TWEAKS: { label: string; value: PlanTweak }[] = [
  { label: 'Healthy', value: 'healthy' },
  { label: 'Under 30 min', value: 'quick' },
  { label: 'Vegetarian', value: 'vegetarian' },
];
const WEEKNIGHTS = [1, 2, 3, 4, 5];
const EVERY_DAY = [1, 2, 3, 4, 5, 6, 7];

/**
 * "Plan my week" (slice 5d, ADR 0015): which days, then what kind of plan.
 *
 * Starts from the Household's usual weekdays in the week it opens on (this week, or
 * next week at the weekend), leaving out past days and days already planned. "How many
 * days" is just how many are ticked; the chips are shortcuts.
 *
 * Picking a kind of plan (`PlanChoices`) remembers the usual days, then hands the mode
 * and days to `onPick`, which starts the chat.
 */
export function PlanSheet({
  onClose,
  onPick,
  week: openOn,
}: {
  onClose: () => void;
  onPick: (mode: PlanMode, days: string[], tweaks: PlanTweak[]) => void;
  /** A Monday to open on, e.g. the week the Meal Plan screen shows. */
  week?: string;
}) {
  const t = useTheme();
  const today = useMealPlan(null).data?.today;
  const prefs = usePreferences();

  const [chosenWeek, setChosenWeek] = useState<string | null>(openOn ?? null);
  const monday = chosenWeek ?? (today ? planWeekFor(today) : null);
  const week = useMealPlan(monday);
  // null = not touched yet, so it follows the usual weekdays once they've loaded.
  const [touched, setTouched] = useState<string[] | null>(null);
  // "This week" chips (slice 6e): soft tastes for this plan only, never saved.
  const [tweaks, setTweaks] = useState<PlanTweak[]>([]);

  const ready = today && monday && week.data && prefs.data;
  const failed = week.error ?? prefs.error;

  return (
    <Sheet label="Plan your week" title="Plan your week" onClose={onClose}>
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
    const same = (a: string[], b: string[]) => a.join() === b.join();
    const shortcut = same(picked, daysFor(WEEKNIGHTS))
      ? 'weeknights'
      : same(picked, daysFor(EVERY_DAY))
        ? 'every'
        : null;
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

    const count = `${picked.length} ${picked.length === 1 ? 'day' : 'days'}`;
    return (
      <View style={{ gap: t.space.md }}>
        <Text muted>Pick the days to plan. Sweep plans one dinner for each.</Text>

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

        <ChoiceChips
          label="Quick pick"
          value={shortcut}
          options={[
            { label: 'Weeknights', value: 'weeknights' as const },
            { label: 'Every day', value: 'every' as const },
          ]}
          onChange={(v) => setTouched(daysFor(v === 'weeknights' ? WEEKNIGHTS : EVERY_DAY))}
        />

        <WeekStrip monday={monday} today={today} meals={meals} picked={picked} onToggle={toggle} />
        <Text variant="caption" muted accessibilityLiveRegion="polite">
          {picked.length === 0
            ? 'Pick at least one day.'
            : `${count} · ✓ already planned (tick one to replace it)`}
        </Text>

        <View style={{ gap: t.space.xs }}>
          <Text variant="label">This week (optional)</Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}>
            {TWEAKS.map((tweak) => {
              const on = tweaks.includes(tweak.value);
              return (
                <Pressable
                  key={tweak.value}
                  accessibilityRole="checkbox"
                  aria-checked={on}
                  accessibilityLabel={tweak.label}
                  onPress={() =>
                    setTweaks(
                      on ? tweaks.filter((v) => v !== tweak.value) : [...tweaks, tweak.value],
                    )
                  }
                  style={{
                    minHeight: t.touchTarget,
                    justifyContent: 'center',
                    paddingHorizontal: t.space.md,
                    borderRadius: t.radius.pill,
                    borderWidth: 1,
                    borderColor: on ? t.colors.inverse : t.colors.border,
                    backgroundColor: on ? t.colors.inverse : t.colors.surface,
                  }}
                >
                  <Text variant="label" style={{ color: on ? t.colors.onInverse : t.colors.text }}>
                    {tweak.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </View>

        <PlanChoices
          monday={monday}
          today={today}
          planned={planned}
          picked={picked}
          onPick={(mode, days) => {
            onClose();
            onPick(mode, days, tweaks);
          }}
        />
      </View>
    );
  }
}
