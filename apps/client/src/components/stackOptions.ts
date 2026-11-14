import { useTheme } from '@/theme/useTheme';

/**
 * The header look for every Stack in the app (each tab has its own Stack, so you can
 * open a recipe and still see the tab bar). One place, so they all match.
 */
export function useStackScreenOptions() {
  const t = useTheme();
  return {
    headerStyle: { backgroundColor: t.colors.background },
    headerShadowVisible: false,
    headerTintColor: t.colors.text,
    headerTitleStyle: { fontFamily: t.fonts.displayBold, fontSize: 18 },
    headerBackButtonDisplayMode: 'minimal' as const,
    contentStyle: { backgroundColor: t.colors.background },
  };
}
