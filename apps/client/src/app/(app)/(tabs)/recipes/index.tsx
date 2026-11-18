import { useState, type ReactNode } from 'react';
import { View } from 'react-native';

import { ChoiceChips } from '@/components/ChoiceChips';
import { Hero, HeroSearch } from '@/components/Hero';
import { Button, ErrorText, Loading, Screen, SectionLabel, Text } from '@/components/ui';
import { AddRecipeSheet } from '@/features/imports/AddRecipeSheet';
import { ruleBreakText } from '@/features/imports/ruleBreaks';
import { CourseTiles } from '@/features/recipes/CourseTiles';
import { COURSES, type Course } from '@/features/recipes/courses';
import { RecipeRow } from '@/features/recipes/RecipeRow';
import { ApiError } from '@/lib/api/client';
import { useImportedRecipes } from '@/lib/api/imports';
import { useDebounced, useRecipeBrowse, useRecipeSearch } from '@/lib/api/recipes';
import { useTheme } from '@/theme/useTheme';

// No "≤": the "Ready in" label already says it, and the four then fit one row at 320px.
const TIMES: { label: string; value: number | null }[] = [
  { label: 'Any time', value: null },
  { label: '20 min', value: 20 },
  { label: '30 min', value: 30 },
  { label: '45 min', value: 45 },
];

/**
 * The Recipe Knowledge Base. Type what you feel like ("quick vegetarian", "leftover
 * rice") and results are ranked by meaning; the time and Course filters are hard limits.
 */
export default function RecipesScreen() {
  const [text, setText] = useState('');
  const [maxMinutes, setMaxMinutes] = useState<number | null>(null);
  const [course, setCourse] = useState<Course | null>(null);
  const [favourites, setFavourites] = useState(false);
  const q = useDebounced(text.trim());
  const searching = q.length >= 2;
  const filters = { maxMinutes, course, favourites };

  const search = useRecipeSearch(q, filters);
  const browse = useRecipeBrowse(filters, !searching);

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
      {searching ? null : <YourRecipes />}
      <FilterGroup label="Show">
        <ChoiceChips
          label="Show"
          size="small"
          options={[
            { label: 'All recipes', value: false },
            { label: 'Favourites', value: true },
          ]}
          value={favourites}
          onChange={setFavourites}
        />
      </FilterGroup>
      <FilterGroup label="Ready in">
        <ChoiceChips
          label="Ready in"
          size="small"
          fill
          options={TIMES.map((o) => ({
            ...o,
            accessibilityLabel: o.value ? `Ready in ${o.label}` : o.label,
          }))}
          value={maxMinutes}
          onChange={setMaxMinutes}
        />
      </FilterGroup>
      <FilterGroup label="Course">
        <CourseTiles value={course} onChange={setCourse} />
      </FilterGroup>

      {searching ? (
        <SearchResults search={search} />
      ) : (
        <BrowseResults browse={browse} course={course} />
      )}
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
        <Text muted>Nothing fits those filters. Try a longer time or another course.</Text>
      ) : null}
      {search.data.map((r) => (
        <RecipeRow key={r.id} recipe={r} />
      ))}
    </View>
  );
}

/**
 * This Household's own recipes, with + Add. Hidden while searching: search already
 * includes them, ranked with everything else.
 */
function YourRecipes() {
  const t = useTheme();
  const mine = useImportedRecipes();
  const [adding, setAdding] = useState(false);
  return (
    <View style={{ gap: t.space.sm }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <SectionLabel>Your recipes</SectionLabel>
        <Button
          title="+ Add"
          accessibilityLabel="Add a recipe"
          variant="secondary"
          compact
          onPress={() => setAdding(true)}
        />
      </View>
      {mine.isError ? <ErrorText message={mine.error.message} /> : null}
      {mine.data?.length === 0 ? (
        <Text muted>
          Bring in the recipes you already cook: paste one, snap a cookbook page, or add a link.
        </Text>
      ) : null}
      {mine.data?.map((r) => (
        <RecipeRow key={r.id} recipe={r} note={ruleBreakText(r.rule_breaks)} />
      ))}
      {adding ? <AddRecipeSheet onClose={() => setAdding(false)} /> : null}
    </View>
  );
}

/** A filter row with its name above it. The name is visual only: each group names itself. */
function FilterGroup({ label, children }: { label: string; children: ReactNode }) {
  const t = useTheme();
  return (
    <View style={{ gap: t.space.xs }}>
      <Text variant="caption" muted aria-hidden>
        {label}
      </Text>
      {children}
    </View>
  );
}

function BrowseResults({
  browse,
  course,
}: {
  browse: ReturnType<typeof useRecipeBrowse>;
  course: Course | null;
}) {
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
      <SectionLabel>
        {course ? COURSES.find((c) => c.value === course)?.label : 'All recipes'}
      </SectionLabel>
      {recipes.length === 0 ? <Text muted>Nothing fits those filters yet.</Text> : null}
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
