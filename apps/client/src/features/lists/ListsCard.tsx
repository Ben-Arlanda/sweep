import { Link } from 'expo-router';
import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { Button, Card, ErrorText, Field, Text } from '@/components/ui';
import { useCreateList, useLists } from '@/lib/api/lists';
import { useTheme } from '@/theme/useTheme';

/** The Household's Shopping Lists, each with how many items are still to buy. */
export function ListsCard() {
  const t = useTheme();
  const lists = useLists();
  const createList = useCreateList();
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState('');

  function submit() {
    if (!name.trim()) return;
    createList.create(name.trim());
    setName('');
    setAdding(false);
  }

  return (
    <Card>
      <Text variant="heading">Shopping Lists</Text>
      <ErrorText message={lists.error?.message ?? createList.error?.message} />
      {lists.data?.map((list) => (
        <Link key={list.id} href={{ pathname: '/lists/[id]', params: { id: list.id } }} asChild>
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
            <Text variant="label">{list.name}</Text>
            <Text muted>
              {list.unchecked_count === 0 ? 'Nothing to buy' : `${list.unchecked_count} to buy`} ›
            </Text>
          </Pressable>
        </Link>
      ))}
      {adding ? (
        <View style={{ gap: t.space.sm }}>
          <Field
            label="List name"
            value={name}
            onChangeText={setName}
            onSubmitEditing={submit}
            autoFocus
            maxLength={60}
            returnKeyType="done"
          />
          <Button title="Create list" onPress={submit} disabled={!name.trim()} />
          <Button title="Cancel" variant="secondary" onPress={() => setAdding(false)} />
        </View>
      ) : (
        <Button title="New list" variant="secondary" onPress={() => setAdding(true)} />
      )}
    </Card>
  );
}
