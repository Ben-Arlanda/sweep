import { useEffect, useRef, useState } from 'react';
import { Modal, Platform, Pressable, ScrollView, View, type HostInstance } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ChoiceChips } from '@/components/ChoiceChips';
import { Button, ErrorText, Field, Text } from '@/components/ui';
import type { Shop } from '@/features/lists/shops';
import { useShopActions } from '@/lib/api/lists';
import { useTheme } from '@/theme/useTheme';

const ANY = 'any';

/**
 * A bottom sheet for choosing where to buy one item (ADR 0009). On a phone the thumb is
 * already at the bottom, so the choices are too. Picking a Shop applies it and closes
 * the sheet: one tap. The same sheet adds, renames and deletes Shops, so there's no
 * separate settings screen to find.
 *
 * `Modal` makes it a real dialog: screen readers stay inside it, and on web it traps
 * focus and closes on Escape (`onRequestClose`).
 */
export function ShopSheet({
  itemText,
  shopId,
  shops,
  onPick,
  onClose,
}: {
  itemText: string;
  shopId: string | null;
  shops: readonly Shop[];
  onPick: (shopId: string | null) => void;
  onClose: () => void;
}) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const actions = useShopActions();
  const [editing, setEditing] = useState(false);
  const [newName, setNewName] = useState('');
  const sheet = useRef<HostInstance>(null);
  const label = `Shop for ${itemText}`;

  // On web, Modal draws its own role="dialog" element but gives it no name, and has no
  // prop for one (Lighthouse: aria-dialog-name). Name it from inside once it's on screen.
  useEffect(() => {
    if (Platform.OS !== 'web') return;
    const node = sheet.current as unknown as HTMLElement | null;
    // aria-modal, not role: Modal only adds role="dialog" after it has opened.
    node?.closest('[aria-modal]')?.setAttribute('aria-label', label);
  }, [label]);

  function pick(value: string) {
    onPick(value === ANY ? null : value);
    onClose();
  }

  function addShop() {
    const name = newName.trim();
    if (!name) return;
    actions.addShop(name);
    setNewName('');
  }

  return (
    <Modal transparent animationType="slide" onRequestClose={onClose}>
      <View style={{ flex: 1, justifyContent: 'flex-end' }}>
        {/* The dimmed screen behind. Tapping it closes, like every sheet; it's hidden
            from screen readers, which use the Done button instead. */}
        <Pressable
          onPress={onClose}
          accessible={false}
          focusable={false}
          aria-hidden
          style={{
            position: 'absolute',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.55)',
          }}
        />
        <View
          ref={sheet}
          accessibilityViewIsModal
          style={{
            maxHeight: '85%',
            backgroundColor: t.colors.background,
            borderTopLeftRadius: t.radius.xl,
            borderTopRightRadius: t.radius.xl,
            paddingTop: t.space.sm,
            paddingBottom: Math.max(insets.bottom, t.space.lg),
          }}
        >
          {/* The grab handle: tells people this is a sheet. Decorative only. */}
          <View
            aria-hidden
            style={{
              alignSelf: 'center',
              width: 40,
              height: 5,
              borderRadius: 3,
              backgroundColor: t.colors.border,
              marginBottom: t.space.md,
            }}
          />
          <ScrollView
            contentContainerStyle={{
              paddingHorizontal: t.space.lg,
              gap: t.space.lg,
            }}
            keyboardShouldPersistTaps="handled"
          >
            <Text variant="heading" accessibilityRole="header">
              {editing ? 'Your shops' : `Where will you buy ${itemText}?`}
            </Text>

            {editing ? (
              <ShopEditor shops={shops} actions={actions} />
            ) : (
              <ChoiceChips
                label="Shop"
                value={shopId ?? ANY}
                onChange={pick}
                options={[
                  ...shops.map((shop) => ({
                    label: shop.name,
                    value: shop.id,
                  })),
                  { label: 'Any shop', value: ANY },
                ]}
              />
            )}

            <View style={{ gap: t.space.sm }}>
              <Field
                label="Add a shop"
                placeholder="e.g. IGA"
                value={newName}
                onChangeText={setNewName}
                onSubmitEditing={addShop}
                returnKeyType="done"
                maxLength={40}
              />
              <Button
                title="Add shop"
                variant="secondary"
                onPress={addShop}
                disabled={!newName.trim()}
              />
            </View>
            <ErrorText message={actions.error?.message} />

            <View style={{ gap: t.space.sm }}>
              <Button
                title={editing ? 'Back to choosing' : 'Rename or delete shops'}
                variant="ghost"
                onPress={() => setEditing(!editing)}
              />
              <Button title="Done" onPress={onClose} />
            </View>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

type ShopActions = ReturnType<typeof useShopActions>;

function ShopEditor({ shops, actions }: { shops: readonly Shop[]; actions: ShopActions }) {
  const t = useTheme();
  return (
    <View style={{ gap: t.space.md }}>
      <Text variant="caption" muted>
        Shops are shared with your Household. Deleting one keeps its items, as &quot;any shop&quot;.
      </Text>
      {shops.map((shop) => (
        <ShopRow key={shop.id} shop={shop} actions={actions} />
      ))}
    </View>
  );
}

function ShopRow({ shop, actions }: { shop: Shop; actions: ShopActions }) {
  const t = useTheme();
  const [renaming, setRenaming] = useState(false);
  const [name, setName] = useState(shop.name);

  if (renaming) {
    const save = () => {
      if (name.trim() && name.trim() !== shop.name) actions.renameShop(shop.id, name.trim());
      setRenaming(false);
    };
    return (
      <View style={{ gap: t.space.sm }}>
        <Field
          label={`New name for ${shop.name}`}
          value={name}
          onChangeText={setName}
          onSubmitEditing={save}
          maxLength={40}
          autoFocus
        />
        <View style={{ flexDirection: 'row', gap: t.space.sm }}>
          <Button title="Save" compact onPress={save} disabled={!name.trim()} />
          <Button title="Cancel" compact variant="ghost" onPress={() => setRenaming(false)} />
        </View>
      </View>
    );
  }

  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.sm,
        flexWrap: 'wrap',
      }}
    >
      <Text variant="label" style={{ flex: 1, minWidth: 120 }}>
        {shop.name}
      </Text>
      <Button
        title="Rename"
        compact
        variant="secondary"
        accessibilityLabel={`Rename ${shop.name}`}
        onPress={() => {
          setName(shop.name);
          setRenaming(true);
        }}
      />
      <Button
        title="Delete"
        compact
        variant="danger"
        accessibilityLabel={`Delete ${shop.name}`}
        onPress={() => actions.deleteShop(shop.id)}
      />
    </View>
  );
}
