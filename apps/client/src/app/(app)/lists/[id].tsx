import { useLocalSearchParams, useRouter } from 'expo-router';
import { useRef, useState } from 'react';
import { Pressable, View, type TextInputInstance } from 'react-native';
import Animated, { FadeInDown, ReduceMotion } from 'react-native-reanimated';

import { AvatarStack } from '@/components/Avatar';
import { Checkbox } from '@/components/Checkbox';
import { Pill, Tag } from '@/components/Pill';
import { useToast } from '@/components/Toast';
import {
  Button,
  Card,
  ErrorText,
  Field,
  Loading,
  Screen,
  SectionLabel,
  Text,
} from '@/components/ui';
import { useMembers } from '@/features/household/useMembers';
import { shoppingOrder } from '@/features/lists/listCache';
import type { Item, MemberOut } from '@/lib/api/client';
import { useIsOnline, useList, useListActions, usePendingListChanges } from '@/lib/api/lists';
import { tintFor } from '@/theme/tint';
import { useTheme } from '@/theme/useTheme';

/**
 * One Shopping List, made for using in a shop with one hand: big tap targets, the
 * add box at the top, and ticked items sinking into "In the trolley".
 */
export default function ListScreen() {
  const t = useTheme();
  const { id } = useLocalSearchParams<{ id: string }>();
  const list = useList(id);
  const actions = useListActions(id);
  const { members, byId } = useMembers();

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

  const summary = [
    toBuy.length === 0 ? 'Nothing left to buy' : `${toBuy.length} to buy`,
    inTrolley.length > 0 ? `${inTrolley.length} in the trolley` : null,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <Screen>
      <Card tint={tintFor(id)} style={{ gap: t.space.sm }}>
        <View style={{ flexDirection: 'row', alignItems: 'flex-start', gap: t.space.md }}>
          <Text variant="title" accessibilityRole="header" style={{ flex: 1 }}>
            {list.data.name}
          </Text>
          <AvatarStack members={members} size={28} />
        </View>
        <Text accessibilityLiveRegion="polite">{summary}</Text>
      </Card>

      <SyncStatus />
      <AddItem onAdd={actions.addItem} />
      <ErrorText message={actions.error?.message} />

      <View style={{ gap: t.space.sm }}>
        <SectionLabel>To buy</SectionLabel>
        {toBuy.length === 0 ? <Text muted>Nothing left to buy. Nice work.</Text> : null}
        {toBuy.map((item, i) => (
          <ItemRow key={item.id} item={item} index={i} actions={actions} members={byId} />
        ))}
      </View>

      {inTrolley.length > 0 ? (
        <View style={{ gap: t.space.sm }}>
          <SectionLabel>In the trolley</SectionLabel>
          {inTrolley.map((item, i) => (
            <ItemRow key={item.id} item={item} index={i} actions={actions} members={byId} />
          ))}
        </View>
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
      placeholder="e.g. 2 L milk"
      value={text}
      onChangeText={setText}
      onSubmitEditing={submit}
      submitBehavior="submit"
      returnKeyType="done"
      maxLength={200}
    />
  );
}

/**
 * One item. The whole row is the checkbox (a big target for one thumb in a shop); the
 * ✕ is a separate button. Ticking an item linked to an Ingredient also stocks the
 * Cabinet (ADR 0003), so we say so with a toast: that's the loop, made visible.
 */
function ItemRow({
  item,
  index,
  actions,
  members,
}: {
  item: Item;
  index: number;
  actions: Actions;
  members: Map<string, MemberOut>;
}) {
  const t = useTheme();
  const toast = useToast();
  const amount = [item.quantity, item.unit].filter(Boolean).join(' ');
  const tint = tintFor(item.ingredient?.name ?? item.text);
  const addedBy = item.added_by_member_id ? members.get(item.added_by_member_id) : undefined;
  const tickedBy = item.checked_by ? members.get(item.checked_by) : undefined;

  const caption = [
    item.ingredient ? `Cabinet: ${item.ingredient.name}` : null,
    addedBy ? `added by ${addedBy.display_name}` : null,
  ]
    .filter(Boolean)
    .join(' · ');

  function toggle() {
    const checked = !item.checked;
    // Send what the Member *sees* as the new state, not "toggle" (ADR 0004).
    actions.setChecked(item.id, checked);
    if (checked && item.ingredient) {
      toast({ tag: 'Cabinet', text: `Added ${amount ? `${amount} ` : ''}${item.ingredient.name}` });
    }
  }

  return (
    <Animated.View
      // Rows rise in one after another when the list opens. Capped so a long list
      // doesn't make the last row wait.
      entering={FadeInDown.delay(Math.min(index, 8) * t.motion.staggerMs)
        .springify()
        .damping(18)
        .reduceMotion(ReduceMotion.System)}
    >
      {/* Ticked rows aren't dimmed with opacity: that would drop the captions below AA
          contrast. The strike-through and the tick already say "done". */}
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          backgroundColor: t.colors.surface,
          borderRadius: t.radius.md,
          boxShadow: t.shadow.card,
        }}
      >
        {/* No custom label: the visible text ("Milk, added by Alice, ✓ Bob, 2 L") is the
            name, so voice control users can say exactly what they see (WCAG 2.5.3). */}
        <Pressable
          accessibilityRole="checkbox"
          accessibilityState={{ checked: item.checked }}
          aria-checked={item.checked}
          onPress={toggle}
          style={({ pressed }) => ({
            flex: 1,
            minHeight: t.touchTarget + 12,
            flexDirection: 'row',
            alignItems: 'center',
            gap: t.space.md,
            paddingVertical: t.space.sm,
            paddingLeft: t.space.sm,
            opacity: pressed ? 0.75 : 1,
          })}
        >
          {/* Thumbnail: the item's own pastel and initial. Decorative, so hidden from screen readers. */}
          <View
            aria-hidden
            style={{
              width: 40,
              height: 40,
              borderRadius: t.radius.sm + 4,
              backgroundColor: t.tints[tint].bg,
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Text variant="heading" style={{ color: t.tints[tint].text }}>
              {(item.ingredient?.name ?? item.text).charAt(0).toUpperCase()}
            </Text>
          </View>
          <View style={{ flex: 1, gap: 2 }}>
            <Text
              variant="label"
              muted={item.checked}
              style={{ textDecorationLine: item.checked ? 'line-through' : 'none' }}
            >
              {item.text}
            </Text>
            {caption ? (
              <Text variant="caption" muted numberOfLines={2}>
                {caption}
              </Text>
            ) : null}
            {item.checked && tickedBy ? (
              <Tag tint={tintFor(tickedBy.id)}>{`✓ ${tickedBy.display_name}`}</Tag>
            ) : null}
          </View>
          {amount ? <Pill tint={tint}>{amount}</Pill> : null}
          <Checkbox checked={item.checked} />
        </Pressable>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`Remove ${item.text}`}
          onPress={() => actions.deleteItem(item.id)}
          style={({ pressed }) => ({
            minWidth: t.touchTarget,
            minHeight: t.touchTarget,
            alignItems: 'center',
            justifyContent: 'center',
            opacity: pressed ? 0.5 : 1,
          })}
        >
          <Text muted>✕</Text>
        </Pressable>
      </View>
    </Animated.View>
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
  const t = useTheme();
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
        <Button title="Cancel" variant="ghost" onPress={() => setMode('idle')} />
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
        <Button title="Cancel" variant="ghost" onPress={() => setMode('idle')} />
      </Card>
    );
  }

  return (
    <View style={{ gap: t.space.sm, marginTop: t.space.lg }}>
      <Button
        title="Rename list"
        variant="secondary"
        onPress={() => {
          setDraft(name);
          setMode('rename');
        }}
      />
      <Button title="Delete list" variant="ghost" onPress={() => setMode('delete')} />
    </View>
  );
}
