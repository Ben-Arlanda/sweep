import { Tabs } from 'expo-router/tabs';
import {
  BookOpen,
  House,
  Refrigerator,
  ShoppingBasket,
  Users,
  type LucideIcon,
} from 'lucide-react-native';
import { Text, View, type ColorValue } from 'react-native';

import { Icon } from '@/components/Icon';
import { tabBarHeight } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

/**
 * The tab bar along the bottom: the five places you go most. Each tab shows an icon
 * and a word (icons alone are guesswork for many people).
 *
 * The selected tab is shown three ways, so it never relies on colour alone (WCAG 1.4.1):
 * the icon's line gets heavier, it sits on a lime pill, and its label turns bold and full
 * contrast.
 */
const TABS: { name: string; title: string; icon: LucideIcon }[] = [
  { name: 'index', title: 'Home', icon: House },
  { name: 'lists', title: 'Lists', icon: ShoppingBasket },
  { name: 'kitchen', title: 'Kitchen', icon: Refrigerator },
  { name: 'recipes', title: 'Recipes', icon: BookOpen },
  { name: 'household', title: 'Household', icon: Users },
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
            tabBarIcon: ({ focused }) => <TabIcon icon={tab.icon} focused={focused} />,
          }}
        />
      ))}
    </Tabs>
  );
}

function TabIcon({ icon, focused }: { icon: LucideIcon; focused: boolean }) {
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
      <Icon icon={icon} color={focused ? t.colors.onAction : t.colors.textMuted} strong={focused} />
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
