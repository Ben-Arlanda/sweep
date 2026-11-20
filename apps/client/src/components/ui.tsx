/**
 * The app's basic building blocks. Every screen is made from these, so the whole app
 * stays consistent and every colour, font and spacing value comes from the theme tokens.
 * Browse them all at /design (src/app/(app)/design.tsx).
 */
import type { LucideIcon } from 'lucide-react-native';
import { use, useEffect, useState, type ReactNode, type Ref } from 'react';
import {
  ActivityIndicator,
  Text as RNText,
  ScrollView,
  TextInput,
  View,
  type ScrollViewInstance,
  type StyleProp,
  type TextInputInstance,
  type TextInputProps,
  type TextProps,
  type ViewStyle,
} from 'react-native';
import { BottomTabBarHeightContext } from 'expo-router/tabs';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';

import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import type { TintName } from '@/theme/tokens';
import { inputText } from '@/theme/inputText';
import { useTheme } from '@/theme/useTheme';
import { haptic } from '@/lib/haptics';

type Variant = 'display' | 'title' | 'heading' | 'body' | 'label' | 'caption';

export function Text({
  variant = 'body',
  muted,
  danger,
  style,
  ...props
}: TextProps & { variant?: Variant; muted?: boolean; danger?: boolean }) {
  const t = useTheme();
  const color = danger ? t.colors.danger : muted ? t.colors.textMuted : t.colors.text;
  return <RNText style={[t.type[variant], { color }, style]} {...props} />;
}

/** A word or phrase on a lime marker stroke, like the website headline. */
export function Highlight({ children }: { children: ReactNode }) {
  const t = useTheme();
  return (
    <RNText style={{ backgroundColor: t.colors.action, color: t.colors.onAction }}>
      {children}
    </RNText>
  );
}

/** Edges for a tab's first screen: it has no navigation header above it. */
export const TAB_ROOT = ['top', 'left', 'right'] as const;

/** The floating round button's size. */
export const FLOATING_SIZE = 56;

export function Screen({
  children,
  edges = ['left', 'right'],
  hero,
  footer,
  scrollRef,
  onScroll,
  floating,
}: {
  children: ReactNode;
  scrollRef?: Ref<ScrollViewInstance>;
  /** A round button floating bottom-right, above the tab bar (the list's +). */
  floating?: ReactNode;
  /** How far the page has scrolled, as it scrolls. */
  onScroll?: (y: number) => void;
  /**
   * Which phone edges (notch, home bar) to keep clear of. The tab bar already keeps
   * clear of the bottom, so most screens need only the sides. Add 'top' on a screen
   * with no navigation header, and 'bottom' on one with no tab bar.
   */
  edges?: readonly ('top' | 'bottom' | 'left' | 'right')[];
  /** A <Hero>: full width at the top, scrolling with the page. It clears the notch itself. */
  hero?: ReactNode;
  /** Stays at the bottom while the page scrolls, e.g. the screen's main button. */
  footer?: ReactNode;
}) {
  const t = useTheme();
  // The floating tab bar covers the bottom of the page: leave room so nothing hides under it.
  const tabBar = use(BottomTabBarHeightContext) ?? 0;
  const insets = useSafeAreaInsets();
  const content = (
    <View
      style={{
        padding: t.space.lg,
        // Room above the toast and the tab bar, and the floating button if there is one.
        paddingBottom: t.space.xxl * 2 + tabBar + (floating ? FLOATING_SIZE : 0),
        gap: t.space.lg,
        width: '100%',
        maxWidth: 560, // readable column on tablets and the web
        alignSelf: 'center',
      }}
    >
      {children}
    </View>
  );
  return (
    <SafeAreaView
      // With a hero, the hero runs up under the status bar and handles the top and sides.
      edges={hero ? edges.filter((e) => e === 'bottom') : edges}
      style={{ flex: 1, backgroundColor: t.colors.background }}
    >
      {/* iOS: leave room for the keyboard so the whole page can scroll above it. */}
      <ScrollView
        ref={scrollRef}
        keyboardShouldPersistTaps="handled"
        automaticallyAdjustKeyboardInsets
        onScroll={onScroll ? (e) => onScroll(e.nativeEvent.contentOffset.y) : undefined}
        scrollEventThrottle={16}
      >
        {hero}
        {content}
      </ScrollView>
      {footer ? (
        // The page colour with a soft shadow above, so the list scrolls "under" the bar.
        <View
          style={{
            backgroundColor: t.colors.background,
            boxShadow: '0 -6px 14px -6px rgba(18, 21, 15, 0.22)',
          }}
        >
          <View
            style={{
              paddingHorizontal: t.space.lg,
              paddingTop: t.space.md,
              paddingBottom: t.space.lg + tabBar,
              width: '100%',
              maxWidth: 560,
              alignSelf: 'center',
              gap: t.space.xs,
            }}
          >
            {footer}
          </View>
        </View>
      ) : null}
      {floating ? (
        <View
          pointerEvents="box-none"
          style={{
            position: 'absolute',
            right: t.space.lg,
            bottom: insets.bottom + tabBar + t.space.md,
          }}
        >
          {floating}
        </View>
      ) : null}
    </SafeAreaView>
  );
}

/**
 * A rounded panel. Plain cards are white with a hairline edge; `tint` makes it a pastel
 * card (one per list, day or Member); `inverse` is the single strong anchor on a screen.
 */
export function Card({
  children,
  tint,
  inverse,
  style,
}: {
  children: ReactNode;
  tint?: TintName;
  inverse?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  const t = useTheme();
  const backgroundColor = inverse ? t.colors.inverse : tint ? t.tints[tint].bg : t.colors.surface;
  return (
    <View
      style={[
        {
          backgroundColor,
          borderRadius: t.radius.lg,
          padding: t.space.lg,
          gap: t.space.md,
          boxShadow: tint || inverse ? undefined : t.shadow.card,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}

type ButtonVariant =
  | 'primary'
  | 'secondary'
  | 'ghost'
  | 'danger'
  | 'dark'
  | 'strong'
  | 'outline'
  | 'lavender'
  | 'dangerSolid';

/**
 * Buttons (12pt corners). `primary` is lime: use one per screen, for the main thing to do next.
 * Everything else is `secondary` (white), `ghost` (text only) or `danger`. `dark` is
 * the deep green for a screen whose main step is "go and look" (Dinner planned!).
 */
export function Button({
  title,
  onPress,
  variant = 'primary',
  disabled,
  loading,
  compact,
  tight,
  accessibilityLabel,
  icon,
}: {
  title: string;
  /** A small icon before the title. Decorative: the title names the button. */
  icon?: LucideIcon;
  /** When the visible title needs more context, e.g. "Remove" → "Remove Bob". */
  accessibilityLabel?: string;
  onPress: () => void;
  variant?: ButtonVariant;
  disabled?: boolean;
  loading?: boolean;
  /** Fits its text instead of filling the width. */
  compact?: boolean;
  /** Less side padding, for two buttons sharing a row ("View recipe | Mark as cooked"). */
  tight?: boolean;
}) {
  const t = useTheme();
  const [pressed, setPressed] = useState(false);
  const inactive = disabled || loading;

  const look: Record<ButtonVariant, { bg: string; fg: string; border: string }> = {
    primary: {
      bg: pressed ? t.colors.actionPressed : t.colors.action,
      fg: t.colors.onAction,
      border: 'transparent',
    },
    secondary: { bg: t.colors.surface, fg: t.colors.text, border: t.colors.border },
    ghost: { bg: 'transparent', fg: t.colors.text, border: 'transparent' },
    danger: { bg: 'transparent', fg: t.colors.danger, border: t.colors.danger },
    dark: { bg: t.colors.tabSelected, fg: t.colors.surface, border: 'transparent' },
    strong: { bg: t.colors.strong, fg: t.colors.onStrong, border: 'transparent' },
    // A quiet second action (Undo): see-through, thin border, muted text.
    outline: { bg: 'transparent', fg: t.colors.textMuted, border: t.colors.border },
    lavender: { bg: t.colors.lavender, fg: t.colors.onLavender, border: 'transparent' },
    // The step that actually deletes something: solid red, white text.
    dangerSolid: { bg: t.colors.danger, fg: t.colors.onDanger, border: 'transparent' },
  };
  const { bg, fg, border } = look[variant];
  // Filled buttons get the heavier label; outlined and text-only ones stay quieter.
  const quiet = variant === 'secondary' || variant === 'ghost' || variant === 'outline';

  return (
    <PressableScale
      accessibilityRole="button"
      // While loading, the spinner replaces the text, so the label keeps the button named.
      accessibilityLabel={accessibilityLabel ?? title}
      accessibilityState={{ disabled: inactive, busy: loading }}
      onPress={onPress}
      onPressIn={() => setPressed(true)}
      onPressOut={() => setPressed(false)}
      disabled={inactive}
      style={{
        minHeight: t.touchTarget,
        borderRadius: t.radius.md,
        paddingHorizontal: tight ? t.space.md : t.space.lg,
        alignItems: 'center',
        justifyContent: 'center',
        alignSelf: compact ? 'flex-start' : 'stretch',
        backgroundColor: bg,
        borderWidth: border === 'transparent' ? 0 : 1,
        borderColor: border,
        opacity: inactive ? 0.45 : 1,
      }}
    >
      {loading ? (
        <ActivityIndicator color={fg} aria-hidden />
      ) : (
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.sm }}>
          {icon ? <Icon icon={icon} size={20} color={fg} /> : null}
          <RNText
            style={[t.type.label, { color: fg, fontFamily: quiet ? t.fonts.medium : t.fonts.bold }]}
          >
            {title}
          </RNText>
        </View>
      )}
    </PressableScale>
  );
}

export function Field({
  label,
  error,
  ref,
  hideLabel,
  style,
  ...props
}: TextInputProps & {
  label: string;
  error?: string | null;
  ref?: Ref<TextInputInstance>;
  /** Keep the label for screen readers but don't show it (e.g. a search box). */
  hideLabel?: boolean;
}) {
  const t = useTheme();
  const [focused, setFocused] = useState(false);
  return (
    <View style={{ gap: t.space.xs }}>
      {hideLabel ? null : <Text variant="label">{label}</Text>}
      <TextInput
        ref={ref}
        accessibilityLabel={label}
        placeholderTextColor={t.colors.textMuted}
        onFocus={(e) => {
          setFocused(true);
          props.onFocus?.(e);
        }}
        onBlur={(e) => {
          setFocused(false);
          props.onBlur?.(e);
        }}
        style={[
          props.multiline ? t.type.body : inputText(t.type.body), // multi-line keeps its line spacing
          {
            minHeight: t.touchTarget + 4,
            borderWidth: 1,
            borderColor: error ? t.colors.danger : focused ? t.colors.text : t.colors.border,
            borderRadius: t.radius.md,
            paddingHorizontal: t.space.lg,
            color: t.colors.text,
            backgroundColor: t.colors.surface,
          },
          style, // added to the look above (e.g. a taller multiline box), not instead of it
        ]}
        {...props}
      />
      {error ? (
        <Text variant="caption" danger>
          {error}
        </Text>
      ) : null}
    </View>
  );
}

/** On its own soft-red pill, so it reads on any page colour as well as on cards. */
export function ErrorText({ message }: { message: string | null | undefined }) {
  const t = useTheme();
  useEffect(() => {
    if (message) haptic.error(); // once per new message, not on every render
  }, [message]);
  if (!message) return null;
  return (
    <Text
      variant="caption"
      danger
      accessibilityRole="alert"
      style={{
        alignSelf: 'flex-start',
        backgroundColor: t.colors.dangerSoft,
        borderRadius: t.radius.sm,
        paddingHorizontal: t.space.sm,
        paddingVertical: 2,
        overflow: 'hidden',
      }}
    >
      {message}
    </Text>
  );
}

export function Loading() {
  const t = useTheme();
  return (
    <View
      style={{
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.background,
      }}
    >
      <ActivityIndicator color={t.colors.onBackground} size="large" accessibilityLabel="Loading" />
    </View>
  );
}

/** A small uppercase label above a group, e.g. "IN THE TROLLEY". */
export function SectionLabel({ children }: { children: ReactNode }) {
  const t = useTheme();
  return (
    <Text
      variant="caption"
      muted
      style={{ fontFamily: t.fonts.bold, letterSpacing: 1.2, textTransform: 'uppercase' }}
    >
      {children}
    </Text>
  );
}
