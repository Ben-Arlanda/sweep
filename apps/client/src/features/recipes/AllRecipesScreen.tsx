import { useLocalSearchParams } from 'expo-router';
import { ChevronDown, Heart, Search } from 'lucide-react-native';
import { useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';

import { ChoiceChips } from '@/components/ChoiceChips';
import { Icon } from '@/components/Icon';
import { Sheet } from '@/components/Sheet';
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
import { useTheme } from '@/theme/useTheme';

import { CourseTiles } from './CourseTiles';
import { COURSES, type Course } from './courses';
import { cuisineName } from './kitchenMatch';
import { RecipeRow } from './RecipeRow';

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

type Open = 'time' | 'cuisine' | 'sort' | null;

/**
 * Every recipe (slice 6f, "See all"): search, Course tiles, Ready in, Cuisine,
 * Favourites and Sort. Browsing pages through; search is ordered by meaning instead.
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
          minHeight: t.touchTarget + 4,
          paddingHorizontal: t.space.lg,
          borderRadius: t.radius.pill,
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
          style={[t.type.body, { flex: 1, minHeight: t.touchTarget, color: t.colors.text }]}
        />
      </View>

      <CourseTiles value={course} onChange={setCourse} />

      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}>
        <FilterChip
          label={maxMinutes ? `≤ ${maxMinutes} min` : 'Ready in'}
          active={maxMinutes !== null}
          menu
          onPress={() => setOpen('time')}
        />
        <FilterChip
          label={cuisine ? (cuisineName(cuisine) ?? cuisine) : 'Cuisine'}
          active={cuisine !== null}
          menu
          onPress={() => setOpen('cuisine')}
        />
        <FilterChip
          label="Favourites"
          icon={Heart}
          active={favourites}
          onPress={() => setFavourites((f) => !f)}
        />
        {searching ? null : (
          <FilterChip
            label={SORTS.find((s) => s.value === sort)?.label ?? 'Sort'}
            accessibilityLabel={`Sort: ${SORTS.find((s) => s.value === sort)?.label}`}
            active={false}
            menu
            onPress={() => setOpen('sort')}
          />
        )}
      </View>

      {countText ? (
        <Text
          variant="label"
          accessibilityLiveRegion="polite"
          style={{ color: t.colors.onBackground }}
        >
          {countText}
        </Text>
      ) : null}

      <Results
        loading={searching ? search.isPending : browse.isPending}
        error={(searching ? search.error : browse.error)?.message ?? null}
        empty={shown.length === 0}
      />
      <View style={{ gap: t.space.sm }}>
        {shown.map((r) => (
          <RecipeRow key={r.id} recipe={r} />
        ))}
      </View>
      {!searching && browse.hasNextPage ? (
        <Button
          title="Show more"
          variant="secondary"
          loading={browse.isFetchingNextPage}
          onPress={() => browse.fetchNextPage()}
        />
      ) : null}

      {open === 'time' ? (
        <Sheet label="Ready in" title="Ready in" onClose={() => setOpen(null)}>
          <ChoiceChips
            label="Ready in"
            options={TIMES}
            value={maxMinutes}
            onChange={(v) => {
              setMaxMinutes(v);
              setOpen(null);
            }}
          />
        </Sheet>
      ) : null}
      {open === 'cuisine' ? (
        <Sheet label="Cuisine" title="Cuisine" onClose={() => setOpen(null)}>
          <ErrorText message={cuisines.error?.message} />
          <ChoiceChips
            label="Cuisine"
            options={[
              { label: 'Any', value: null as string | null },
              ...(cuisines.data ?? []).map((c) => ({ label: cuisineName(c) ?? c, value: c })),
            ]}
            value={cuisine}
            onChange={(v) => {
              setCuisine(v);
              setOpen(null);
            }}
          />
        </Sheet>
      ) : null}
      {open === 'sort' ? (
        <Sheet label="Sort" title="Sort by" onClose={() => setOpen(null)}>
          <ChoiceChips
            label="Sort by"
            options={SORTS}
            value={sort}
            onChange={(v) => {
              setSort(v);
              setOpen(null);
            }}
          />
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

/** A filter pill: deep green when it's narrowing the list; ▾ when it opens a menu. */
function FilterChip({
  label,
  accessibilityLabel,
  icon,
  active,
  menu,
  onPress,
}: {
  label: string;
  accessibilityLabel?: string;
  icon?: typeof Heart;
  active: boolean;
  menu?: boolean;
  onPress: () => void;
}) {
  const t = useTheme();
  const color = active ? t.colors.surface : t.colors.text;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? label}
      accessibilityState={menu ? { expanded: false } : { selected: active }}
      aria-pressed={menu ? undefined : active}
      onPress={onPress}
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        minHeight: t.touchTarget,
        paddingHorizontal: t.space.md,
        borderRadius: t.radius.pill,
        borderWidth: 1,
        borderColor: active ? t.colors.tabSelected : t.colors.border,
        backgroundColor: active ? t.colors.tabSelected : t.colors.surface,
      }}
    >
      {icon ? <Icon icon={icon} size={16} color={color} fill={active ? color : undefined} /> : null}
      <Text variant="label" style={{ color }}>
        {label}
      </Text>
      {menu ? <Icon icon={ChevronDown} size={16} color={color} /> : null}
    </Pressable>
  );
}
