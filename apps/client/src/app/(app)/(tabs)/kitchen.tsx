import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { ChoiceChips } from '@/components/ChoiceChips';
import { FoodThumb } from '@/components/FoodThumb';
import { Hero, HeroSearch } from '@/components/Hero';
import { StatusBadge } from '@/components/Pill';
import { useToast } from '@/components/Toast';
import {
  Button,
  Card,
  ErrorText,
  Field,
  Loading,
  Screen,
  SectionLabel,
  TAB_ROOT,
  Text,
} from '@/components/ui';
import { AddFromPhotoSheet } from '@/features/kitchen/AddFromPhotoSheet';
import { newIngredientName } from '@/features/kitchen/addNew';
import { displayName, formatAmount } from '@/features/kitchen/format';
import { usePlaceFilter } from '@/features/kitchen/placeFilter';
import {
  byPlace,
  PLACES,
  type Place,
  type PlaceFilter,
  type Staple,
  type Tracked,
} from '@/features/kitchen/places';
import { useKitchen, useKitchenActions, useIngredientSearch } from '@/lib/api/kitchen';
import { ingredientEmoji } from '@/theme/foodEmoji';
import { tintFor } from '@/theme/tint';
import { useTheme } from '@/theme/useTheme';

type Actions = ReturnType<typeof useKitchenActions>;

/**
 * What the Household has at home, grouped by where it lives: Fridge, Freezer, Cupboard
 * (ADR 0011). Tracked Ingredients show an amount and how much to trust it (ADR 0003);
 * Staples are just "have" or "run out". Tap any item to change it or move it.
 */
export default function KitchenScreen() {
  const t = useTheme();
  const kitchen = useKitchen();
  const actions = useKitchenActions();
  const [query, setQuery] = useState(''); // the "Add to Kitchen" search in the hero
  const [filter, setFilter] = usePlaceFilter();
  const [photoSheet, setPhotoSheet] = useState(false);

  if (kitchen.isPending) return <Loading />;
  if (kitchen.isError) {
    return (
      <Screen edges={TAB_ROOT}>
        <ErrorText message={kitchen.error.message} />
        <Button title="Try again" onPress={() => kitchen.refetch()} />
      </Screen>
    );
  }

  const { tracked, staples } = kitchen.data;
  const known = new Set([...tracked, ...staples].map((x) => x.ingredient.id));
  const sections = byPlace({ tracked, staples }, filter);

  const toCheck = tracked.filter((i) => i.status === 'unknown').length;
  const ranOut = staples.filter((s) => !s.have).length;

  return (
    <Screen
      hero={
        <Hero
          title="Kitchen"
          subtitle={[
            `${tracked.length} tracked`,
            toCheck ? `${toCheck} to check` : null,
            ranOut ? `${ranOut} run out` : null,
          ]
            .filter(Boolean)
            .join(' · ')}
        >
          <HeroSearch
            label="Add to Kitchen"
            placeholder="Add to Kitchen, e.g. rice"
            value={query}
            onChangeText={setQuery}
            autoCorrect={false}
          />
        </Hero>
      }
    >
      <AddMatches
        query={query}
        known={known}
        onAdd={(id) => {
          actions.setAmount(id, null);
          setQuery('');
        }}
        onAddNew={(name) => {
          actions.addNew(name);
          setQuery('');
        }}
      />
      <ErrorText message={actions.error?.message} />
      <Button title="Add from photo" variant="secondary" onPress={() => setPhotoSheet(true)} />

      <ChoiceChips<PlaceFilter>
        label="Show"
        value={filter}
        onChange={setFilter}
        options={[
          { label: 'All', value: 'all', accessibilityLabel: 'All places' },
          ...PLACES.map(({ place, label }) => ({ label, value: place })),
        ]}
      />
      <Text variant="caption" muted>
        Ticking items off the Shopping List adds them here, or add a photo of things laid out. Tap
        one to change it or move it.
      </Text>

      {sections.length === 0 ? <Text muted>Nothing in your Kitchen yet.</Text> : null}
      {sections.map((section) => (
        <View key={section.place} style={{ gap: t.space.sm }}>
          <SectionLabel>{section.label}</SectionLabel>
          {section.tracked.length + section.staples.length === 0 ? (
            <Text muted>Nothing in the {section.label.toLowerCase()} yet.</Text>
          ) : null}
          {section.tracked.map((item) => (
            <TrackedRow key={item.ingredient.id} item={item} actions={actions} />
          ))}
          {section.staples.map((staple) => (
            <StapleRow key={staple.ingredient.id} staple={staple} actions={actions} />
          ))}
        </View>
      ))}
      {photoSheet ? (
        <AddFromPhotoSheet
          start={filter === 'all' ? 'fridge' : filter}
          onClose={() => setPhotoSheet(false)}
        />
      ) : null}
    </Screen>
  );
}

/**
 * Ingredients matching the hero's "Add to Kitchen" search, each one tap to add. When
 * nothing is called exactly what was typed, the last row offers to add it anyway, as a
 * Household Ingredient (ADR 0012): the Kitchen takes anything.
 */
function AddMatches({
  query,
  known,
  onAdd,
  onAddNew,
}: {
  query: string;
  known: Set<string>;
  onAdd: (id: string) => void;
  onAddNew: (name: string) => void;
}) {
  const t = useTheme();
  const results = useIngredientSearch(query);
  const showing = query.trim().length >= 2;
  if (!showing) return null;
  // Wait for this query's results (not the previous query's, kept on screen meanwhile),
  // so we never offer to add something search is about to show.
  const settled = results.isSuccess && !results.isPlaceholderData;
  const offer = settled
    ? newIngredientName(
        query,
        results.data.map((i) => i.name),
      )
    : null;

  return (
    <View style={{ gap: t.space.sm }}>
      <SectionLabel>Add to Kitchen</SectionLabel>
      {results.data?.slice(0, 6).map((ingredient) => {
        const already = known.has(ingredient.id);
        return (
          <Pressable
            key={ingredient.id}
            accessibilityRole="button"
            accessibilityState={{ disabled: already }}
            disabled={already}
            onPress={() => onAdd(ingredient.id)}
            style={({ pressed }) => ({
              minHeight: t.touchTarget,
              justifyContent: 'center',
              opacity: already ? 0.5 : pressed ? 0.6 : 1,
            })}
          >
            <Text>
              {displayName(ingredient.name)}
              <Text muted> {already ? '· already in Kitchen' : '· add'}</Text>
            </Text>
          </Pressable>
        );
      })}
      {offer ? (
        <Pressable
          accessibilityRole="button"
          onPress={() => onAddNew(offer)}
          style={({ pressed }) => ({
            minHeight: t.touchTarget,
            justifyContent: 'center',
            opacity: pressed ? 0.6 : 1,
          })}
        >
          <Text>
            {`Add "${displayName(offer)}"`}
            <Text muted> · new to your Kitchen</Text>
          </Text>
        </Pressable>
      ) : null}
    </View>
  );
}

function TrackedRow({ item, actions }: { item: Tracked; actions: Actions }) {
  const t = useTheme();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(item.quantity ?? '');
  const id = item.ingredient.id;

  if (editing) {
    const valid = draft.trim() === '' || Number(draft) > 0;
    return (
      <Card>
        <Field
          label={`${item.ingredient.name}: amount in ${item.unit === 'count' ? 'items' : item.unit}`}
          value={draft}
          onChangeText={setDraft}
          keyboardType="decimal-pad"
          placeholder="Leave empty for 'some'"
          autoFocus
          error={valid ? null : 'Enter a number above 0'}
        />
        <Button
          title="Save"
          disabled={!valid}
          onPress={() => {
            actions.setAmount(id, draft.trim() === '' ? null : draft.trim());
            setEditing(false);
          }}
        />
        <Button
          title="Used it up"
          variant="secondary"
          onPress={() => {
            actions.usedUp(id);
            setEditing(false);
          }}
        />
        <KeepIn
          name={item.ingredient.name}
          place={item.place}
          onMove={(place) => {
            actions.setPlace(id, place);
            setEditing(false);
          }}
        />
        <Button
          title="Make it a Staple"
          variant="secondary"
          onPress={() => {
            actions.setStaple(id, true);
            setEditing(false);
          }}
        />
        <Button title="Cancel" variant="ghost" onPress={() => setEditing(false)} />
      </Card>
    );
  }

  const amount = `${item.status === 'confirmed' ? '' : 'about '}${formatAmount(item.quantity, item.unit)}`;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${displayName(item.ingredient.name)}, ${amount}, ${item.status}`}
      accessibilityHint="Edit amount or move it"
      onPress={() => {
        setDraft(item.quantity ?? '');
        setEditing(true);
      }}
      style={({ pressed }) => [rowStyle(t), { opacity: pressed ? 0.75 : 1 }]}
    >
      <FoodThumb emoji={ingredientEmoji(item.ingredient)} tint={tintFor(item.ingredient.name)} />
      <View style={{ flex: 1, gap: 2 }}>
        <Text variant="label">{displayName(item.ingredient.name)}</Text>
        <Text variant="caption" muted>
          {amount}
        </Text>
      </View>
      <StatusBadge status={item.status} />
    </Pressable>
  );
}

function StapleRow({ staple, actions }: { staple: Staple; actions: Actions }) {
  const t = useTheme();
  const [editing, setEditing] = useState(false);
  const id = staple.ingredient.id;
  const name = displayName(staple.ingredient.name);

  if (editing) {
    return (
      <Card>
        <Text variant="label">{name}</Text>
        <KeepIn
          name={staple.ingredient.name}
          place={staple.place}
          onMove={(place) => {
            actions.setPlace(id, place);
            setEditing(false);
          }}
        />
        <Button
          title="Stop treating it as a Staple"
          variant="secondary"
          onPress={() => actions.notAStaple(id)}
        />
        <Button title="Done" variant="ghost" onPress={() => setEditing(false)} />
      </Card>
    );
  }

  return (
    <View style={rowStyle(t)}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`${name}, Staple${staple.have ? '' : ', run out'}`}
        accessibilityHint="Move it or stop treating it as a Staple"
        onPress={() => setEditing(true)}
        style={({ pressed }) => ({
          flex: 1,
          minHeight: t.touchTarget,
          flexDirection: 'row',
          alignItems: 'center',
          gap: t.space.md,
          opacity: pressed ? 0.75 : 1,
        })}
      >
        <FoodThumb
          emoji={ingredientEmoji(staple.ingredient)}
          tint={tintFor(staple.ingredient.name)}
        />
        <View style={{ flex: 1, gap: 4 }}>
          <Text variant="label">{name}</Text>
          {!staple.have ? (
            <View style={{ alignSelf: 'flex-start' }}>
              <StatusBadge status="runOut" />
            </View>
          ) : null}
        </View>
      </Pressable>
      <Button
        title={staple.have ? 'Ran out' : 'Got it'}
        accessibilityLabel={staple.have ? `${name} ran out` : `Got ${name}`}
        variant={staple.have ? 'secondary' : 'primary'}
        compact
        onPress={() => actions.setStaple(id, !staple.have)}
      />
    </View>
  );
}

/**
 * Where it's kept. Choosing a Place moves it at once; the toast says where it went,
 * because under a filter the item disappears from view.
 */
function KeepIn({
  name,
  place,
  onMove,
}: {
  name: string;
  place: Place;
  onMove: (place: Place) => void;
}) {
  const toast = useToast();
  const t = useTheme();
  return (
    <View style={{ gap: t.space.xs }}>
      <Text variant="label" aria-hidden>
        Keep in
      </Text>
      <ChoiceChips<Place>
        label={`Keep ${displayName(name)} in`}
        value={place}
        onChange={(next) => {
          if (next === place) return;
          onMove(next);
          const label = PLACES.find((p) => p.place === next)?.label ?? next;
          toast({
            tag: 'Kitchen',
            text: `Moved ${displayName(name)} to the ${label.toLowerCase()}`,
          });
        }}
        options={PLACES.map(({ place: value, label }) => ({ label, value }))}
      />
    </View>
  );
}

function rowStyle(t: ReturnType<typeof useTheme>) {
  return {
    minHeight: t.touchTarget + 12,
    flexDirection: 'row' as const,
    alignItems: 'center' as const,
    gap: t.space.md,
    backgroundColor: t.colors.surface,
    borderRadius: t.radius.md,
    paddingVertical: t.space.sm,
    paddingHorizontal: t.space.sm,
    boxShadow: t.shadow.card,
  };
}
