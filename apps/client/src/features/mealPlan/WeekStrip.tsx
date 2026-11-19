import { Pressable, View } from 'react-native';

import { Text } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

import { addDays, canPick } from './week';

const LETTERS = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
const NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export type StripMeal = { title: string; cooked: boolean };

/**
 * A Mon–Sun week as seven tiles (slice 5d). Two uses:
 * - on the Meal Plan screen, a glance: ✓ for a planned dinner, – for a free day;
 * - in the "Plan my week" sheet, a picker: pass `picked` and `onToggle`, and each tile
 *   becomes a checkbox. Past days can't be picked.
 *
 * Seven tiles share the row (each `flex: 1`), so it fits at 320px without wrapping.
 */
export function WeekStrip({
  monday,
  today,
  meals,
  picked,
  onToggle,
}: {
  monday: string;
  today: string;
  /** Planned Meals by date. */
  meals: Record<string, StripMeal>;
  picked?: string[];
  onToggle?: (date: string) => void;
}) {
  const t = useTheme();
  const picking = onToggle !== undefined;
  return (
    <View
      style={{ flexDirection: 'row', gap: 4 }}
      // As a glance it repeats the day rows under it, so screen readers skip it (they'd
      // hear "M, 9, T, 10…"). As a picker, every tile is a labelled checkbox.
      aria-hidden={!picking}
      importantForAccessibility={picking ? 'auto' : 'no-hide-descendants'}
    >
      {LETTERS.map((letter, i) => {
        const date = addDays(monday, i);
        const meal = meals[date];
        const isToday = date === today;
        const past = !canPick(date, today);
        const isPicked = picked?.includes(date) ?? false;

        // Picked: navy (selection). Planned: the quiet grey fill. Otherwise a white tile.
        const fill = isPicked ? t.colors.selected : meal ? t.colors.fill : t.colors.surface;
        const ink = isPicked ? t.colors.onSelected : t.colors.text;
        const mark = isPicked ? '●' : meal ? '✓' : '–';
        const dayName = `${NAMES[i]} ${Number(date.slice(8))}`;

        const tile = (
          <View
            style={{
              alignItems: 'center',
              gap: 2,
              paddingVertical: 8,
              borderRadius: t.radius.md,
              backgroundColor: fill,
              borderWidth: isToday ? 2 : 1,
              borderColor: isToday
                ? t.colors.selected
                : isPicked
                  ? t.colors.selected
                  : t.colors.border,
              minHeight: t.touchTarget + 28,
            }}
          >
            <Text variant="caption" style={{ color: past && !meal ? t.colors.textMuted : ink }}>
              {letter}
            </Text>
            <Text
              variant="label"
              style={{ color: past && !meal ? t.colors.textMuted : ink, fontSize: 17 }}
            >
              {Number(date.slice(8))}
            </Text>
            <Text variant="caption" style={{ color: ink }} aria-hidden>
              {mark}
            </Text>
          </View>
        );

        if (!onToggle) {
          return (
            <View key={date} style={{ flex: 1 }}>
              {tile}
            </View>
          );
        }
        return (
          <Pressable
            key={date}
            style={{ flex: 1 }}
            accessibilityRole="checkbox"
            accessibilityState={{ checked: isPicked, disabled: past }}
            aria-checked={isPicked}
            accessibilityLabel={`${dayName}${isToday ? ', today' : ''}${
              meal ? `, planned: ${meal.title}` : ''
            }`}
            disabled={past}
            onPress={() => onToggle(date)}
          >
            {tile}
          </Pressable>
        );
      })}
    </View>
  );
}
