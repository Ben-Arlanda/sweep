import { useState } from 'react';
import { View } from 'react-native';

import { ChoiceChips } from '@/components/ChoiceChips';
import { Sheet } from '@/components/Sheet';
import { Button, ErrorText, Field, Text } from '@/components/ui';
import type { Shop } from '@/features/lists/shops';
import { useShopActions } from '@/lib/api/lists';
import { useTheme } from '@/theme/useTheme';

const ANY = 'any';

/**
 * A bottom sheet for choosing where to buy one item (ADR 0009). Picking a Shop applies
 * it and closes the sheet: one tap. The same sheet adds, renames and deletes Shops, so
 * there's no separate settings screen to find.
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
  const actions = useShopActions();
  const [editing, setEditing] = useState(false);
  const [newName, setNewName] = useState('');

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
    <Sheet
      label={`Shop for ${itemText}`}
      title={editing ? 'Your shops' : `Where will you buy ${itemText}?`}
      onClose={onClose}
    >
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
        <Button title="Add shop" variant="secondary" onPress={addShop} disabled={!newName.trim()} />
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
    </Sheet>
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
