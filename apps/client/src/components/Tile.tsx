import { Link, type Href } from 'expo-router';
import type { ReactNode } from 'react';
import { Text, View } from 'react-native';

import { PressableScale } from '@/components/PressableScale';
import type { TintName } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

/**
 * A pastel card on the home board ("the fridge door"): a list, the Cabinet, and later
 * tonight's dinner and the week. Taps through to `href`.
 */
export function Tile({
  href,
  tint,
  title,
  subtitle,
  emoji,
  wide,
  children,
}: {
  href: Href;
  tint: TintName;
  title: string;
  subtitle?: string;
  emoji?: string;
  /** Span both columns. */
  wide?: boolean;
  children?: ReactNode;
}) {
  const t = useTheme();
  const c = t.tints[tint];
  return (
    <Link href={href} asChild>
      <PressableScale
        accessibilityRole="link"
        style={{
          flexBasis: wide ? '100%' : '47%',
          flexGrow: 1,
          minHeight: 112,
          backgroundColor: c.bg,
          borderRadius: t.radius.lg,
          padding: t.space.lg,
          gap: 2,
        }}
      >
        {emoji ? (
          <Text aria-hidden style={{ fontSize: 24, marginBottom: 4 }}>
            {emoji}
          </Text>
        ) : null}
        <Text style={[t.type.heading, { color: c.text }]} numberOfLines={2}>
          {title}
        </Text>
        {subtitle ? (
          <Text style={[t.type.caption, { color: c.text, opacity: 0.8 }]}>{subtitle}</Text>
        ) : null}
        {children ? <View style={{ marginTop: t.space.sm }}>{children}</View> : null}
      </PressableScale>
    </Link>
  );
}
