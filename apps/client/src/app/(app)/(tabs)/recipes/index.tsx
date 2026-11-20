import { router } from 'expo-router';
import {
  BookOpen,
  ChevronRight,
  Heart,
  Plus,
  SlidersHorizontal,
  Sparkles,
  type LucideIcon,
} from 'lucide-react-native';
import { useState } from 'react';
import { View } from 'react-native';

import { HeroSearch } from '@/components/Hero';
import { Icon } from '@/components/Icon';
import { PageHeader } from '@/components/PageHeader';
import { PressableScale } from '@/components/PressableScale';
import { ErrorText, Loading, Screen, TAB_ROOT, Text } from '@/components/ui';
import { AddRecipeSheet } from '@/features/imports/AddRecipeSheet';
import { IdeaTile, KITCHEN_FIRST } from '@/features/recipes/IdeaTile';
import { RecipeRow } from '@/features/recipes/RecipeRow';
import { ApiError } from '@/lib/api/client';
import { useImportedRecipes } from '@/lib/api/imports';
import { useDinnerIdeas } from '@/lib/api/planning';
import { useDebounced, useRecipeSearch } from '@/lib/api/recipes';
import { PageColors } from '@/theme/PageColors';
import { useTheme } from '@/theme/useTheme';

/**
 * The Recipes tab (slice 6f, premium redesign): header with Add recipe and Food rules,
 * search, Find dinner ideas with a Favourites square beside it, what fits the Kitchen now
 * (with Browse all), and your added recipes. Typing a search swaps the sections for results,
 * ranked by meaning.
 */
/** The Find dinner ideas button and the Favourites square beside it share this height. */
const BIG = 56;

function RecipesScreenContent() {
  const t = useTheme();
  const [text, setText] = useState('');
  const [adding, setAdding] = useState(false);
  const q = useDebounced(text.trim());
  const searching = q.length >= 2;
  const search = useRecipeSearch(q, { maxMinutes: null, course: null });

  return (
    <Screen edges={TAB_ROOT}>
      <PageHeader
        icon={BookOpen}
        section="recipes"
        title="Recipes"
        right={
          <View style={{ flexDirection: 'row', gap: t.space.sm }}>
            <BoxButton
              icon={SlidersHorizontal}
              label="Food rules"
              role="link"
              onPress={() => router.push('/dietary-rules')}
            />
            <BoxButton icon={Plus} label="Add a recipe" onPress={() => setAdding(true)} />
          </View>
        }
      />
      <HeroSearch
        label="Search recipes"
        placeholder="e.g. quick vegetarian dinner"
        value={text}
        onChangeText={setText}
        autoCorrect={false}
        returnKeyType="search"
      />
      {searching ? (
        <SearchResults search={search} />
      ) : (
        <>
          <View style={{ flexDirection: 'row', gap: t.space.sm, marginTop: -t.space.xs }}>
            <PressableScale
              accessibilityRole="link"
              onPress={() => router.push('/dinner-ideas')}
              style={{
                flex: 1,
                minHeight: BIG,
                borderRadius: t.radius.lg,
                backgroundColor: t.colors.action,
                flexDirection: 'row',
                alignItems: 'center',
                justifyContent: 'center',
                gap: t.space.sm,
              }}
            >
              <Icon icon={Sparkles} size={20} color={t.colors.onAction} />
              <Text style={[t.type.label, { color: t.colors.onAction }]}>Find dinner ideas</Text>
            </PressableScale>
            <PressableScale
              accessibilityRole="link"
              accessibilityLabel="Favourites"
              onPress={() => router.push({ pathname: '/recipes/all', params: { favourites: '1' } })}
              style={{
                width: BIG,
                height: BIG,
                borderRadius: t.radius.lg,
                borderWidth: 1,
                borderColor: t.colors.border,
                backgroundColor: t.colors.surface,
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Icon icon={Heart} color={t.colors.text} />
            </PressableScale>
          </View>
          <Recommended />
          <YourRecipes />
        </>
      )}
      {adding ? <AddRecipeSheet onClose={() => setAdding(false)} /> : null}
    </Screen>
  );
}

/** A 44pt square icon button with a hairline box, for the header. */
function BoxButton({
  icon,
  label,
  role = 'button',
  onPress,
}: {
  icon: LucideIcon;
  label: string;
  role?: 'button' | 'link';
  onPress: () => void;
}) {
  const t = useTheme();
  return (
    <PressableScale
      accessibilityRole={role}
      accessibilityLabel={label}
      onPress={onPress}
      style={{
        width: t.touchTarget,
        height: t.touchTarget,
        borderRadius: t.radius.md,
        borderWidth: 1,
        borderColor: t.colors.border,
        backgroundColor: t.colors.surface,
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Icon icon={icon} color={t.colors.text} />
    </PressableScale>
  );
}

function Recommended() {
  const t = useTheme();
  const ideas = useDinnerIdeas(KITCHEN_FIRST, 'all', 4);
  if (ideas.isError) return null; // optional: browsing still works without it
  return (
    <View style={{ gap: t.space.sm }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Text
          variant="label"
          role="heading"
          aria-level={2}
          style={{ color: t.colors.onBackground, fontSize: 17, lineHeight: 22, flexShrink: 1 }}
        >
          Recommended for you
        </Text>
        <PressableScale
          accessibilityRole="link"
          onPress={() => router.push('/recipes/all')}
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            gap: 2,
            minHeight: t.touchTarget,
            paddingLeft: t.space.sm,
          }}
        >
          <Text style={{ color: t.colors.onBackgroundMuted }}>Browse all</Text>
          <Icon icon={ChevronRight} size={18} color={t.colors.onBackgroundMuted} />
        </PressableScale>
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
      <Text
        variant="label"
        role="heading"
        aria-level={2}
        style={{ color: t.colors.onBackground, fontSize: 17, lineHeight: 22 }}
      >
        Your added recipes
      </Text>
      {mine.data.map((r) => (
        <RecipeRow key={r.id} recipe={r} brief />
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
