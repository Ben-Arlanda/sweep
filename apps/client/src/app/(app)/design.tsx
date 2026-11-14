/**
 * The design system on one screen: every token and component, in the current theme.
 * Switch the device to dark mode (or "reduce motion") and check this page.
 *
 * Linked from the Account card in development builds only. It's harmless in production
 * (no data, no actions), so it isn't locked down beyond being signed in.
 */
import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { Avatar, AvatarStack } from '@/components/Avatar';
import { Checkbox } from '@/components/Checkbox';
import { Pill, StatusBadge, Tag } from '@/components/Pill';
import { Tile } from '@/components/Tile';
import { useToast } from '@/components/Toast';
import { Button, Card, Field, Highlight, Screen, SectionLabel, Text } from '@/components/ui';
import { TINT_NAMES } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

const SAMPLE_MEMBERS = [
  { id: 'alice', display_name: 'Alice' },
  { id: 'bob', display_name: 'Bob' },
  { id: 'sam-k', display_name: 'Sam K' },
];

export default function DesignScreen() {
  const t = useTheme();
  const toast = useToast();
  const [checked, setChecked] = useState(false);

  return (
    <Screen edges={['bottom', 'left', 'right']}>
      <Text variant="display">
        Zest + <Highlight>Kitchen Table</Highlight>
      </Text>
      <Text muted>
        Theme: {t.scheme}. Lime is for actions only; pastels give lists and people their own
        colour (ADR 0007).
      </Text>

      <SectionLabel>Colour roles</SectionLabel>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}>
        {(Object.entries(t.colors) as [string, string][]).map(([name, value]) => (
          <Swatch key={name} name={name} color={value} />
        ))}
      </View>

      <SectionLabel>Tints · card and matched pill</SectionLabel>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}>
        {TINT_NAMES.map((name) => (
          <View
            key={name}
            style={{
              backgroundColor: t.tints[name].bg,
              borderRadius: t.radius.md,
              padding: t.space.md,
              gap: t.space.sm,
              minWidth: 96,
            }}
          >
            <Text variant="label" style={{ color: t.tints[name].text }}>
              {name}
            </Text>
            <Pill tint={name}>1.5 kg</Pill>
          </View>
        ))}
      </View>

      <SectionLabel>Type</SectionLabel>
      <Card>
        <Text variant="display">Display 34</Text>
        <Text variant="title">Title 28</Text>
        <Text variant="heading">Heading 20</Text>
        <Text>Body 16. Urbanist for everything.</Text>
        <Text variant="label">Label 15</Text>
        <Text variant="caption" muted>
          Caption 13, muted
        </Text>
      </Card>

      <SectionLabel>Buttons</SectionLabel>
      <Button title="Primary: one per screen" onPress={() => {}} />
      <Button title="Secondary" variant="secondary" onPress={() => {}} />
      <Button title="Ghost" variant="ghost" onPress={() => {}} />
      <Button title="Danger" variant="danger" onPress={() => {}} />
      <Button title="Loading" loading onPress={() => {}} />
      <Button title="Disabled" disabled onPress={() => {}} />

      <SectionLabel>Pills, tags and Cabinet status</SectionLabel>
      <Card>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}>
          <Pill>neutral</Pill>
          <Tag>5 of 6 in Cabinet</Tag>
          <Tag kind="need">Need: yoghurt</Tag>
          <Tag kind="action">✦ Sweep AI</Tag>
        </View>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}>
          <StatusBadge status="confirmed" />
          <StatusBadge status="estimated" />
          <StatusBadge status="unknown" />
          <StatusBadge status="runOut" />
        </View>
      </Card>

      <SectionLabel>People</SectionLabel>
      <Card>
        <View style={{ flexDirection: 'row', gap: t.space.md, alignItems: 'center' }}>
          {SAMPLE_MEMBERS.map((m) => (
            <Avatar key={m.id} id={m.id} name={m.display_name} size={40} />
          ))}
          <AvatarStack members={SAMPLE_MEMBERS} />
        </View>
      </Card>

      <SectionLabel>Motion · tap to try</SectionLabel>
      <Card>
        <Pressable
          accessibilityRole="checkbox"
          accessibilityState={{ checked }}
          aria-checked={checked}
          onPress={() => setChecked((c) => !c)}
          style={{
            minHeight: t.touchTarget,
            flexDirection: 'row',
            alignItems: 'center',
            gap: t.space.md,
          }}
        >
          <Checkbox checked={checked} />
          <Text>The tick pops (off with Reduce Motion)</Text>
        </Pressable>
        <Button
          title="Show a toast"
          variant="secondary"
          onPress={() => toast({ tag: 'Cabinet', text: 'Added 1.5 kg chicken thigh' })}
        />
      </Card>

      <SectionLabel>Tiles</SectionLabel>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.md }}>
        <Tile href="/design" tint="butter" emoji="🧺" title="Weekly shop" subtitle="4 to buy" />
        <Tile href="/design" tint="mint" emoji="🥫" title="Cabinet" subtitle="12 tracked" />
      </View>

      <SectionLabel>Cards</SectionLabel>
      <Card>
        <Text variant="heading">Plain card</Text>
        <Text muted>White, soft shadow.</Text>
      </Card>
      <Card inverse>
        <Text variant="heading" style={{ color: t.colors.onInverse }}>
          Inverse card
        </Text>
        <Text style={{ color: t.colors.onInverse }}>The one strong anchor on a screen.</Text>
      </Card>

      <SectionLabel>Fields</SectionLabel>
      <Field label="Add an item" placeholder="e.g. 2 L milk" />
      <Field label="Amount" value="-1" error="Enter a number above 0" onChangeText={() => {}} />
    </Screen>
  );
}

function Swatch({ name, color }: { name: string; color: string }) {
  const t = useTheme();
  return (
    <View style={{ width: 96, gap: 4 }}>
      <View
        style={{
          height: 40,
          borderRadius: t.radius.sm,
          backgroundColor: color,
          borderWidth: 1,
          borderColor: t.colors.border,
        }}
      />
      <Text variant="caption">{name}</Text>
      <Text variant="caption" muted selectable>
        {color}
      </Text>
    </View>
  );
}
