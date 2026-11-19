import { ChevronUp } from 'lucide-react-native';
import type { ReactNode } from 'react';
import { Pressable, View } from 'react-native';

import { Icon } from '@/components/Icon';
import { Text } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

/**
 * A food-category card that opens and closes (Kitchen): name,
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
          paddingHorizontal: 14,
          minHeight: 48,
        }}
      >
        <Text variant="label" accessibilityRole="header" style={{ flex: 1 }}>
          {label}
        </Text>
        <Text variant="caption" muted style={{ fontVariant: ['tabular-nums'] }}>
          {count}
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
