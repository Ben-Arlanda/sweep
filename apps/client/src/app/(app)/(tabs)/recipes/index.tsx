import { router } from 'expo-router';
import {
  ChefHat,
  ChevronRight,
  Heart,
  SlidersHorizontal,
  SquarePlus,
  type LucideIcon,
} from 'lucide-react-native';
import { useState } from 'react';
import { View } from 'react-native';

import { Hero, HeroSearch } from '@/components/Hero';
import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { ErrorText, Loading, Screen, Text } from '@/components/ui';
import { AddRecipeSheet } from '@/features/imports/AddRecipeSheet';
import { ruleBreakText } from '@/features/imports/ruleBreaks';
import { IdeaTile, KITCHEN_FIRST } from '@/features/recipes/IdeaTile';
import { RecipeRow } from '@/features/recipes/RecipeRow';
import { ApiError } from '@/lib/api/client';
import { useImportedRecipes } from '@/lib/api/imports';
import { useDinnerIdeas } from '@/lib/api/planning';
import { useDebounced, useRecipeSearch } from '@/lib/api/recipes';
import { PageColors } from '@/theme/PageColors';
import { useTheme } from '@/theme/useTheme';

/**
 * The Recipes tab (slice 6f): search, three ways in (Dinner ideas, Add recipe,
 * Favourites), shortcuts into All recipes, and what fits the Kitchen now. Typing a
 * search swaps the sections for results, ranked by meaning.
 */
function RecipesScreenContent() {
  const t = useTheme();
  const [text, setText] = useState('');
  const [adding, setAdding] = useState(false);
  const q = useDebounced(text.trim());
  const searching = q.length >= 2;
  const search = useRecipeSearch(q, { maxMinutes: null, course: null });

  return (
    <Screen
      hero={
        <Hero
          title={
            <>
              Find a recipe you’ll love to{' '}
              <Text
                variant="display"
                style={{
                  color: t.colors.onAction,
                  backgroundColor: t.colors.action,
                  borderRadius: t.radius.sm,
                }}
              >
                {' cook '}
              </Text>
            </>
          }
          subtitle="Search, browse and save recipes, or add your own."
          aside={
            <PressableScale
              accessibilityRole="link"
              accessibilityLabel="Food rules"
              onPress={() => router.push('/dietary-rules')}
              style={{
                width: t.touchTarget,
                height: t.touchTarget,
                borderRadius: t.radius.pill,
                backgroundColor: t.colors.surface,
                alignItems: 'center',
                justifyContent: 'center',
                alignSelf: 'flex-start',
              }}
            >
              <Icon icon={SlidersHorizontal} color={t.colors.text} />
            </PressableScale>
          }
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
      {searching ? (
        <SearchResults search={search} />
      ) : (
        <>
          <View style={{ flexDirection: 'row', gap: t.space.sm }}>
            <Tile
              icon={ChefHat}
              title="Dinner ideas"
              hint="Suggestions from Sweep"
              lime
              onPress={() => router.push('/dinner-ideas')}
            />
            <Tile
              icon={SquarePlus}
              title="Add recipe"
              hint="Paste, photo or link"
              onPress={() => setAdding(true)}
            />
            <Tile
              icon={Heart}
              title="Favourites"
              hint="Your hearted recipes"
              onPress={() => router.push({ pathname: '/recipes/all', params: { favourites: '1' } })}
            />
          </View>
          <Browse />
          <Recommended />
          <YourRecipes />
        </>
      )}
      {adding ? <AddRecipeSheet onClose={() => setAdding(false)} /> : null}
    </Screen>
  );
}

function Tile({
  icon,
  title,
  hint,
  lime,
  onPress,
}: {
  icon: LucideIcon;
  title: string;
  hint: string;
  lime?: boolean;
  onPress: () => void;
}) {
  const t = useTheme();
  return (
    <PressableScale
      accessibilityRole="button"
      accessibilityLabel={`${title}: ${hint}`}
      onPress={onPress}
      style={{
        flex: 1,
        minWidth: 0,
        alignItems: 'center',
        gap: 4,
        paddingVertical: t.space.md,
        paddingHorizontal: t.space.xs,
        borderRadius: t.radius.lg,
        backgroundColor: lime ? t.colors.action : t.colors.surface,
        boxShadow: lime ? undefined : t.shadow.card,
      }}
    >
      <Icon icon={icon} size={26} color={lime ? t.colors.onAction : t.colors.text} />
      <Text
        variant="label"
        style={{ textAlign: 'center', color: lime ? t.colors.onAction : t.colors.text }}
      >
        {title}
      </Text>
      <Text
        variant="caption"
        style={{ textAlign: 'center', color: lime ? t.colors.onAction : t.colors.textMuted }}
      >
        {hint}
      </Text>
    </PressableScale>
  );
}

/** "Browse recipes" with See all: the filters live on All recipes. */
function Browse() {
  const t = useTheme();
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
      <Text variant="title" role="heading" aria-level={2} style={{ color: t.colors.onBackground }}>
        Browse recipes
      </Text>
      <PressableScale
        accessibilityRole="link"
        accessibilityLabel="See all recipes"
        onPress={() => router.push('/recipes/all')}
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: 2,
          minHeight: t.touchTarget,
          paddingHorizontal: t.space.md,
          borderRadius: t.radius.pill,
          backgroundColor: t.colors.tabSelected,
        }}
      >
        <Text variant="label" style={{ color: t.colors.surface }}>
          See all
        </Text>
        <Icon icon={ChevronRight} size={16} color={t.colors.surface} />
      </PressableScale>
    </View>
  );
}

/** The best Kitchen Matches right now (the same code as Dinner Ideas), two across. */
function Recommended() {
  const t = useTheme();
  const ideas = useDinnerIdeas(KITCHEN_FIRST, 'all', 4);
  if (ideas.isError) return null; // optional: browsing still works without it
  return (
    <View style={{ gap: t.space.sm }}>
      <View>
        <Text
          variant="heading"
          role="heading"
          aria-level={2}
          style={{ color: t.colors.onBackground }}
        >
          Recommended for you
        </Text>
        <Text variant="caption" style={{ color: t.colors.onBackgroundMuted }}>
          From your Kitchen and Dietary Rules.
        </Text>
      </View>
      {ideas.isPending ? <Loading /> : null}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}>
        {ideas.data?.map((idea) => (
          <IdeaTile key={idea.id} idea={idea} path="/recipes/[id]" />
        ))}
      </View>
    </View>
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
            ? "Search isn't available right now. Clear the search box to browse."
            : search.error.message
        }
      />
    );
  }
  return (
    <View style={{ gap: t.space.sm }}>
      <Text
        variant="caption"
        style={{
          color: t.colors.onBackgroundMuted,
          fontFamily: t.fonts.bold,
          letterSpacing: 1.2,
          textTransform: 'uppercase',
        }}
      >
        Best matches
      </Text>
      {search.data.length === 0 ? (
        <Text style={{ color: t.colors.onBackgroundMuted }}>
          Nothing fits that. Try other words.
        </Text>
      ) : null}
      {search.data.map((r) => (
        <RecipeRow key={r.id} recipe={r} />
      ))}
    </View>
  );
}

/**
 * This Household's own recipes. Kept here because one that breaks a Dietary Rule is
 * left out of browsing, and this is where its note says why.
 */
function YourRecipes() {
  const t = useTheme();
  const mine = useImportedRecipes();
  if (!mine.data?.length) return mine.isError ? <ErrorText message={mine.error.message} /> : null;
  return (
    <View style={{ gap: t.space.sm }}>
      <Text variant="title" role="heading" aria-level={2} style={{ color: t.colors.onBackground }}>
        Your recipes
      </Text>
      {mine.data.map((r) => (
        <RecipeRow key={r.id} recipe={r} note={ruleBreakText(r.rule_breaks)} />
      ))}
    </View>
  );
}

/** The recipes tab on its own page colour (PAGE_COLORS). */
export default function RecipesScreen() {
  return (
    <PageColors page="recipes">
      <RecipesScreenContent />
    </PageColors>
  );
}
