import { BlurView } from 'expo-blur';
import { BottomTabBarHeightCallbackContext, type BottomTabBarProps } from 'expo-router/tabs';
import type { LucideIcon } from 'lucide-react-native';
import { use } from 'react';
import { Platform, Text, View } from 'react-native';

import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { mix } from '@/theme/contrast';
import {
  PAGE_COLORS,
  palette,
  TAB_BAR_FROST,
  TAB_PILL_TINT,
  tabBarHeight,
  type Page,
} from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

export type TabItem = { name: string; title: string; icon: LucideIcon; page: Page };

/**
 * The tab bar as a frosted pill floating over the page (like Apple's Podcasts): the
 * screen scrolls underneath it. The selected tab is shown three ways, never colour
 * alone (WCAG 1.4.1): its own solid pill, a heavier icon line and a bold label.
 */
export function FloatingTabBar({
  state,
  emitter,
  navigateToTab,
  insets,
  tabs,
}: BottomTabBarProps & { tabs: TabItem[] }) {
  const t = useTheme();
  // Tells each screen how much room the bar takes, so <Screen> can leave space for it.
  const reportHeight = use(BottomTabBarHeightCallbackContext);
  const current = tabs.find((tab) => tab.name === state.routes[state.index]?.name);
  const selectedPill = mix(
    PAGE_COLORS[current?.page ?? 'home'].background,
    palette.paper,
    TAB_PILL_TINT,
  );

  return (
    <View
      pointerEvents="box-none"
      onLayout={(e) => reportHeight?.(e.nativeEvent.layout.height)}
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        bottom: 0,
        paddingBottom: Math.max(insets.bottom, t.space.md),
        paddingLeft: Math.max(insets.left, t.space.lg),
        paddingRight: Math.max(insets.right, t.space.lg),
      }}
    >
      {/* The shadow sits on an outer view: iOS clips shadows on a view with overflow hidden. */}
      <View
        style={{
          width: '100%',
          maxWidth: 560,
          alignSelf: 'center',
          height: tabBarHeight - t.space.sm,
          borderRadius: t.radius.pill,
          // Two shadows: a soft one far below and a tight one close in, for depth.
          boxShadow: '0 14px 30px -10px rgba(18, 21, 15, 0.5), 0 2px 6px rgba(18, 21, 15, 0.14)',
        }}
      >
        <View
          accessibilityRole="tablist"
          style={{
            flex: 1,
            borderRadius: t.radius.pill,
            borderWidth: 1,
            borderColor: 'rgba(255, 255, 255, 0.85)',
            overflow: 'hidden',
          }}
        >
          {/* Android's blur needs a target view, so it gets the frost colour alone. */}
          {Platform.OS === 'android' ? null : (
            <BlurView
              intensity={60}
              tint="light"
              style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 }}
            />
          )}
          <View
            style={{
              flex: 1,
              flexDirection: 'row',
              padding: 5,
              backgroundColor: `rgba(255, 250, 244, ${TAB_BAR_FROST})`,
              // Glass: a bright sheen across the top half and a lit top edge.
              backgroundImage:
                'linear-gradient(180deg, rgba(255, 255, 255, 0.6) 0%, rgba(255, 255, 255, 0) 55%)',
              boxShadow:
                'inset 0 1.5px 0 rgba(255, 255, 255, 0.95), inset 0 -1px 0 rgba(18, 21, 15, 0.06)',
            }}
          >
            {state.routes.map((route, index) => {
              const tab = tabs.find((x) => x.name === route.name);
              if (!tab) return null;
              const focused = index === state.index;
              const colour = focused ? palette.ink : palette.ink700;
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
                    backgroundColor: focused ? selectedPill : 'transparent',
                    // Pressed in: shade at the top inside, a light lip along the bottom.
                    boxShadow: focused
                      ? 'inset 0 2px 5px rgba(18, 21, 15, 0.3), inset 0 -1px 0 rgba(255, 255, 255, 0.45)'
                      : undefined,
                  }}
                >
                  <Icon icon={tab.icon} color={colour} strong={focused} />
                  <Text
                    numberOfLines={1}
                    style={{
                      fontFamily: focused ? t.fonts.bold : t.fonts.medium,
                      fontSize: 12,
                      lineHeight: 16,
                      color: colour,
                    }}
                  >
                    {tab.title}
                  </Text>
                </PressableScale>
              );
            })}
          </View>
        </View>
      </View>
    </View>
  );
}
