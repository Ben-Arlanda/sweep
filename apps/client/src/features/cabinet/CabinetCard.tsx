import { Link } from 'expo-router';
import { Pressable } from 'react-native';

import { Card, ErrorText, Text } from '@/components/ui';
import { useCabinet } from '@/lib/api/cabinet';
import { useTheme } from '@/theme/useTheme';

/** Home summary: what's tracked, and what needs a look. */
export function CabinetCard() {
  const t = useTheme();
  const cabinet = useCabinet();
  const tracked = cabinet.data?.tracked ?? [];
  const unknown = tracked.filter((i) => i.status === 'unknown').length;
  const ranOut = (cabinet.data?.staples ?? []).filter((s) => !s.have).length;

  const notes = [
    `${tracked.length} tracked`,
    unknown > 0 ? `${unknown} to check` : null,
    ranOut > 0 ? `${ranOut} Staples run out` : null,
  ].filter(Boolean);

  return (
    <Card>
      <Link href="/cabinet" asChild>
        <Pressable
          accessibilityRole="link"
          style={({ pressed }) => ({
            minHeight: t.touchTarget,
            flexDirection: 'row',
            alignItems: 'center',
            justifyContent: 'space-between',
            opacity: pressed ? 0.6 : 1,
          })}
        >
          <Text variant="heading">Cabinet</Text>
          <Text muted>{cabinet.data ? `${notes.join(' · ')} ›` : '›'}</Text>
        </Pressable>
      </Link>
      <ErrorText message={cabinet.error?.message} />
    </Card>
  );
}
