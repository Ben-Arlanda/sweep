import type { ReactNode } from 'react';
import { Text, View } from 'react-native';

import type { StatusName, TintName } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

/**
 * Quantity and price pills, in "matched tint": a deeper shade of the item's own pastel,
 * so the pill and its row read as one object. Without a tint it's a quiet neutral.
 */
export function Pill({ children, tint }: { children: ReactNode; tint?: TintName }) {
  const t = useTheme();
  const bg = tint ? t.tints[tint].pill : t.colors.border;
  const fg = tint ? t.tints[tint].onPill : t.colors.text;
  return (
    <View
      style={{
        backgroundColor: bg,
        borderRadius: t.radius.pill,
        paddingHorizontal: 9,
        paddingVertical: 3,
        alignSelf: 'center',
      }}
    >
      <Text style={[t.type.pill, { color: fg, fontVariant: ['tabular-nums'] }]}>{children}</Text>
    </View>
  );
}

/**
 * Small labels: `soft` (white), `need` (soft red outline, for "Need: yoghurt"),
 * `action` (lime, for AI and actions only).
 */
export function Tag({
  children,
  kind = 'soft',
  tint,
}: {
  children: ReactNode;
  kind?: 'soft' | 'need' | 'action';
  /** A Member's or item's pastel, e.g. "✓ Bob" in Bob's colour. Overrides `kind`. */
  tint?: TintName;
}) {
  const t = useTheme();
  const look = tint
    ? { bg: t.tints[tint].bg, fg: t.tints[tint].text, border: 'transparent' }
    : {
        soft: { bg: t.colors.surface, fg: t.colors.text, border: 'transparent' },
        need: { bg: t.colors.surface, fg: t.colors.danger, border: t.colors.danger },
        action: { bg: t.colors.action, fg: t.colors.onAction, border: 'transparent' },
      }[kind];
  return (
    <View
      style={{
        backgroundColor: look.bg,
        borderColor: look.border,
        borderWidth: look.border === 'transparent' ? 0 : 1,
        borderRadius: t.radius.pill,
        paddingHorizontal: 9,
        paddingVertical: 3,
        alignSelf: 'flex-start',
      }}
    >
      <Text style={[t.type.pill, { color: look.fg }]}>{children}</Text>
    </View>
  );
}

const STATUS_TEXT: Record<StatusName, string> = {
  confirmed: 'Confirmed',
  estimated: 'Estimated',
  unknown: 'Unknown',
  runOut: 'Run out',
};

/** Cabinet status (ADR 0003). Unknown is dashed: "we genuinely don't know". */
export function StatusBadge({ status }: { status: StatusName }) {
  const t = useTheme();
  const s = t.status[status];
  return (
    <View
      style={{
        backgroundColor: s.bg,
        borderColor: s.border,
        borderWidth: 1.5,
        borderStyle: status === 'unknown' ? 'dashed' : 'solid',
        borderRadius: t.radius.pill,
        paddingHorizontal: 8,
        paddingVertical: 2,
        alignSelf: 'center',
      }}
    >
      <Text style={[t.type.pill, { color: s.fg }]}>{STATUS_TEXT[status]}</Text>
    </View>
  );
}
