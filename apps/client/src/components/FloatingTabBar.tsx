import { BlurView } from 'expo-blur';
import { BottomTabBarHeightCallbackContext, type BottomTabBarProps } from 'expo-router/tabs';
import type { LucideIcon } from 'lucide-react-native';
import { use } from 'react';
import { Platform, Text, View } from 'react-native';

import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { palette, TAB_BAR_FROST, TAB_PILL_SHADE, tabBarHeight } from '@/theme/tokens';

const BAR_RADIUS = 22;
import { useTheme } from '@/theme/useTheme';

export type TabItem = { name: string; title: string; icon: LucideIcon };

/**
 * The tab bar as a flat frosted bar floating over the page: the screen scrolls underneath
 * it. The selected tab is shown three ways, never colour alone (WCAG 1.4.1): a soft navy
 * pill, a heavier icon line and a bold label.
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
          height: tabBarHeight,
          borderRadius: BAR_RADIUS,
          boxShadow: '0 10px 28px -12px rgba(18, 26, 46, 0.4)',
        }}
      >
        <View
          accessibilityRole="tablist"
          style={{
            flex: 1,
            borderRadius: BAR_RADIUS,
            borderWidth: 1,
            borderColor: 'rgba(18, 26, 46, 0.08)',
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
              padding: 6,
              gap: 2,
              backgroundColor: `rgba(255, 255, 255, ${TAB_BAR_FROST})`,
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
                    gap: 3,
                    paddingVertical: 4,
                    paddingHorizontal: 6,
                    borderRadius: BAR_RADIUS - 6,
                    backgroundColor: focused ? `rgba(27, 42, 78, ${TAB_PILL_SHADE})` : 'transparent',
                  }}
                >
                  <Icon icon={tab.icon} color={colour} strong={focused} />
                  <Text
                    numberOfLines={1}
                    style={{
                      fontFamily: focused ? t.fonts.bold : t.fonts.medium,
                      fontSize: 11,
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
