import { ChevronUp } from 'lucide-react-native';
import type { ReactNode } from 'react';
import { Pressable, View } from 'react-native';

import { Icon } from '@/components/Icon';
import { Text } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

/**
 * A food category (Kitchen and Shopping List): a small uppercase heading over a white card
 * of rows. The heading folds the card away, so a long list stays easy to scan.
 */
export function CategoryAccordion({
  label,
  count,
  first,
  open,
  onToggle,
  children,
}: {
  label: string;
  count: number;
  /** The first category has no line above it; the others are split by one. */
  first: boolean;
  open: boolean;
  onToggle: () => void;
  children: ReactNode;
}) {
  const t = useTheme();
  return (
    <View
      style={[
        { gap: t.space.sm },
        first ? null : { borderTopWidth: 1, borderTopColor: t.colors.border, paddingTop: 10 },
      ]}
    >
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ expanded: open }}
        accessibilityLabel={`${label}, ${count} ${count === 1 ? 'item' : 'items'}`}
        onPress={onToggle}
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: 6,
          minHeight: 32,
          paddingLeft: 2,
        }}
      >
        <Text
          variant="caption"
          muted
          accessibilityRole="header"
          style={{
            fontFamily: t.fonts.bold,
            fontSize: 13,
            lineHeight: 18,
            letterSpacing: 0.7,
            textTransform: 'uppercase',
          }}
        >
          {label}
        </Text>
        <View style={{ transform: [{ rotate: open ? '0deg' : '180deg' }] }}>
          <Icon icon={ChevronUp} size={16} color={t.colors.textMuted} strong />
        </View>
      </Pressable>
      {open ? (
        <View
          style={{
            backgroundColor: t.colors.surface,
            borderRadius: t.radius.lg,
            boxShadow: t.shadow.card,
            overflow: 'hidden', // rows swipe inside the card's rounded corners
          }}
        >
          {children}
        </View>
      ) : null}
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
