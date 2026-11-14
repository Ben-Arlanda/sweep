import { useState } from 'react';
import { Pressable, View } from 'react-native';

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
import { RecipeRow } from '@/features/recipes/RecipeRow';
import { ApiError } from '@/lib/api/client';
import { useDebounced, useRecipeBrowse, useRecipeSearch } from '@/lib/api/recipes';
import { useTheme } from '@/theme/useTheme';

const TIMES: { label: string; value: number | null }[] = [
  { label: 'Any time', value: null },
  { label: '20 min', value: 20 },
  { label: '30 min', value: 30 },
  { label: '45 min', value: 45 },
];

/**
 * The Recipe Knowledge Base. Type what you feel like ("quick vegetarian", "leftover
 * rice") and results are ranked by meaning; the time chips are hard limits.
 */
export default function RecipesScreen() {
  const t = useTheme();
  const [text, setText] = useState('');
  const [maxMinutes, setMaxMinutes] = useState<number | null>(null);
  const q = useDebounced(text.trim());
  const searching = q.length >= 2;

  const search = useRecipeSearch(q, maxMinutes);
  const browse = useRecipeBrowse(maxMinutes, !searching);

  return (
    <Screen>
      <Card tint="butter" style={{ gap: t.space.sm }}>
        <Text variant="title" accessibilityRole="header">
          Recipes
        </Text>
        <Text>
          Say what you feel like. Sweep finds recipes that fit, not just ones with the same words.
        </Text>
      </Card>

      <Field
        label="Search recipes"
        placeholder="e.g. quick vegetarian dinner"
        value={text}
        onChangeText={setText}
        autoCorrect={false}
        returnKeyType="search"
      />

      <View
        accessibilityRole="radiogroup"
        accessibilityLabel="Ready in"
        style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}
      >
        {TIMES.map((option) => {
          const selected = option.value === maxMinutes;
          return (
            <Pressable
              key={option.label}
              accessibilityRole="radio"
              aria-checked={selected}
              accessibilityLabel={option.value ? `Ready in ${option.label}` : option.label}
              onPress={() => setMaxMinutes(option.value)}
              style={({ pressed }) => ({
                minHeight: t.touchTarget,
                paddingHorizontal: t.space.md,
                borderRadius: t.radius.pill,
                justifyContent: 'center',
                backgroundColor: selected ? t.colors.inverse : t.colors.surface,
                borderWidth: 1,
                borderColor: selected ? t.colors.inverse : t.colors.border,
                opacity: pressed ? 0.75 : 1,
              })}
            >
              <Text
                variant="label"
                style={{ color: selected ? t.colors.onInverse : t.colors.text }}
              >
                {option.value ? `≤ ${option.label}` : option.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {searching ? <SearchResults search={search} /> : <BrowseResults browse={browse} />}
    </Screen>
  );
}

function SearchResults({ search }: { search: ReturnType<typeof useRecipeSearch> }) {
  const t = useTheme();
  if (search.isPending) return <Loading />;
  if (search.isError) {
    const unavailable = search.error instanceof ApiError && search.error.status === 503;
    return (
      <ErrorText
        message={
          unavailable
            ? "Search isn't available right now. Clear the search box to browse all recipes."
            : search.error.message
        }
      />
    );
  }
  return (
    <View style={{ gap: t.space.sm }}>
      <SectionLabel>Best matches</SectionLabel>
      {search.data.length === 0 ? (
        <Text muted>Nothing fits that time limit. Try a longer one.</Text>
      ) : null}
      {search.data.map((r) => (
        <RecipeRow key={r.id} recipe={r} />
      ))}
    </View>
  );
}

function BrowseResults({ browse }: { browse: ReturnType<typeof useRecipeBrowse> }) {
  const t = useTheme();
  if (browse.isPending) return <Loading />;
  if (browse.isError) {
    return (
      <>
        <ErrorText message={browse.error.message} />
        <Button title="Try again" onPress={() => browse.refetch()} />
      </>
    );
  }
  const recipes = browse.data.pages.flat();
  return (
    <View style={{ gap: t.space.sm }}>
      <SectionLabel>All recipes</SectionLabel>
      {recipes.length === 0 ? <Text muted>No recipes that quick yet.</Text> : null}
      {recipes.map((r) => (
        <RecipeRow key={r.id} recipe={r} />
      ))}
      {browse.hasNextPage ? (
        <Button
          title="Show more"
          variant="secondary"
          loading={browse.isFetchingNextPage}
          onPress={() => browse.fetchNextPage()}
        />
      ) : null}
    </View>
  );
}
