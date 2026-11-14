/**
 * The app's basic building blocks. Every screen is made from these, so the whole app
 * stays consistent and every colour/spacing value comes from the theme tokens.
 */
import type { ReactNode, Ref } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text as RNText,
  TextInput,
  View,
  type TextInputInstance,
  type TextInputProps,
  type TextProps,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useTheme } from '@/theme/useTheme';

type Variant = 'title' | 'heading' | 'body' | 'label' | 'caption';

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

export function Screen({ children }: { children: ReactNode }) {
  const t = useTheme();
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.colors.background }}>
      <ScrollView
        contentContainerStyle={{
          padding: t.space.xl,
          gap: t.space.lg,
          width: '100%',
          maxWidth: 520, // readable column on tablets and the web
          alignSelf: 'center',
        }}
        keyboardShouldPersistTaps="handled"
      >
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

export function Card({ children }: { children: ReactNode }) {
  const t = useTheme();
  return (
    <View
      style={{
        backgroundColor: t.colors.surface,
        borderColor: t.colors.border,
        borderWidth: 1,
        borderRadius: t.radius.lg,
        padding: t.space.lg,
        gap: t.space.md,
      }}
    >
      {children}
    </View>
  );
}

export function Button({
  title,
  onPress,
  variant = 'primary',
  disabled,
  loading,
}: {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
  loading?: boolean;
}) {
  const t = useTheme();
  const inactive = disabled || loading;
  const filled = variant === 'primary';
  const textColor = filled
    ? t.colors.onPrimary
    : variant === 'danger'
      ? t.colors.danger
      : t.colors.primary;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: inactive, busy: loading }}
      onPress={onPress}
      disabled={inactive}
      style={({ pressed }) => ({
        minHeight: t.touchTarget,
        borderRadius: t.radius.md,
        paddingHorizontal: t.space.lg,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: filled
          ? pressed
            ? t.colors.primaryPressed
            : t.colors.primary
          : 'transparent',
        borderWidth: filled ? 0 : 1,
        borderColor: variant === 'danger' ? t.colors.danger : t.colors.border,
        opacity: inactive ? 0.5 : pressed && !filled ? 0.7 : 1,
      })}
    >
      {loading ? (
        <ActivityIndicator color={textColor} />
      ) : (
        <Text variant="label" style={{ color: textColor }}>
          {title}
        </Text>
      )}
    </Pressable>
  );
}

export function Field({
  label,
  error,
  ref,
  ...props
}: TextInputProps & { label: string; error?: string | null; ref?: Ref<TextInputInstance> }) {
  const t = useTheme();
  return (
    <View style={{ gap: t.space.xs }}>
      <Text variant="label">{label}</Text>
      <TextInput
        ref={ref}
        accessibilityLabel={label}
        placeholderTextColor={t.colors.textMuted}
        style={[
          t.type.body,
          {
            minHeight: t.touchTarget,
            borderWidth: 1,
            borderColor: error ? t.colors.danger : t.colors.border,
            borderRadius: t.radius.md,
            paddingHorizontal: t.space.md,
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
      <ActivityIndicator color={t.colors.primary} size="large" />
    </View>
  );
}
