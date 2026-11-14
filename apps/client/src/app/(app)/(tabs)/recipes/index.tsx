import { useState } from 'react';
import { View } from 'react-native';

import { ChoiceChips } from '@/components/ChoiceChips';
import { Hero, HeroSearch } from '@/components/Hero';
import { Button, ErrorText, Loading, Screen, SectionLabel, Text } from '@/components/ui';
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
  const [text, setText] = useState('');
  const [maxMinutes, setMaxMinutes] = useState<number | null>(null);
  const q = useDebounced(text.trim());
  const searching = q.length >= 2;

  const search = useRecipeSearch(q, maxMinutes);
  const browse = useRecipeBrowse(maxMinutes, !searching);

  return (
    <Screen
      hero={
        <Hero
          title="What do you feel like cooking?"
          subtitle="Sweep finds recipes that fit, not just ones with the same words."
        >
          <HeroSearch
            label="Search recipes"
            placeholder="e.g. quick vegetarian dinner"
            value={text}
            onChangeText={setText}
            autoCorrect={false}
            returnKeyType="search"
          />
        </Hero>
      }
    >
      <ChoiceChips
        label="Ready in"
        options={TIMES.map((o) => ({
          ...o,
          label: o.value ? `≤ ${o.label}` : o.label,
          accessibilityLabel: o.value ? `Ready in ${o.label}` : o.label,
        }))}
        value={maxMinutes}
        onChange={setMaxMinutes}
      />

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
