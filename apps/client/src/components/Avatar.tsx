import { Text, View } from 'react-native';

import { initials, tintFor } from '@/theme/tint';
import { useTheme } from '@/theme/useTheme';

/**
 * A Member's initials on their own pastel. The colour comes from their id, so it's the
 * same everywhere. Avatars are decorative (the name is always written nearby or in the
 * group label), so screen readers skip them rather than reading out "A".
 */
export function Avatar({ id, name, size = 28 }: { id: string; name: string; size?: number }) {
  const t = useTheme();
  const tint = t.tints[tintFor(id)];
  return (
    <View
      aria-hidden
      style={{
        width: size,
        height: size,
        borderRadius: size / 2,
        backgroundColor: tint.bg,
        borderWidth: 2,
        borderColor: t.colors.surface,
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Text style={[t.type.pill, { color: tint.text, fontSize: Math.round(size * 0.4) }]}>
        {initials(name)}
      </Text>
    </View>
  );
}

/** Overlapping avatars, e.g. the Household in a header. */
export function AvatarStack({
  members,
  size = 28,
  max = 4,
}: {
  members: { id: string; display_name: string }[];
  size?: number;
  max?: number;
}) {
  return (
    <View
      accessible
      accessibilityRole="image"
      accessibilityLabel={members.map((m) => m.display_name).join(', ')}
      style={{ flexDirection: 'row' }}
    >
      {members.slice(0, max).map((m, i) => (
        <View key={m.id} style={{ marginLeft: i === 0 ? 0 : -size / 3.5 }}>
          <Avatar id={m.id} name={m.display_name} size={size} />
        </View>
      ))}
    </View>
  );
}
