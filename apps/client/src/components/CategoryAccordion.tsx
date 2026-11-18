import {
  Beef,
  ChevronUp,
  Croissant,
  CupSoda,
  Fish,
  Milk,
  Package,
  Refrigerator,
  Salad,
  Snowflake,
  Sparkles,
  type LucideIcon,
} from 'lucide-react-native';
import type { ReactNode } from 'react';
import { Pressable, View } from 'react-native';

import { Icon } from '@/components/Icon';
import { Text } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

const CATEGORY_ICON: Record<string, LucideIcon> = {
  spices: Sparkles,
  pantry: Package,
  bakery: Croissant,
  produce: Salad,
  dairy: Milk,
  chilled: Refrigerator,
  meat: Beef,
  seafood: Fish,
  frozen: Snowflake,
  drinks: CupSoda,
};

/**
 * A food-category card that opens and closes (Kitchen and Shopping List): icon, name,
 * how many items, and a chevron. The header is one button that says whether it's open.
 */
export function CategoryAccordion({
  category,
  label,
  count,
  open,
  onToggle,
  children,
}: {
  category: string;
  label: string;
  count: number;
  open: boolean;
  onToggle: () => void;
  children: ReactNode;
}) {
  const t = useTheme();
  return (
    <View
      style={{
        backgroundColor: t.colors.surface,
        borderRadius: t.radius.lg,
        boxShadow: t.shadow.card,
        overflow: 'hidden', // rows swipe inside the card's rounded corners
      }}
    >
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ expanded: open }}
        accessibilityLabel={`${label}, ${count} ${count === 1 ? 'item' : 'items'}`}
        onPress={onToggle}
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: t.space.sm,
          paddingHorizontal: t.space.lg,
          minHeight: 56,
        }}
      >
        <Icon icon={CATEGORY_ICON[category] ?? Package} color={t.colors.text} />
        <Text variant="heading" accessibilityRole="header" style={{ fontSize: 18 }}>
          {label}
        </Text>
        <Text variant="caption" muted style={{ flex: 1 }}>
          {count} {count === 1 ? 'item' : 'items'}
        </Text>
        <View style={{ transform: [{ rotate: open ? '0deg' : '180deg' }] }}>
          <Icon icon={ChevronUp} size={20} color={t.colors.text} strong />
        </View>
      </Pressable>
      {open ? children : null}
    </View>
  );
}

/** Which categories are closed, toggled one at a time. */
export function toggled(closed: ReadonlySet<string>, category: string): Set<string> {
  const next = new Set(closed);
  if (next.has(category)) next.delete(category);
  else next.add(category);
  return next;
}
