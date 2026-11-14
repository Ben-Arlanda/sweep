/**
 * The app's basic building blocks. Every screen is made from these, so the whole app
 * stays consistent and every colour, font and spacing value comes from the theme tokens.
 * Browse them all at /design (src/app/(app)/design.tsx).
 */
import { useState, type ReactNode, type Ref } from 'react';
import {
  ActivityIndicator,
  Text as RNText,
  ScrollView,
  TextInput,
  View,
  type StyleProp,
  type TextInputInstance,
  type TextInputProps,
  type TextProps,
  type ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { PressableScale } from '@/components/PressableScale';
import type { TintName } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

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

export function Screen({
  children,
  edges = ['bottom', 'left', 'right'],
}: {
  children: ReactNode;
  /** Pass ['top', ...] on screens without a navigation header. */
  edges?: ('top' | 'bottom' | 'left' | 'right')[];
}) {
  const t = useTheme();
  return (
    <SafeAreaView edges={edges} style={{ flex: 1, backgroundColor: t.colors.background }}>
      <ScrollView
        contentContainerStyle={{
          padding: t.space.lg,
          paddingBottom: t.space.xxl * 2, // room above the toast
          gap: t.space.lg,
          width: '100%',
          maxWidth: 560, // readable column on tablets and the web
          alignSelf: 'center',
        }}
        keyboardShouldPersistTaps="handled"
      >
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

/**
 * A rounded panel. Plain cards are white with a soft shadow; `tint` makes it a pastel
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
  const backgroundColor = inverse
    ? t.colors.inverse
    : tint
      ? t.tints[tint].bg
      : t.colors.surface;
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

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

/**
 * Pill buttons. `primary` is lime: use one per screen, for the main thing to do next.
 * Everything else is `secondary` (white), `ghost` (text only) or `danger`.
 */
export function Button({
  title,
  onPress,
  variant = 'primary',
  disabled,
  loading,
  compact,
  accessibilityLabel,
}: {
  title: string;
  /** When the visible title needs more context, e.g. "Remove" → "Remove Bob". */
  accessibilityLabel?: string;
  onPress: () => void;
  variant?: ButtonVariant;
  disabled?: boolean;
  loading?: boolean;
  /** Fits its text instead of filling the width. */
  compact?: boolean;
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
  };
  const { bg, fg, border } = look[variant];

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
        minHeight: t.touchTarget + 4,
        borderRadius: t.radius.pill,
        paddingHorizontal: t.space.xl,
        alignItems: 'center',
        justifyContent: 'center',
        alignSelf: compact ? 'flex-start' : 'stretch',
        backgroundColor: bg,
        borderWidth: border === 'transparent' ? 0 : 1.5,
        borderColor: border,
        opacity: inactive ? 0.45 : 1,
      }}
    >
      {loading ? (
        <ActivityIndicator color={fg} aria-hidden />
      ) : (
        <RNText style={[t.type.label, { color: fg, fontFamily: t.fonts.displayBold, fontSize: 16 }]}>
          {title}
        </RNText>
      )}
    </PressableScale>
  );
}

export function Field({
  label,
  error,
  ref,
  hideLabel,
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
          t.type.body,
          {
            minHeight: t.touchTarget + 4,
            borderWidth: 1.5,
            borderColor: error ? t.colors.danger : focused ? t.colors.text : t.colors.border,
            borderRadius: t.radius.md,
            paddingHorizontal: t.space.lg,
            color: t.colors.text,
            backgroundColor: t.colors.surface,
          },
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

export function ErrorText({ message }: { message: string | null | undefined }) {
  if (!message) return null;
  return (
    <Text variant="caption" danger accessibilityRole="alert">
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
      <ActivityIndicator color={t.colors.text} size="large" accessibilityLabel="Loading" />
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
