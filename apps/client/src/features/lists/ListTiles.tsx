import { useState } from 'react';
import { View } from 'react-native';

import { Tile } from '@/components/Tile';
import { Button, Card, ErrorText, Field } from '@/components/ui';
import { useCreateList, useLists } from '@/lib/api/lists';
import { tintFor } from '@/theme/tint';
import { useTheme } from '@/theme/useTheme';

/** Each Shopping List as its own pastel tile on the home board. */
export function ListTiles() {
  const lists = useLists();
  return (
    <>
      <ErrorText message={lists.error?.message} />
      {lists.data?.map((list) => (
        <Tile
          key={list.id}
          href={{ pathname: '/lists/[id]', params: { id: list.id } }}
          tint={tintFor(list.id)}
          emoji="🧺"
          title={list.name}
          subtitle={
            list.unchecked_count === 0 ? 'Nothing to buy' : `${list.unchecked_count} to buy`
          }
        />
      ))}
    </>
  );
}

export function NewList() {
  const t = useTheme();
  const createList = useCreateList();
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState('');

  function submit() {
    if (!name.trim()) return;
    createList.create(name.trim());
    setName('');
    setAdding(false);
  }

  if (!adding) {
    return (
      <View style={{ gap: t.space.sm }}>
        <ErrorText message={createList.error?.message} />
        <Button title="+ New list" variant="secondary" onPress={() => setAdding(true)} />
      </View>
    );
  }

  return (
    <Card>
      <Field
        label="List name"
        value={name}
        onChangeText={setName}
        onSubmitEditing={submit}
        placeholder="e.g. BBQ Saturday"
        autoFocus
        maxLength={60}
        returnKeyType="done"
      />
      <Button title="Create list" onPress={submit} disabled={!name.trim()} />
      <Button title="Cancel" variant="ghost" onPress={() => setAdding(false)} />
    </Card>
  );
}
