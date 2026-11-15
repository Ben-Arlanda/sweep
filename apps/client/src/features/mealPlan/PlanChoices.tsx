import { randomUUID } from 'expo-crypto';
import { View } from 'react-native';

import { Button, Text } from '@/components/ui';
import type { PlanMode } from '@/features/chat/starters';
import { usePreferences, useSavePlanWeekdays } from '@/lib/api/diet';
import { useTheme } from '@/theme/useTheme';

import { nextWeekdays } from './week';

/**
 * The two kinds of plan, under a week strip with days ticked (ADR 0015). Used by the
 * "Plan my week" sheet and straight under the Meal Plan screen's strip.
 *
 * Choosing one also remembers the Household's usual days. Only days the Member could
 * choose change that pattern (see `nextWeekdays`). If saving fails the plan still
 * starts; the sheet just opens on the old days next time.
 */
export function PlanChoices({
  monday,
  today,
  planned,
  picked,
  onPick,
}: {
  monday: string;
  today: string;
  /** Days in this week that already have a Planned Meal. */
  planned: string[];
  picked: string[];
  onPick: (mode: PlanMode, days: string[]) => void;
}) {
  const t = useTheme();
  const prefs = usePreferences();
  const saveWeekdays = useSavePlanWeekdays();
  const count = `${picked.length} ${picked.length === 1 ? 'day' : 'days'}`;

  function choose(mode: PlanMode) {
    if (picked.length === 0) return;
    if (prefs.data) {
      const before = prefs.data.plan_weekdays;
      const weekdays = nextWeekdays({ monday, today, planned, before, picked });
      saveWeekdays.mutate({ key: randomUUID(), weekdays });
    }
    onPick(mode, picked);
  }

  return (
    <View style={{ gap: t.space.sm }}>
      <Button
        title="Cook from my Kitchen"
        accessibilityLabel={`Cook from my Kitchen, ${count}`}
        disabled={picked.length === 0}
        onPress={() => choose('kitchen')}
      />
      <Text variant="caption" muted>
        Uses what you have, so there&apos;s less to buy.
      </Text>
      <Button
        title="New recipes to shop for"
        accessibilityLabel={`New recipes to shop for, ${count}`}
        variant="secondary"
        disabled={picked.length === 0}
        onPress={() => choose('new')}
      />
      <Text variant="caption" muted>
        A fresh week. Sweep builds the Shopping List.
      </Text>
    </View>
  );
}
