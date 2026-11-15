import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { Sheet } from '@/components/Sheet';
import { Button, Field, Text } from '@/components/ui';
import { displayName } from '@/features/kitchen/format';
import type { Ingredient, Item } from '@/lib/api/client';
import { useIngredientSearch } from '@/lib/api/kitchen';
import { useTheme } from '@/theme/useTheme';

/**
 * "What is this in the Kitchen?" (ADR 0012). Every item gets an Ingredient when it's
 * added; when Sweep's guess is a near-miss ("Chocolate" made a new "chocolate" but you
 * meant dark chocolate), pick the right one here. The server remembers the choice for
 * this name, so the next "Chocolate" goes to dark chocolate too, and a ticked item's
 * stock moves with it.
 */
export function LinkSheet({
  item,
  onPick,
  onClose,
}: {
  item: Item;
  onPick: (ingredient: Ingredient | null) => void;
  onClose: () => void;
}) {
  const t = useTheme();
  const [query, setQuery] = useState(item.text);
  const results = useIngredientSearch(query);
  const current = item.ingredient?.id ?? null;

  function pick(ingredient: Ingredient | null) {
    onPick(ingredient);
    onClose();
  }

  return (
    <Sheet
      label={`Kitchen link for ${item.text}`}
      title={`What is ${item.text} in the Kitchen?`}
      onClose={onClose}
    >
      <Text variant="caption" muted>
        Sweep will remember this for {item.text} next time.
      </Text>
      <Field
        label="Search Ingredients"
        placeholder="e.g. dark chocolate"
        value={query}
        onChangeText={setQuery}
        autoCorrect={false}
        maxLength={80}
      />
      <View style={{ gap: t.space.xs }}>
        {query.trim().length >= 2 && results.data?.length === 0 ? (
          <Text variant="caption" muted>
            No Ingredient called that.
          </Text>
        ) : null}
        {results.data?.slice(0, 8).map((ingredient) => {
          const chosen = ingredient.id === current;
          return (
            <Pressable
              key={ingredient.id}
              accessibilityRole="button"
              accessibilityState={{ selected: chosen }}
              onPress={() => pick(ingredient)}
              style={({ pressed }) => ({
                minHeight: t.touchTarget,
                justifyContent: 'center',
                opacity: pressed ? 0.6 : 1,
              })}
            >
              <Text>
                {displayName(ingredient.name)}
                <Text muted>
                  {chosen ? ' · linked now' : ingredient.is_household_ingredient ? ' · yours' : ''}
                </Text>
              </Text>
            </Pressable>
          );
        })}
      </View>
      <View style={{ gap: t.space.sm }}>
        {current ? (
          <Button
            title="Don't add it to the Kitchen"
            variant="secondary"
            onPress={() => pick(null)}
          />
        ) : null}
        <Button title="Done" onPress={onClose} />
      </View>
    </Sheet>
  );
}
