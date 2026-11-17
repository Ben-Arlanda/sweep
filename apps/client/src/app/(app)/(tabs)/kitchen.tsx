import { Ellipsis } from 'lucide-react-native';
import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { ChoiceChips } from '@/components/ChoiceChips';
import { FoodThumb } from '@/components/FoodThumb';
import { Icon } from '@/components/Icon';
import { Hero, HeroSearch } from '@/components/Hero';
import { StatusBadge } from '@/components/Pill';
import { Sheet } from '@/components/Sheet';
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
import { goneText, undoSteps, type Gone } from '@/features/kitchen/usedUp';
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
  const [menu, setMenu] = useState<string | null>(null); // the item whose ⋯ menu is open
  const [gone, setGone] = useState<Gone | null>(null); // the last Used up, for Undo

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

  async function markGone(row: Tracked | Staple, kind: Gone['kind']) {
    setMenu(null);
    setGone(null);
    try {
      const out = await actions.usedUp(row.ingredient.id);
      setGone({
        ingredientId: row.ingredient.id,
        name: row.ingredient.name,
        kind,
        quantity: kind === 'tracked' ? (row as Tracked).quantity : null,
        place: row.place,
        listId: out.list_id,
        listItemId: out.list_item_id ?? null,
      });
    } catch {
      // actions.error has the server's message
    }
  }

  function undo(what: Gone) {
    for (const step of undoSteps(what)) {
      if (step.do === 'setAmount') actions.setAmount(step.ingredientId, step.quantity);
      if (step.do === 'setPlace') actions.setPlace(step.ingredientId, step.place);
      if (step.do === 'have') actions.setStaple(step.ingredientId, true);
      if (step.do === 'removeFromList') actions.unlist(step.listId, step.itemId);
    }
    setGone(null);
  }

  const menuTracked = tracked.find((i) => i.ingredient.id === menu);
  const menuStaple = staples.find((s) => s.ingredient.id === menu);
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
      {gone ? (
        // Inline and without a timer, so there's time to Undo (WCAG 2.2.1).
        <Card style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.sm }}>
          <Text accessibilityLiveRegion="polite" aria-live="polite" style={{ flex: 1 }}>
            {goneText(gone)}
          </Text>
          <Button title="Undo" variant="secondary" compact onPress={() => undo(gone)} />
          <Button title="OK" variant="ghost" compact onPress={() => setGone(null)} />
        </Card>
      ) : null}
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
        Ticking items off the Shopping List adds them here, or add a photo of things laid out. Used
        up and Ran out put things back on the list.
      </Text>

      {sections.length === 0 ? <Text muted>Nothing in your Kitchen yet.</Text> : null}
      {sections.map((section) => (
        <View key={section.place} style={{ gap: t.space.sm }}>
          <SectionLabel>{section.label}</SectionLabel>
          {section.tracked.length + section.staples.length === 0 ? (
            <Text muted>Nothing in the {section.label.toLowerCase()} yet.</Text>
          ) : null}
          {section.tracked.map((item) => (
            <TrackedRow
              key={item.ingredient.id}
              item={item}
              onMore={() => setMenu(item.ingredient.id)}
            />
          ))}
          {section.staples.map((staple) => (
            <StapleRow
              key={staple.ingredient.id}
              staple={staple}
              actions={actions}
              onGone={() => markGone(staple, 'staple')}
              onMore={() => setMenu(staple.ingredient.id)}
            />
          ))}
        </View>
      ))}
      {menuTracked ? (
        <TrackedMenu
          item={menuTracked}
          actions={actions}
          onGone={() => markGone(menuTracked, 'tracked')}
          onClose={() => setMenu(null)}
        />
      ) : null}
      {menuStaple ? (
        <StapleMenu
          staple={menuStaple}
          actions={actions}
          onGone={() => markGone(menuStaple, 'staple')}
          onClose={() => setMenu(null)}
        />
      ) : null}
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

/** The ⋯ at the end of a card, and the card itself: both open the item's menu. */
function MoreButton({ name, onPress }: { name: string; onPress: () => void }) {
  const t = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`More for ${name}`}
      onPress={onPress}
      style={({ pressed }) => ({
        minWidth: t.touchTarget,
        minHeight: t.touchTarget,
        alignItems: 'center',
        justifyContent: 'center',
        opacity: pressed ? 0.6 : 1,
      })}
    >
      <Icon icon={Ellipsis} color={t.colors.text} />
    </Pressable>
  );
}

function TrackedRow({ item, onMore }: { item: Tracked; onMore: () => void }) {
  const t = useTheme();
  const name = displayName(item.ingredient.name);
  const amount = `${item.status === 'confirmed' ? '' : 'about '}${formatAmount(item.quantity, item.unit)}`;
  return (
    <View style={rowStyle(t)}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`${name}, ${amount}${item.status === 'confirmed' ? '' : `, ${item.status}`}`}
        accessibilityHint="Change the amount, mark it used up, or move it"
        onPress={onMore}
        style={({ pressed }) => ({
          flex: 1,
          minHeight: t.touchTarget,
          flexDirection: 'row',
          alignItems: 'center',
          gap: t.space.md,
          opacity: pressed ? 0.75 : 1,
        })}
      >
        <FoodThumb emoji={ingredientEmoji(item.ingredient)} tint={tintFor(item.ingredient.name)} />
        <View style={{ flex: 1, gap: 2 }}>
          <Text variant="label">{name}</Text>
          <Text variant="caption" muted>
            {amount}
          </Text>
        </View>
        {/* Confirmed is the normal state: only what needs a second look gets a badge. */}
        {item.status === 'confirmed' ? null : <StatusBadge status={item.status} />}
      </Pressable>
      <MoreButton name={name} onPress={onMore} />
    </View>
  );
}

function StapleRow({
  staple,
  actions,
  onGone,
  onMore,
}: {
  staple: Staple;
  actions: Actions;
  onGone: () => void;
  onMore: () => void;
}) {
  const t = useTheme();
  const id = staple.ingredient.id;
  const name = displayName(staple.ingredient.name);
  return (
    <View style={rowStyle(t)}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`${name}, Staple${staple.have ? '' : ', run out'}`}
        accessibilityHint="Move it or stop treating it as a Staple"
        onPress={onMore}
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
        onPress={() => (staple.have ? onGone() : actions.setStaple(id, true))}
      />
      <MoreButton name={name} onPress={onMore} />
    </View>
  );
}

/** A Tracked item's ⋯ menu: amount, Used up, Place, Staple, or Remove. */
function TrackedMenu({
  item,
  actions,
  onGone,
  onClose,
}: {
  item: Tracked;
  actions: Actions;
  onGone: () => void;
  onClose: () => void;
}) {
  const t = useTheme();
  const [draft, setDraft] = useState(item.quantity ?? '');
  const id = item.ingredient.id;
  const name = displayName(item.ingredient.name);
  const valid = draft.trim() === '' || Number(draft) > 0;
  return (
    <Sheet label={name} title={name} onClose={onClose}>
      <View style={{ gap: t.space.md }}>
        <Field
          label={`Amount in ${item.unit === 'count' ? 'items' : item.unit}`}
          value={draft}
          onChangeText={setDraft}
          keyboardType="decimal-pad"
          placeholder="Leave empty for 'some'"
          error={valid ? null : 'Enter a number above 0'}
        />
        <Button
          title="Save amount"
          disabled={!valid}
          onPress={() => {
            actions.setAmount(id, draft.trim() === '' ? null : draft.trim());
            onClose();
          }}
        />
        <Button title="Used up: add to list" variant="secondary" onPress={onGone} />
        <KeepIn
          name={item.ingredient.name}
          place={item.place}
          onMove={(place) => {
            actions.setPlace(id, place);
            onClose();
          }}
        />
        <Button
          title="Make it a Staple"
          variant="secondary"
          onPress={() => {
            actions.setStaple(id, true);
            onClose();
          }}
        />
        <Button
          title="Remove: it isn't here"
          variant="ghost"
          onPress={() => {
            actions.remove(id);
            onClose();
          }}
        />
      </View>
    </Sheet>
  );
}

/** A Staple's ⋯ menu: Ran out (or Got it), Place, or stop treating it as a Staple. */
function StapleMenu({
  staple,
  actions,
  onGone,
  onClose,
}: {
  staple: Staple;
  actions: Actions;
  onGone: () => void;
  onClose: () => void;
}) {
  const t = useTheme();
  const id = staple.ingredient.id;
  const name = displayName(staple.ingredient.name);
  return (
    <Sheet label={name} title={name} onClose={onClose}>
      <View style={{ gap: t.space.md }}>
        {staple.have ? (
          <Button title="Ran out: add to list" onPress={onGone} />
        ) : (
          <Button
            title="Got it"
            onPress={() => {
              actions.setStaple(id, true);
              onClose();
            }}
          />
        )}
        <KeepIn
          name={staple.ingredient.name}
          place={staple.place}
          onMove={(place) => {
            actions.setPlace(id, place);
            onClose();
          }}
        />
        <Button
          title="Stop treating it as a Staple"
          variant="secondary"
          onPress={() => {
            actions.notAStaple(id);
            onClose();
          }}
        />
      </View>
    </Sheet>
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
