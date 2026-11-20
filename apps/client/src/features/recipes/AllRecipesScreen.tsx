import { useLocalSearchParams } from 'expo-router';
import { Search, SlidersHorizontal } from 'lucide-react-native';
import { useState, type ReactNode } from 'react';
import { TextInput, View } from 'react-native';

import { ChoiceChips } from '@/components/ChoiceChips';
import { Icon } from '@/components/Icon';
import { Sheet } from '@/components/Sheet';
import { PressableScale } from '@/components/PressableScale';
import { Button, ErrorText, Loading, Screen, Text } from '@/components/ui';
import { useCuisines } from '@/lib/api/diet';
import {
  useDebounced,
  useRecipeBrowse,
  useRecipeCount,
  useRecipeSearch,
  type RecipeFilters,
  type RecipeSort,
} from '@/lib/api/recipes';
import { inputText } from '@/theme/inputText';
import { useTheme } from '@/theme/useTheme';

import { COURSES, type Course } from './courses';
import { cuisineName } from './kitchenMatch';
import { RecipeCard } from './RecipeCard';

const TIMES = [
  { label: 'Any time', value: null },
  { label: '20 min', value: 20 },
  { label: '30 min', value: 30 },
  { label: '45 min', value: 45 },
];

const SORTS: { label: string; value: RecipeSort; accessibilityLabel?: string }[] = [
  {
    label: 'Recommended',
    value: 'recommended',
    accessibilityLabel: 'Recommended: fewest things to buy first',
  },
  { label: 'Newest', value: 'newest' },
  { label: 'A–Z', value: 'title', accessibilityLabel: 'A to Z' },
];

type Open = 'filters' | null;

/**
 * Every recipe (slice 6f, "See all"): search, Course pills that slide, then the count
 * and a Filters sheet (Sort, Ready in, Cuisine, Favourites). Browsing pages through; search is ordered by meaning instead.
 * Opened with params from the Recipes screen's chips (`course`, `max`, `favourites`).
 */
export function AllRecipesScreen() {
  const t = useTheme();
  const params = useLocalSearchParams<{ course?: string; max?: string; favourites?: string }>();
  const [text, setText] = useState('');
  const [course, setCourse] = useState<Course | null>(
    COURSES.find((c) => c.value === params.course)?.value ?? null,
  );
  const [maxMinutes, setMaxMinutes] = useState<number | null>(
    TIMES.find((o) => String(o.value) === params.max)?.value ?? null,
  );
  const [favourites, setFavourites] = useState(params.favourites === '1');
  const [cuisine, setCuisine] = useState<string | null>(null);
  const [sort, setSort] = useState<RecipeSort>('recommended');
  const [open, setOpen] = useState<Open>(null);
  const cuisines = useCuisines();

  const q = useDebounced(text.trim());
  const searching = q.length >= 2;
  const filters: RecipeFilters = { maxMinutes, course, favourites, cuisine, sort };
  // How many filters narrow the list (the course pills are shown, so they don't count).
  const active = [maxMinutes !== null, cuisine !== null, favourites].filter(Boolean).length;
  const browse = useRecipeBrowse(filters, !searching);
  const search = useRecipeSearch(q, filters);
  const count = useRecipeCount(filters);

  const shown = searching ? (search.data ?? []) : (browse.data?.pages.flat() ?? []);
  const countText = searching
    ? `${search.data?.length ?? 0} best matches`
    : count.data !== undefined
      ? `${count.data} ${count.data === 1 ? 'recipe' : 'recipes'}`
      : null;

  return (
    <Screen>
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: t.space.sm,
          minHeight: 46,
          paddingHorizontal: t.space.md,
          borderRadius: t.radius.md,
          backgroundColor: t.colors.surface,
          borderWidth: 1,
          borderColor: t.colors.border,
        }}
      >
        <Icon icon={Search} size={20} color={t.colors.textMuted} />
        <TextInput
          accessibilityLabel="Search recipes"
          placeholder="Search recipes…"
          placeholderTextColor={t.colors.textMuted}
          value={text}
          onChangeText={setText}
          autoCorrect={false}
          returnKeyType="search"
          style={[
            inputText(t.type.body),
            { flex: 1, minHeight: t.touchTarget, color: t.colors.text },
          ]}
        />
      </View>

      <ChoiceChips
        label="Course"
        scroll
        value={course}
        onChange={setCourse}
        options={[
          { label: 'All', value: null as Course | null, accessibilityLabel: 'All courses' },
          ...COURSES.map((c) => ({ label: c.label, value: c.value as Course | null })),
        ]}
      />

      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginTop: -t.space.sm,
        }}
      >
        <Text style={{ color: t.colors.onBackgroundMuted }} accessibilityLiveRegion="polite">
          {countText}
        </Text>
        <PressableScale
          accessibilityRole="button"
          accessibilityLabel={active ? `Filters, ${active} on` : 'Filters'}
          onPress={() => setOpen('filters')}
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            gap: 6,
            minHeight: t.touchTarget,
            paddingLeft: t.space.sm,
          }}
        >
          <Icon icon={SlidersHorizontal} size={18} color={t.colors.text} />
          <Text variant="label">{active ? `Filters · ${active}` : 'Filters'}</Text>
        </PressableScale>
      </View>

      <Results
        loading={searching ? search.isPending : browse.isPending}
        error={(searching ? search.error : browse.error)?.message ?? null}
        empty={shown.length === 0}
      />
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10 }}>
        {shown.map((r) => (
          <RecipeCard key={r.id} recipe={r} />
        ))}
        {/* Keeps an odd last card half width instead of stretching across. */}
        {shown.length % 2 === 1 ? <View style={{ flexGrow: 1, flexBasis: 140 }} /> : null}
      </View>
      {!searching && browse.hasNextPage ? (
        <Button
          title="Show more"
          variant="secondary"
          loading={browse.isFetchingNextPage}
          onPress={() => browse.fetchNextPage()}
        />
      ) : null}

      {open === 'filters' ? (
        <Sheet label="Filters" title="Filters" onClose={() => setOpen(null)}>
          <View style={{ gap: t.space.lg }}>
            {searching ? null : (
              <FilterGroup title="Sort by">
                <ChoiceChips label="Sort by" options={SORTS} value={sort} onChange={setSort} />
              </FilterGroup>
            )}
            <FilterGroup title="Ready in">
              <ChoiceChips
                label="Ready in"
                options={TIMES}
                value={maxMinutes}
                onChange={setMaxMinutes}
              />
            </FilterGroup>
            <FilterGroup title="Cuisine">
              <ErrorText message={cuisines.error?.message} />
              <ChoiceChips
                label="Cuisine"
                scroll
                options={[
                  { label: 'Any', value: null as string | null },
                  ...(cuisines.data ?? []).map((c) => ({ label: cuisineName(c) ?? c, value: c })),
                ]}
                value={cuisine}
                onChange={setCuisine}
              />
            </FilterGroup>
            <FilterGroup title="Show">
              <ChoiceChips
                label="Show"
                options={[
                  { label: 'All recipes', value: false },
                  { label: 'Favourites', value: true },
                ]}
                value={favourites}
                onChange={setFavourites}
              />
            </FilterGroup>
            <View style={{ flexDirection: 'row', gap: t.space.sm }}>
              {active || sort !== 'recommended' ? (
                <View style={{ flex: 1 }}>
                  <Button
                    title="Clear all"
                    variant="secondary"
                    onPress={() => {
                      setMaxMinutes(null);
                      setCuisine(null);
                      setFavourites(false);
                      setSort('recommended');
                    }}
                  />
                </View>
              ) : null}
              <View style={{ flex: 1 }}>
                <Button
                  title={countText ? `Show ${countText}` : 'Done'}
                  onPress={() => setOpen(null)}
                />
              </View>
            </View>
          </View>
        </Sheet>
      ) : null}
    </Screen>
  );
}

function Results({
  loading,
  error,
  empty,
}: {
  loading: boolean;
  error: string | null;
  empty: boolean;
}) {
  const t = useTheme();
  if (loading) return <Loading />;
  if (error) return <ErrorText message={error} />;
  if (empty)
    return (
      <Text style={{ color: t.colors.onBackgroundMuted }}>
        Nothing fits those filters. Try a longer time or another course.
      </Text>
    );
  return null;
}

/** One group in the Filters sheet: a small heading over its options. */
function FilterGroup({ title, children }: { title: string; children: ReactNode }) {
  const t = useTheme();
  return (
    <View style={{ gap: t.space.sm }}>
      <Text variant="label" role="heading" aria-level={2}>
        {title}
      </Text>
      {children}
    </View>
  );
}
