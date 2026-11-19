import { Tabs } from 'expo-router/tabs';
import { BookOpen, CalendarDays, House, Refrigerator, ShoppingBasket } from 'lucide-react-native';

import { FloatingTabBar, type TabItem } from '@/components/FloatingTabBar';
import { useTheme } from '@/theme/useTheme';

/**
 * The tab bar along the bottom: the five places you go most, as a floating pill
 * (FloatingTabBar). Household settings sit behind the cog on Home instead (ADR 0026).
 * Each tab shows an icon and a word (icons alone are guesswork for many people).
 */
const TABS: TabItem[] = [
  { name: 'index', title: 'Home', icon: House, page: 'home' },
  { name: 'lists', title: 'Lists', icon: ShoppingBasket, page: 'list' },
  { name: 'kitchen', title: 'Kitchen', icon: Refrigerator, page: 'kitchen' },
  { name: 'meal-plan', title: 'Plan', icon: CalendarDays, page: 'plan' },
  { name: 'recipes', title: 'Recipes', icon: BookOpen, page: 'recipes' },
];

export default function TabsLayout() {
  const t = useTheme();
  return (
    <Tabs
      tabBar={(props) => <FloatingTabBar {...props} tabs={TABS} />}
      screenOptions={{
        headerShown: false, // each tab's own Stack (or screen) draws its header
        sceneStyle: { backgroundColor: t.colors.background },
      }}
    >
      {TABS.map((tab) => (
        <Tabs.Screen key={tab.name} name={tab.name} options={{ title: tab.title }} />
      ))}
    </Tabs>
  );
}
