import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { Button, Card, ErrorText, Field, Loading, Screen, Text } from '@/components/ui';
import { formatAmount, needsAttention, STATUS_LABEL } from '@/features/cabinet/format';
import { useCabinet, useCabinetActions, useIngredientSearch } from '@/lib/api/cabinet';
import type { components } from '@/lib/api/schema';
import { useTheme } from '@/theme/useTheme';

type Tracked = components['schemas']['CabinetItemOut'];
type Staple = components['schemas']['StapleOut'];
type Actions = ReturnType<typeof useCabinetActions>;

/**
 * What the Household has at home (ADR 0003). Tracked Ingredients show an amount and how
 * much to trust it; Staples are just "have" or "run out".
 */
export default function CabinetScreen() {
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

  return (
    <Screen>
      <AddToCabinet known={known} onAdd={(id) => actions.setAmount(id, null)} />
      <ErrorText message={actions.error?.message} />

      <Card>
        <Text variant="heading">Tracked</Text>
        <Text variant="caption" muted>
          Ticking items off a Shopping List adds them here.
        </Text>
        {tracked.length === 0 ? <Text muted>Nothing tracked yet.</Text> : null}
        {tracked.map((item) => (
          <TrackedRow key={item.ingredient.id} item={item} actions={actions} />
        ))}
      </Card>

      <Card>
        <Text variant="heading">Staples</Text>
        <Text variant="caption" muted>
          Assumed to be in the cupboard until someone says it&apos;s run out.
        </Text>
        {sortedStaples.map((staple) => (
          <StapleRow key={staple.ingredient.id} staple={staple} actions={actions} />
        ))}
      </Card>
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
                  {ingredient.name}
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
  const attention = needsAttention(item.status);

  if (editing) {
    const valid = draft.trim() === '' || Number(draft) > 0;
    return (
      <View style={{ gap: t.space.sm }}>
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
        <Button title="Cancel" variant="secondary" onPress={() => setEditing(false)} />
      </View>
    );
  }

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityHint="Edit amount"
      onPress={() => {
        setDraft(item.quantity ?? '');
        setEditing(true);
      }}
      style={({ pressed }) => ({
        minHeight: t.touchTarget,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: t.space.md,
        opacity: pressed ? 0.6 : 1,
      })}
    >
      <View style={{ flex: 1 }}>
        <Text variant="label">{item.ingredient.name}</Text>
        <Text variant="caption" muted={!attention} danger={attention}>
          {STATUS_LABEL[item.status]}
        </Text>
      </View>
      <Text muted={item.status !== 'confirmed'}>
        {item.status === 'confirmed' ? '' : '~'}
        {formatAmount(item.quantity, item.unit)}
      </Text>
    </Pressable>
  );
}

function StapleRow({ staple, actions }: { staple: Staple; actions: Actions }) {
  const t = useTheme();
  const id = staple.ingredient.id;
  return (
    <View
      style={{
        minHeight: t.touchTarget,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: t.space.sm,
      }}
    >
      <View style={{ flex: 1 }}>
        <Text>{staple.ingredient.name}</Text>
        {!staple.have ? (
          <Text variant="caption" danger>
            Run out
          </Text>
        ) : null}
      </View>
      <Button
        title={staple.have ? 'Ran out' : 'Got it'}
        variant="secondary"
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
