import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { StatusBadge } from '@/components/Pill';
import { Button, Card, ErrorText, Field, Loading, Screen, SectionLabel, Text } from '@/components/ui';
import { displayName, formatAmount } from '@/features/cabinet/format';
import { useCabinet, useCabinetActions, useIngredientSearch } from '@/lib/api/cabinet';
import type { components } from '@/lib/api/schema';
import { tintFor } from '@/theme/tint';
import { useTheme } from '@/theme/useTheme';

type Tracked = components['schemas']['CabinetItemOut'];
type Staple = components['schemas']['StapleOut'];
type Actions = ReturnType<typeof useCabinetActions>;

/**
 * What the Household has at home (ADR 0003). Tracked Ingredients show an amount and how
 * much to trust it; Staples are just "have" or "run out".
 */
export default function CabinetScreen() {
  const t = useTheme();
  const cabinet = useCabinet();
  const actions = useCabinetActions();

  if (cabinet.isPending) return <Loading />;
  if (cabinet.isError) {
    return (
      <Screen>
        <ErrorText message={cabinet.error.message} />
        <Button title="Try again" onPress={() => cabinet.refetch()} />
      </Screen>
    );
  }

  const { tracked, staples } = cabinet.data;
  const known = new Set([...tracked, ...staples].map((x) => x.ingredient.id));
  // Run-out Staples first: they're the ones that need buying.
  const sortedStaples = [...staples].sort((a, b) => Number(a.have) - Number(b.have));

  const toCheck = tracked.filter((i) => i.status === 'unknown').length;
  const ranOut = staples.filter((s) => !s.have).length;

  return (
    <Screen>
      <Card tint="mint" style={{ gap: t.space.sm }}>
        <Text variant="title" accessibilityRole="header">
          Cabinet
        </Text>
        <Text>
          {[
            `${tracked.length} tracked`,
            toCheck ? `${toCheck} to check` : null,
            ranOut ? `${ranOut} run out` : null,
          ]
            .filter(Boolean)
            .join(' · ')}
        </Text>
      </Card>

      <AddToCabinet known={known} onAdd={(id) => actions.setAmount(id, null)} />
      <ErrorText message={actions.error?.message} />

      <View style={{ gap: t.space.sm }}>
        <SectionLabel>Tracked</SectionLabel>
        <Text variant="caption" muted>
          Ticking items off a Shopping List adds them here. Tap one to change the amount.
        </Text>
        {tracked.length === 0 ? <Text muted>Nothing tracked yet.</Text> : null}
        {tracked.map((item) => (
          <TrackedRow key={item.ingredient.id} item={item} actions={actions} />
        ))}
      </View>

      <View style={{ gap: t.space.sm }}>
        <SectionLabel>Staples</SectionLabel>
        <Text variant="caption" muted>
          Assumed to be in the cupboard until someone says it&apos;s run out.
        </Text>
        {sortedStaples.map((staple) => (
          <StapleRow key={staple.ingredient.id} staple={staple} actions={actions} />
        ))}
      </View>
    </Screen>
  );
}

function AddToCabinet({ known, onAdd }: { known: Set<string>; onAdd: (id: string) => void }) {
  const t = useTheme();
  const [query, setQuery] = useState('');
  const results = useIngredientSearch(query);
  const showing = query.trim().length >= 2;

  return (
    <View style={{ gap: t.space.sm }}>
      <Field
        label="Add to Cabinet"
        placeholder="Search, e.g. rice"
        value={query}
        onChangeText={setQuery}
        autoCorrect={false}
      />
      {showing && results.data?.length === 0 ? (
        <Text variant="caption" muted>
          No Ingredient called that yet.
        </Text>
      ) : null}
      {showing
        ? results.data?.slice(0, 6).map((ingredient) => {
            const already = known.has(ingredient.id);
            return (
              <Pressable
                key={ingredient.id}
                accessibilityRole="button"
                accessibilityState={{ disabled: already }}
                disabled={already}
                onPress={() => {
                  onAdd(ingredient.id);
                  setQuery('');
                }}
                style={({ pressed }) => ({
                  minHeight: t.touchTarget,
                  justifyContent: 'center',
                  opacity: already ? 0.5 : pressed ? 0.6 : 1,
                })}
              >
                <Text>
                  {displayName(ingredient.name)}
                  <Text muted> {already ? '· already in Cabinet' : '· add'}</Text>
                </Text>
              </Pressable>
            );
          })
        : null}
    </View>
  );
}

function TrackedRow({ item, actions }: { item: Tracked; actions: Actions }) {
  const t = useTheme();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(item.quantity ?? '');
  const id = item.ingredient.id;

  if (editing) {
    const valid = draft.trim() === '' || Number(draft) > 0;
    return (
      <Card>
        <Field
          label={`${item.ingredient.name}: amount in ${item.unit === 'count' ? 'items' : item.unit}`}
          value={draft}
          onChangeText={setDraft}
          keyboardType="decimal-pad"
          placeholder="Leave empty for 'some'"
          autoFocus
          error={valid ? null : 'Enter a number above 0'}
        />
        <Button
          title="Save"
          disabled={!valid}
          onPress={() => {
            actions.setAmount(id, draft.trim() === '' ? null : draft.trim());
            setEditing(false);
          }}
        />
        <Button
          title="Used it up"
          variant="secondary"
          onPress={() => {
            actions.usedUp(id);
            setEditing(false);
          }}
        />
        <Button
          title="Make it a Staple"
          variant="secondary"
          onPress={() => {
            actions.setStaple(id, true);
            setEditing(false);
          }}
        />
        <Button title="Cancel" variant="ghost" onPress={() => setEditing(false)} />
      </Card>
    );
  }

  const amount = `${item.status === 'confirmed' ? '' : 'about '}${formatAmount(item.quantity, item.unit)}`;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${displayName(item.ingredient.name)}, ${amount}, ${item.status}`}
      accessibilityHint="Edit amount"
      onPress={() => {
        setDraft(item.quantity ?? '');
        setEditing(true);
      }}
      style={({ pressed }) => [rowStyle(t), { opacity: pressed ? 0.75 : 1 }]}
    >
      <Thumb name={item.ingredient.name} />
      <View style={{ flex: 1, gap: 2 }}>
        <Text variant="label">{displayName(item.ingredient.name)}</Text>
        <Text variant="caption" muted>
          {amount}
        </Text>
      </View>
      <StatusBadge status={item.status} />
    </Pressable>
  );
}

function StapleRow({ staple, actions }: { staple: Staple; actions: Actions }) {
  const t = useTheme();
  const id = staple.ingredient.id;
  return (
    <View style={rowStyle(t)}>
      <Thumb name={staple.ingredient.name} />
      <View style={{ flex: 1, gap: 4 }}>
        <Text variant="label">{displayName(staple.ingredient.name)}</Text>
        {!staple.have ? (
          <View style={{ alignSelf: 'flex-start' }}>
            <StatusBadge status="runOut" />
          </View>
        ) : null}
      </View>
      <Button
        title={staple.have ? 'Ran out' : 'Got it'}
        variant={staple.have ? 'secondary' : 'primary'}
        compact
        onPress={() => actions.setStaple(id, !staple.have)}
      />
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`Stop treating ${staple.ingredient.name} as a Staple`}
        onPress={() => actions.notAStaple(id)}
        hitSlop={8}
        style={{
          minWidth: t.touchTarget,
          minHeight: t.touchTarget,
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Text muted>✕</Text>
      </Pressable>
    </View>
  );
}

function rowStyle(t: ReturnType<typeof useTheme>) {
  return {
    minHeight: t.touchTarget + 12,
    flexDirection: 'row' as const,
    alignItems: 'center' as const,
    gap: t.space.md,
    backgroundColor: t.colors.surface,
    borderRadius: t.radius.md,
    paddingVertical: t.space.sm,
    paddingHorizontal: t.space.sm,
    boxShadow: t.shadow.card,
  };
}

/** The Ingredient's own pastel and initial. Decorative, so hidden from screen readers. */
function Thumb({ name }: { name: string }) {
  const t = useTheme();
  const tint = t.tints[tintFor(name)];
  return (
    <View
      aria-hidden
      style={{
        width: 40,
        height: 40,
        borderRadius: t.radius.sm + 4,
        backgroundColor: tint.bg,
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Text variant="heading" style={{ color: tint.text }}>
        {name.charAt(0).toUpperCase()}
      </Text>
    </View>
  );
}
