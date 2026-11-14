import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Tabs } from 'expo-router/tabs';
import type { ComponentProps } from 'react';
import { Text, View, type ColorValue } from 'react-native';

import { tabBarHeight } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

type IconName = ComponentProps<typeof MaterialCommunityIcons>['name'];

/**
 * The tab bar along the bottom: the five places you go most. Each tab shows an icon
 * and a word (icons alone are guesswork for many people).
 *
 * The selected tab is shown three ways, so it never relies on colour alone (WCAG 1.4.1):
 * the icon fills in, it sits on a lime pill, and its label turns bold and full contrast.
 */
const TABS: { name: string; title: string; icon: IconName; iconSelected: IconName }[] = [
  { name: 'index', title: 'Home', icon: 'home-variant-outline', iconSelected: 'home-variant' },
  { name: 'lists', title: 'Lists', icon: 'basket-outline', iconSelected: 'basket' },
  { name: 'cabinet', title: 'Cabinet', icon: 'fridge-outline', iconSelected: 'fridge' },
  {
    name: 'recipes',
    title: 'Recipes',
    icon: 'book-open-page-variant-outline',
    iconSelected: 'book-open-page-variant',
  },
  {
    name: 'household',
    title: 'Household',
    icon: 'account-group-outline',
    iconSelected: 'account-group',
  },
];

export default function TabsLayout() {
  const t = useTheme();
  return (
    <Tabs
      screenOptions={{
        headerShown: false, // each tab's own Stack (or screen) draws its header
        sceneStyle: { backgroundColor: t.colors.background },
        tabBarActiveTintColor: t.colors.text,
        tabBarInactiveTintColor: t.colors.textMuted,
        tabBarStyle: {
          backgroundColor: t.colors.surface,
          borderTopColor: t.colors.border,
          minHeight: tabBarHeight,
          paddingTop: t.space.xs,
        },
      }}
    >
      {TABS.map((tab) => (
        <Tabs.Screen
          key={tab.name}
          name={tab.name}
          options={{
            title: tab.title,
            tabBarLabel: ({ focused, color }) => (
              <TabLabel title={tab.title} focused={focused} color={color} />
            ),
            tabBarIcon: ({ focused }) => (
              <TabIcon name={focused ? tab.iconSelected : tab.icon} focused={focused} />
            ),
          }}
        />
      ))}
    </Tabs>
  );
}

function TabIcon({ name, focused }: { name: IconName; focused: boolean }) {
  const t = useTheme();
  return (
    <View
      style={{
        width: 52,
        height: 30,
        borderRadius: t.radius.pill,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: focused ? t.colors.action : 'transparent',
      }}
    >
      <MaterialCommunityIcons
        name={name}
        size={22}
        color={focused ? t.colors.onAction : t.colors.textMuted}
        aria-hidden
      />
    </View>
  );
}

function TabLabel({
  title,
  focused,
  color,
}: {
  title: string;
  focused: boolean;
  color: ColorValue;
}) {
  const t = useTheme();
  return (
    <Text
      style={{
        fontFamily: focused ? t.fonts.bold : t.fonts.medium,
        fontSize: 12,
        lineHeight: 16,
        marginTop: 2,
        color,
      }}
    >
      {title}
    </Text>
  );
}
