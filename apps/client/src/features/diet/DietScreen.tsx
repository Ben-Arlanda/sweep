import { useState, type ReactNode } from 'react';
import { View } from 'react-native';

import { Checkbox } from '@/components/Checkbox';
import { PressableScale } from '@/components/PressableScale';
import { useToast } from '@/components/Toast';
import { Button, Card, ErrorText, Field, Loading, Screen, Text } from '@/components/ui';
import { useIngredientSearch } from '@/lib/api/cabinet';
import {
  newSaveKey,
  useCuisines,
  useDietaryRules,
  usePreferences,
  useSaveDiet,
  type Diet,
  type DietaryRules,
  type Preferences,
} from '@/lib/api/diet';
import { useTheme } from '@/theme/useTheme';

import { parseHouseholdSize } from './form';

const DIETS: { value: Diet; label: string; hint: string }[] = [
  { value: 'vegetarian', label: 'Vegetarian', hint: 'No meat or seafood' },
  { value: 'vegan', label: 'Vegan', hint: 'No animal products' },
  { value: 'gluten_free', label: 'Gluten free', hint: 'No wheat, barley or rye' },
  { value: 'dairy_free', label: 'Dairy free', hint: 'No milk, cheese, butter or cream' },
];

type Ingredient = DietaryRules['excluded_ingredients'][number];

/** Loads what's saved, then shows the form. */
export function DietScreen() {
  const rules = useDietaryRules();
  const preferences = usePreferences();
  if (rules.isError || preferences.isError) {
    return (
      <Screen>
        <ErrorText message={(rules.error ?? preferences.error)?.message} />
        <Button
          title="Try again"
          onPress={() => {
            void rules.refetch();
            void preferences.refetch();
          }}
        />
      </Screen>
    );
  }
  if (!rules.data || !preferences.data) return <Loading />;
  // The form copies the saved values once, as its starting point. Later refetches don't
  // overwrite what someone is in the middle of typing.
  return <DietForm rules={rules.data} preferences={preferences.data} />;
}

function DietForm({ rules, preferences }: { rules: DietaryRules; preferences: Preferences }) {
  const t = useTheme();
  const toast = useToast();
  const save = useSaveDiet();

  const [diets, setDiets] = useState<Diet[]>(rules.diets);
  const [excluded, setExcluded] = useState<Ingredient[]>(rules.excluded_ingredients);
  const [size, setSize] = useState(preferences.household_size?.toString() ?? '');
  const [cuisines, setCuisines] = useState<string[]>(preferences.cuisines);
  const [showErrors, setShowErrors] = useState(false);

  const sizeParsed = parseHouseholdSize(size);
  const invalid = Boolean(sizeParsed.error);

  const toggle = <T,>(list: T[], item: T) =>
    list.includes(item) ? list.filter((x) => x !== item) : [...list, item];

  function onSave() {
    setShowErrors(true);
    if (invalid) return;
    save.mutate(
      {
        key: newSaveKey(),
        rules: { diets, excluded_ingredient_ids: excluded.map((i) => i.id) },
        preferences: {
          household_size: sizeParsed.value,
          cuisines,
        },
      },
      { onSuccess: () => toast({ tag: 'Saved', text: 'Sweep will use these from now on' }) },
    );
  }

  return (
    <Screen edges={['left', 'right', 'bottom']}>
      <Card>
        <Text variant="heading" role="heading" aria-level={2}>
          Dietary Rules
        </Text>
        <Text muted>
          Sweep never suggests a recipe that breaks these. They apply to everyone in your Household.
        </Text>
        <View role="group" aria-label="Diets" style={{ gap: t.space.xs }}>
          {DIETS.map((d) => (
            <CheckRow
              key={d.value}
              label={d.label}
              hint={d.hint}
              checked={diets.includes(d.value)}
              onToggle={() => setDiets((now) => toggle(now, d.value))}
            />
          ))}
        </View>
        <ExcludedIngredients
          excluded={excluded}
          onAdd={(i) => setExcluded((now) => [...now, i])}
          onRemove={(id) => setExcluded((now) => now.filter((i) => i.id !== id))}
        />
        <Text variant="caption" muted>
          Sweep checks recipe ingredients against these rules. Packaged foods can still contain
          allergens, so always check the label. This isn&apos;t medical advice.
        </Text>
      </Card>

      <Card>
        <Text variant="heading" role="heading" aria-level={2}>
          Preferences
        </Text>
        <Text muted>
          What you&apos;d like more of. Sweep leans towards these but can trade them off.
        </Text>
        <Field
          label="People to cook for"
          placeholder="e.g. 4"
          keyboardType="number-pad"
          value={size}
          onChangeText={setSize}
          maxLength={2}
          error={showErrors ? sizeParsed.error : null}
        />
        <CuisineChips selected={cuisines} onToggle={(c) => setCuisines((now) => toggle(now, c))} />
      </Card>

      {/* Said next to the button too, so someone using a screen reader hears it. */}
      <View accessibilityLiveRegion="assertive">
        <ErrorText
          message={
            showErrors && invalid ? 'Fix the fields marked above, then save.' : save.error?.message
          }
        />
      </View>
      <Button title="Save" onPress={onSave} loading={save.isPending} />
    </Screen>
  );
}

/** A whole row is the checkbox: a big target, and the label is read with its state. */
function CheckRow(props: { label: string; hint?: string; checked: boolean; onToggle: () => void }) {
  const t = useTheme();
  return (
    <PressableScale
      role="checkbox"
      aria-checked={props.checked}
      accessibilityLabel={props.hint ? `${props.label}. ${props.hint}` : props.label}
      onPress={props.onToggle}
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.md,
        minHeight: t.touchTarget,
        paddingVertical: t.space.xs,
      }}
    >
      <Checkbox checked={props.checked} />
      <View style={{ flexShrink: 1 }}>
        <Text>{props.label}</Text>
        {props.hint ? (
          <Text variant="caption" muted>
            {props.hint}
          </Text>
        ) : null}
      </View>
    </PressableScale>
  );
}

function ExcludedIngredients(props: {
  excluded: Ingredient[];
  onAdd: (ingredient: Ingredient) => void;
  onRemove: (id: string) => void;
}) {
  const t = useTheme();
  const [query, setQuery] = useState('');
  const search = useIngredientSearch(query);
  const chosen = new Set(props.excluded.map((i) => i.id));
  // keepPreviousData keeps old results on screen while a search loads, so once the box
  // is cleared (search switched off) they'd stay forever. Only show them for a real query.
  const searching = query.trim().length >= 2;
  const results = searching
    ? (search.data ?? []).filter((i) => !chosen.has(i.id)).slice(0, 6)
    : [];

  return (
    <View style={{ gap: t.space.sm }}>
      <Text variant="label">Never use</Text>
      {props.excluded.length === 0 ? (
        <Text muted>No ingredients excluded.</Text>
      ) : (
        props.excluded.map((i) => (
          <Row key={i.id}>
            <Text style={{ flexShrink: 1 }}>{i.name}</Text>
            <Button
              title="Remove"
              accessibilityLabel={`Remove ${i.name}`}
              variant="ghost"
              compact
              onPress={() => props.onRemove(i.id)}
            />
          </Row>
        ))
      )}
      <Field
        label="Add an ingredient to avoid"
        placeholder="e.g. peanuts, mushrooms"
        value={query}
        onChangeText={setQuery}
        autoCorrect={false}
      />
      {searching && !search.isPending && results.length === 0 ? (
        <Text muted>No matching ingredient. Try another name.</Text>
      ) : null}
      {results.map((i) => (
        <Row key={i.id}>
          <Text style={{ flexShrink: 1 }}>{i.name}</Text>
          <Button
            title="Add"
            accessibilityLabel={`Never use ${i.name}`}
            variant="secondary"
            compact
            onPress={() => {
              props.onAdd(i);
              setQuery('');
            }}
          />
        </Row>
      ))}
    </View>
  );
}

function CuisineChips(props: { selected: string[]; onToggle: (cuisine: string) => void }) {
  const t = useTheme();
  const cuisines = useCuisines();
  return (
    <View style={{ gap: t.space.sm }}>
      <Text variant="label">Cuisines you like</Text>
      <ErrorText message={cuisines.error?.message} />
      <View
        role="group"
        aria-label="Cuisines you like"
        style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}
      >
        {(cuisines.data ?? []).map((c) => {
          const on = props.selected.includes(c);
          return (
            <PressableScale
              key={c}
              role="checkbox"
              aria-checked={on}
              accessibilityLabel={cuisineLabel(c)}
              onPress={() => props.onToggle(c)}
              style={{
                minHeight: t.touchTarget,
                justifyContent: 'center',
                paddingHorizontal: t.space.lg,
                borderRadius: t.radius.pill,
                borderWidth: 1.5,
                // Selected shows as fill AND a tick, not colour alone (WCAG 1.4.1).
                borderColor: on ? t.colors.text : t.colors.border,
                backgroundColor: on ? t.colors.inverse : t.colors.surface,
              }}
            >
              <Text style={{ color: on ? t.colors.onInverse : t.colors.text }}>
                {on ? '✓ ' : ''}
                {cuisineLabel(c)}
              </Text>
            </PressableScale>
          );
        })}
      </View>
    </View>
  );
}

/** "middle-eastern" → "Middle Eastern". */
export function cuisineLabel(cuisine: string) {
  return cuisine
    .split('-')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function Row({ children }: { children: ReactNode }) {
  const t = useTheme();
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: t.space.md,
        minHeight: t.touchTarget,
      }}
    >
      {children}
    </View>
  );
}
