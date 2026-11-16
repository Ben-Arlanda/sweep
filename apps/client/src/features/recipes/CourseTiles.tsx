import {
  CakeSlice,
  EggFried,
  Salad,
  Sandwich,
  Utensils,
  type LucideIcon,
} from 'lucide-react-native';
import { Pressable, Text, useWindowDimensions, View } from 'react-native';

import { Icon } from '@/components/Icon';
import { useTheme } from '@/theme/useTheme';

import { COURSES, tapCourse, type Course } from './courses';

const ICONS: Record<Course, LucideIcon> = {
  main: Utensils,
  side: Salad,
  dessert: CakeSlice,
  breakfast: EggFried,
  lunch: Sandwich,
};

/**
 * The Course filter: one row of five tiles, an icon over the word. The tiles share the
 * width equally, so the row never wraps or runs off a small phone. There's no "All"
 * tile: tapping the chosen one again shows every Course.
 *
 * For screen readers it's a radio group, like ChoiceChips. Each tile is named by its
 * word; the icon is decorative.
 */
export function CourseTiles({
  value,
  onChange,
}: {
  value: Course | null;
  onChange: (value: Course | null) => void;
}) {
  const t = useTheme();
  // "Breakfast" is the longest word: on the smallest phones the labels step down a size
  // so it still fits on one line (320px is the WCAG reflow width).
  const narrow = useWindowDimensions().width < 360;
  return (
    <View
      accessibilityRole="radiogroup"
      accessibilityLabel="Course"
      style={{ flexDirection: 'row', gap: t.space.xs + 2 }}
    >
      {COURSES.map((course) => {
        const selected = course.value === value;
        const color = selected ? t.colors.onInverse : t.colors.text;
        return (
          <Pressable
            key={course.value}
            accessibilityRole="radio"
            aria-checked={selected}
            accessibilityLabel={course.label}
            accessibilityHint={selected ? 'Tap again to show every course' : undefined}
            onPress={() => onChange(tapCourse(value, course.value))}
            style={({ pressed }) => ({
              flex: 1,
              minWidth: 0,
              minHeight: 60,
              borderRadius: t.radius.lg - 2,
              borderWidth: 1,
              borderColor: selected ? t.colors.inverse : t.colors.border,
              backgroundColor: selected ? t.colors.inverse : t.colors.surface,
              alignItems: 'center',
              justifyContent: 'center',
              gap: t.space.xs,
              paddingVertical: t.space.sm,
              opacity: pressed ? 0.75 : 1,
            })}
          >
            <Icon icon={ICONS[course.value]} size={narrow ? 20 : 22} color={color} />
            <Text
              numberOfLines={1}
              style={{
                fontFamily: t.fonts.bold,
                fontSize: narrow ? 11 : 12,
                lineHeight: 16,
                letterSpacing: narrow ? -0.2 : 0,
                color,
              }}
            >
              {course.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}
