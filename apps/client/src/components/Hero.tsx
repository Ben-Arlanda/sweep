import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useState, type ReactNode } from 'react';
import { Platform, TextInput, View, type TextInputProps } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Text } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

/**
 * The coloured panel at the top of a main screen, running up under the status bar, with
 * big rounded bottom corners. It holds the screen's title and, where there is one, the
 * search box. Pass it to `<Screen hero={…}>`, which puts it above the content.
 */
export function Hero({
  title,
  top,
  subtitle,
  children,
}: {
  /** The screen's heading (one per screen, so it's marked as the header). */
  title: ReactNode;
  /** A row above the title: who's in the Household, a small label, etc. */
  top?: ReactNode;
  subtitle?: ReactNode;
  /** Usually a HeroSearch. */
  children?: ReactNode;
}) {
  const t = useTheme();
  const insets = useSafeAreaInsets();

  return (
    <View
      style={{
        backgroundColor: t.colors.hero,
        borderBottomLeftRadius: t.radius.hero,
        borderBottomRightRadius: t.radius.hero,
        paddingTop: insets.top + t.space.lg,
        paddingBottom: t.space.xl,
        paddingLeft: Math.max(insets.left, t.space.lg),
        paddingRight: Math.max(insets.right, t.space.lg),
      }}
    >
      <View style={{ width: '100%', maxWidth: 560, alignSelf: 'center', gap: t.space.lg }}>
        {top}
        <View style={{ gap: t.space.xs }}>
          <Text variant="display" accessibilityRole="header" style={{ color: t.colors.onHero }}>
            {title}
          </Text>
          {subtitle ? (
            <Text style={{ color: t.colors.onHeroMuted }}>{subtitle}</Text>
          ) : null}
        </View>
        {children}
      </View>
    </View>
  );
}

/** A small label over a value, for the hero's top row ("Household" / "The Flat"). */
export function HeroLabel({ label, value }: { label: string; value: string }) {
  const t = useTheme();
  return (
    <View>
      <Text variant="caption" style={{ color: t.colors.onHeroMuted }}>
        {label}
      </Text>
      <Text variant="label" style={{ color: t.colors.onHero }}>
        {value}
      </Text>
    </View>
  );
}

// Web only: browsers draw their own focus box inside the pill. The white ring on the
// pill is our focus indicator, so turn the browser's off for these fields alone.
if (Platform.OS === 'web' && typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = '[data-hero-search]:focus { outline: none; }';
  document.head.appendChild(style);
}

/** The pill-shaped search box that sits inside the hero. */
export function HeroSearch({ label, ...props }: TextInputProps & { label: string }) {
  const t = useTheme();
  const [focused, setFocused] = useState(false);
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.sm,
        minHeight: t.touchTarget + 8,
        paddingHorizontal: t.space.lg,
        borderRadius: t.radius.pill,
        backgroundColor: t.colors.heroField,
        borderWidth: 1.5,
        // A clear ring while typing: the field's focus indicator (see the web rule above).
        borderColor: focused ? t.colors.onHero : 'transparent',
      }}
    >
      <MaterialCommunityIcons name="magnify" size={22} color={t.colors.onHeroMuted} aria-hidden />
      <TextInput
        {...props}
        // react-native-web turns dataSet into a data-hero-search attribute (see above).
        {...({ dataSet: { heroSearch: '' } } as object)}
        accessibilityLabel={label}
        placeholderTextColor={t.colors.onHeroMuted}
        onFocus={(e) => {
          setFocused(true);
          props.onFocus?.(e);
        }}
        onBlur={(e) => {
          setFocused(false);
          props.onBlur?.(e);
        }}
        style={[
          t.type.body,
          { flex: 1, minHeight: t.touchTarget, color: t.colors.onHero },
        ]}
      />
    </View>
  );
}
