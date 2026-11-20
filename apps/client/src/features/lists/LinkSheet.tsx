import { useState } from 'react';
import { View } from 'react-native';

import { Sheet } from '@/components/Sheet';
import { PressableScale } from '@/components/PressableScale';
import { Button, Field, Text } from '@/components/ui';
import { displayName } from '@/features/kitchen/format';
import type { Ingredient } from '@/lib/api/client';
import { useIngredientSearch } from '@/lib/api/kitchen';
import { useTheme } from '@/theme/useTheme';

/**
 * "What is this in the Kitchen?" (ADR 0012). Every item gets an Ingredient when it's
 * added; when Sweep's guess is a near-miss ("Chocolate" made a new "chocolate" but you
 * meant dark chocolate), pick the right one here. The server remembers the choice for
 * this name, so the next "Chocolate" goes to dark chocolate too, and a ticked item's
 * stock moves with it.
 *
 * Imported Recipe lines use it too (slice 4d), with their own wording and no "Don't add".
 */
export function LinkSheet({
  name,
  current: currentIngredient,
  onPick,
  onClose,
  title = `What is ${name} in the Kitchen?`,
  hint = `Sweep will remember this for ${name} next time.`,
  allowNone = true,
  startQuery = name,
  label = `Kitchen link for ${name}`,
}: {
  name: string; // what the Member wrote: "Chocolate", "2 shallots, sliced"
  current: Ingredient | null;
  onPick: (ingredient: Ingredient | null) => void;
  onClose: () => void;
  title?: string;
  hint?: string;
  allowNone?: boolean;
  startQuery?: string; // what the search box starts with
  label?: string; // the dialog's name for screen readers
}) {
  const t = useTheme();
  const [query, setQuery] = useState(startQuery);
  const results = useIngredientSearch(query);
  const current = currentIngredient?.id ?? null;

  function pick(ingredient: Ingredient | null) {
    onPick(ingredient);
    onClose();
  }

  return (
    <Sheet label={label} title={title} onClose={onClose}>
      <Text variant="caption" muted>
        {hint}
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
            <PressableScale
              key={ingredient.id}
              accessibilityRole="button"
              accessibilityState={{ selected: chosen }}
              onPress={() => pick(ingredient)}
              style={{
                minHeight: t.touchTarget,
                justifyContent: 'center',
              }}
            >
              <Text>
                {displayName(ingredient.name)}
                <Text muted>
                  {chosen ? ' · linked now' : ingredient.is_household_ingredient ? ' · yours' : ''}
                </Text>
              </Text>
            </PressableScale>
          );
        })}
      </View>
      <View style={{ gap: t.space.sm }}>
        {current && allowNone ? (
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
