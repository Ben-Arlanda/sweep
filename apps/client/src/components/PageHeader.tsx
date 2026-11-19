import type { LucideIcon } from 'lucide-react-native';
import type { ReactNode } from 'react';
import { View } from 'react-native';

import { Icon } from '@/components/Icon';
import { Text } from '@/components/ui';
import { sectionTints } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

/**
 * The header on a plain tab screen (Kitchen, Shopping List, Plan): the tab's icon on its
 * small coloured tile, the title, optional things on the right, and a line under it. One
 * component, so every tab's header is the same size and sits at the same height.
 */
export function PageHeader({
  icon,
  section,
  title,
  right,
  subtitle,
}: {
  icon: LucideIcon;
  /** Which tab: picks the colour of the small icon tile. */
  section: keyof typeof sectionTints;
  title: string;
  right?: ReactNode;
  /** Under the title, e.g. "4 to buy" (read out when it changes). */
  subtitle?: ReactNode;
}) {
  const t = useTheme();
  return (
    <View style={{ gap: t.space.xs, paddingTop: t.space.lg }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.sm }}>
        <View
          style={{
            width: 32,
            height: 32,
            borderRadius: 10,
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: sectionTints[section].bg,
          }}
        >
          <Icon icon={icon} size={18} color={sectionTints[section].fg} />
        </View>
        <Text
          variant="title"
          accessibilityRole="header"
          style={{ flex: 1, color: t.colors.onBackground }}
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
