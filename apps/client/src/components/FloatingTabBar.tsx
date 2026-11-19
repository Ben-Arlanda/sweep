import type { BottomTabBarProps } from 'expo-router/tabs';
import type { LucideIcon } from 'lucide-react-native';
import { Text, View } from 'react-native';

import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { PAGE_COLORS, palette, tabBarHeight, type Page } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

export type TabItem = { name: string; title: string; icon: LucideIcon; page: Page };

/**
 * The tab bar as a floating pill on the page colour. The selected tab is shown three
 * ways, never colour alone (WCAG 1.4.1): its own rounded pill, a heavier icon line and
 * a bold label. Solid warm white, not glass: see-through glass over the page colour
 * would change the label contrast per page.
 */
export function FloatingTabBar({
  state,
  emitter,
  navigateToTab,
  insets,
  tabs,
}: BottomTabBarProps & { tabs: TabItem[] }) {
  const t = useTheme();
  const current = tabs.find((tab) => tab.name === state.routes[state.index]?.name);
  const pageColour = PAGE_COLORS[current?.page ?? 'home'].background;

  const items = state.routes.map((route, index) => {
    const tab = tabs.find((x) => x.name === route.name);
    if (!tab) return null;
    const focused = index === state.index;
    return (
      <PressableScale
        key={route.key}
        accessibilityRole="tab"
        accessibilityLabel={tab.title}
        accessibilityState={{ selected: focused }}
        onPress={() => {
          const event = emitter.emit({
            type: 'tabPress',
            target: route.key,
            canPreventDefault: true,
          });
          if (!focused && !event.defaultPrevented) navigateToTab(route.key);
        }}
        style={{
          flex: 1,
          alignItems: 'center',
          justifyContent: 'center',
          gap: 2,
          borderRadius: t.radius.pill,
          // The page colour, faint, so the selected pill matches the screen you're on.
          backgroundColor: focused ? `${pageColour}38` : 'transparent',
        }}
      >
        <Icon
          icon={tab.icon}
          color={focused ? t.colors.text : t.colors.textMuted}
          strong={focused}
        />
        <Text
          numberOfLines={1}
          style={{
            fontFamily: focused ? t.fonts.bold : t.fonts.medium,
            fontSize: 12,
            lineHeight: 16,
            color: focused ? t.colors.text : t.colors.textMuted,
          }}
        >
          {tab.title}
        </Text>
      </PressableScale>
    );
  });

  const pill = {
    flexDirection: 'row',
    height: tabBarHeight - t.space.sm,
    padding: 4,
    borderRadius: t.radius.pill,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.7)',
    boxShadow: '0 8px 24px -8px rgba(18, 21, 15, 0.35)',
    overflow: 'hidden',
  } as const;

  return (
    <View
      accessibilityRole="tablist"
      style={{
        backgroundColor: pageColour,
        paddingTop: t.space.sm,
        paddingBottom: Math.max(insets.bottom, t.space.md),
        paddingLeft: Math.max(insets.left, t.space.lg),
        paddingRight: Math.max(insets.right, t.space.lg),
      }}
    >
      <View style={{ width: '100%', maxWidth: 560, alignSelf: 'center' }}>
        <View style={[pill, { backgroundColor: palette.paper }]}>{items}</View>
      </View>
    </View>
  );
}
