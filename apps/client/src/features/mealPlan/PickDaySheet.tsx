import { CalendarDays } from 'lucide-react-native';
import { useState } from 'react';
import { View } from 'react-native';

import { Sheet } from '@/components/Sheet';
import { Button, ErrorText, Text } from '@/components/ui';
import { formatDay } from '@/features/chat/format';
import { useMealPlan } from '@/lib/api/mealPlan';
import { useTheme } from '@/theme/useTheme';

import { addDays, mondayOf } from './week';
import { WeekStrip, type StripMeal } from './WeekStrip';

/**
 * "Another day" for one recipe: this week and next as day strips (a plan covers today
 * and the next 13 days). ✓ marks a day already planned; picking it replaces that meal.
 */
export function PickDaySheet({
  today,
  busy,
  error,
  onPick,
  onClose,
}: {
  today: string;
  busy: boolean;
  error: string | null;
  onPick: (date: string) => void;
  onClose: () => void;
}) {
  const t = useTheme();
  const thisWeek = mondayOf(today);
  const nextWeek = addDays(thisWeek, 7);
  const now = useMealPlan(thisWeek);
  const next = useMealPlan(nextWeek);
  const [picked, setPicked] = useState<string | null>(null);
  const meals: Record<string, StripMeal> = Object.fromEntries(
    [...(now.data?.meals ?? []), ...(next.data?.meals ?? [])].map((m) => [
      m.date,
      { title: m.title, cooked: m.cooked_at !== null },
    ]),
  );
  const toggle = (date: string) => setPicked((p) => (p === date ? null : date));
  return (
    <Sheet label="Pick a day" title="Which day?" onClose={onClose}>
      <View style={{ gap: t.space.md }}>
        <Text variant="label">This week</Text>
        <WeekStrip
          monday={thisWeek}
          today={today}
          meals={meals}
          picked={picked ? [picked] : []}
          onToggle={toggle}
        />
        <Text variant="label">Next week</Text>
        <WeekStrip
          monday={nextWeek}
          today={today}
          meals={meals}
          picked={picked ? [picked] : []}
          onToggle={toggle}
        />
        <Text variant="caption" muted accessibilityLiveRegion="polite">
          {picked && meals[picked]
            ? `Replaces ${meals[picked].title}.`
            : '✓ already planned: pick it to replace that dinner.'}
        </Text>
        <ErrorText message={error} />
        <Button
          title={picked ? `Plan for ${formatDay(picked)}` : 'Pick a day'}
          icon={CalendarDays}
          disabled={!picked}
          loading={busy}
          onPress={() => picked && onPick(picked)}
        />
      </View>
    </Sheet>
  );
}
