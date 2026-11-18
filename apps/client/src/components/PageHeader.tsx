import type { LucideIcon } from 'lucide-react-native';
import type { ReactNode } from 'react';
import { View } from 'react-native';

import { Icon } from '@/components/Icon';
import { Text } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

/**
 * The header on a plain tab screen (Kitchen, Shopping List, Plan): the tab's icon, the
 * title at "title" size, optional things on the right, and a line under it. The icon
 * and title are white on every page, like Home; the line under it uses the page's text
 * colour (white or ink, whichever passes AA), so small text stays readable. One
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
        <Icon icon={icon} size={34} color={t.colors.onHeader} />
        <Text
          variant="title"
          accessibilityRole="header"
          style={{ flex: 1, color: t.colors.onHeader }}
        >
          {title}
        </Text>
        {right}
      </View>
      {subtitle ? (
        <Text accessibilityLiveRegion="polite" style={{ color: t.colors.onBackgroundMuted }}>
          {subtitle}
        </Text>
      ) : null}
    </View>
  );
}
