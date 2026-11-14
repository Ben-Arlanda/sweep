import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { useRef, useState } from 'react';
import { Pressable, View, type TextInputInstance } from 'react-native';

import { Button, Card, ErrorText, Field, Loading, Screen, Text } from '@/components/ui';
import { shoppingOrder } from '@/features/lists/listCache';
import type { Item } from '@/lib/api/client';
import { useIsOnline, useList, useListActions, usePendingListChanges } from '@/lib/api/lists';
import { useTheme } from '@/theme/useTheme';

/**
 * One Shopping List, made for using in a shop with one hand: big tap targets, the
 * add box at the top, and ticked items sinking into "In the trolley".
 */
export default function ListScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const list = useList(id);
  const actions = useListActions(id);

  if (list.isPending) return <Loading />;
  if (list.isError) {
    return (
      <Screen>
        <ErrorText message={list.error.message} />
        <Button title="Try again" onPress={() => list.refetch()} />
      </Screen>
    );
  }

  const { toBuy, inTrolley } = shoppingOrder(list.data.items);

  return (
    <Screen>
      <Stack.Screen options={{ title: list.data.name }} />
      <SyncStatus />
      <AddItem onAdd={actions.addItem} />
      <ErrorText message={actions.error?.message} />

      <Card>
        <Text variant="heading">To buy</Text>
        {toBuy.length === 0 ? <Text muted>Nothing left to buy.</Text> : null}
        {toBuy.map((item) => (
          <ItemRow key={item.id} item={item} actions={actions} />
        ))}
      </Card>

      {inTrolley.length > 0 ? (
        <Card>
          <Text variant="heading">In the trolley</Text>
          {inTrolley.map((item) => (
            <ItemRow key={item.id} item={item} actions={actions} />
          ))}
        </Card>
      ) : null}

      <ListSettings name={list.data.name} actions={actions} />
    </Screen>
  );
}

type Actions = ReturnType<typeof useListActions>;

function AddItem({ onAdd }: { onAdd: (text: string) => void }) {
  const [text, setText] = useState('');
  const input = useRef<TextInputInstance>(null);

  function submit() {
    if (!text.trim()) return;
    onAdd(text.trim());
    setText('');
    input.current?.focus(); // keep the keyboard up for the next item
  }

  return (
    <Field
      ref={input}
      label="Add an item"
      placeholder="e.g. Milk"
      value={text}
      onChangeText={setText}
      onSubmitEditing={submit}
      submitBehavior="submit"
      returnKeyType="done"
      maxLength={200}
    />
  );
}

function ItemRow({ item, actions }: { item: Item; actions: Actions }) {
  const t = useTheme();
  const amount = [item.quantity, item.unit].filter(Boolean).join(' ');

  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.sm }}>
      <Pressable
        accessibilityRole="checkbox"
        accessibilityState={{ checked: item.checked }}
        accessibilityLabel={item.text}
        // Send what the Member *sees* as the new state, not "toggle" (ADR 0004).
        onPress={() => actions.setChecked(item.id, !item.checked)}
        style={{
          flex: 1,
          minHeight: t.touchTarget,
          flexDirection: 'row',
          alignItems: 'center',
          gap: t.space.md,
        }}
      >
        <View
          style={{
            width: 24,
            height: 24,
            borderRadius: t.radius.sm,
            borderWidth: 2,
            borderColor: item.checked ? t.colors.primary : t.colors.border,
            backgroundColor: item.checked ? t.colors.primary : 'transparent',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {item.checked ? <Text style={{ color: t.colors.onPrimary }}>✓</Text> : null}
        </View>
        <Text
          muted={item.checked}
          style={{
            flex: 1,
            textDecorationLine: item.checked ? 'line-through' : 'none',
          }}
        >
          {item.text}
          {amount ? <Text muted> · {amount}</Text> : null}
        </Text>
      </Pressable>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`Remove ${item.text}`}
        onPress={() => actions.deleteItem(item.id)}
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

/** Tells the Member their taps are safe even when the signal isn't. */
function SyncStatus() {
  const pending = usePendingListChanges();
  const online = useIsOnline();
  if (pending === 0) return null;
  return (
    <Text variant="caption" muted accessibilityLiveRegion="polite">
      {online
        ? 'Saving…'
        : `Offline. ${pending} ${pending === 1 ? 'change' : 'changes'} will sync when you're back online.`}
    </Text>
  );
}

function ListSettings({ name, actions }: { name: string; actions: Actions }) {
  const router = useRouter();
  const [mode, setMode] = useState<'idle' | 'rename' | 'delete'>('idle');
  const [draft, setDraft] = useState(name);

  if (mode === 'rename') {
    return (
      <Card>
        <Field label="List name" value={draft} onChangeText={setDraft} maxLength={60} autoFocus />
        <Button
          title="Save"
          disabled={!draft.trim()}
          onPress={() => {
            actions.rename(draft.trim());
            setMode('idle');
          }}
        />
        <Button title="Cancel" variant="secondary" onPress={() => setMode('idle')} />
      </Card>
    );
  }

  if (mode === 'delete') {
    return (
      <Card>
        <Text danger>Delete &quot;{name}&quot; and everything on it, for the whole Household?</Text>
        <Button
          title="Yes, delete list"
          variant="danger"
          onPress={async () => {
            await actions.deleteList();
            router.back();
          }}
        />
        <Button title="Cancel" variant="secondary" onPress={() => setMode('idle')} />
      </Card>
    );
  }

  return (
    <View style={{ gap: 8 }}>
      <Button
        title="Rename list"
        variant="secondary"
        onPress={() => {
          setDraft(name);
          setMode('rename');
        }}
      />
      <Button title="Delete list" variant="danger" onPress={() => setMode('delete')} />
    </View>
  );
}
