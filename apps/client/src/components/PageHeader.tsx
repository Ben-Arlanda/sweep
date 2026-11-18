import type { LucideIcon } from 'lucide-react-native';
import type { ReactNode } from 'react';
import { View } from 'react-native';

import { Icon } from '@/components/Icon';
import { Text } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

/**
 * The header on a plain tab screen (Kitchen, Shopping List, Plan): the tab's icon, the
 * title at "title" size, optional things on the right, and a line under it. One
 * component, so every tab's header is the same size and sits at the same height.
 */
export function PageHeader({
  icon,
  title,
  right,
  subtitle,
}: {
  icon: LucideIcon;
  title: string;
  right?: ReactNode;
  /** Under the title, e.g. "4 to buy" (read out when it changes). */
  subtitle?: ReactNode;
}) {
  const t = useTheme();
  return (
    <View style={{ gap: t.space.xs, paddingTop: t.space.lg }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.sm }}>
        <Icon icon={icon} size={34} color={t.colors.text} />
        <Text variant="title" accessibilityRole="header" style={{ flex: 1 }}>
          {title}
        </Text>
        {right}
      </View>
      {subtitle ? (
        <Text muted accessibilityLiveRegion="polite">
          {subtitle}
        </Text>
      ) : null}
    </View>
  );
}
