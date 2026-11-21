import { router, usePreventRemove } from 'expo-router';
import { X } from 'lucide-react-native';
import { useEffect, useState } from 'react';
import { Pressable, View } from 'react-native';

import { ChoiceChips } from '@/components/ChoiceChips';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { Icon } from '@/components/Icon';
import { Tag } from '@/components/Pill';
import { PressableScale } from '@/components/PressableScale';
import { RecipeArt } from '@/components/RecipeArt';
import { useToast } from '@/components/Toast';
import { Button, ErrorText, Field, Screen, SectionLabel, Text } from '@/components/ui';
import { displayName } from '@/features/kitchen/format';
import { LinkSheet } from '@/features/lists/LinkSheet';
import { COURSES } from '@/features/recipes/courses';
import { PhotoButton } from '@/features/recipes/OwnPhoto';
import type { RecipeImage } from '@/features/recipes/photo';
import { cuisineName } from '@/features/recipes/kitchenMatch';
import { photoTap, saveTap, useImportedRecipeActions, useReadLines } from '@/lib/api/imports';
import type { PickedFile } from '@/lib/api/upload';
import { useTheme } from '@/theme/useTheme';

import { dropDraft } from './drafts';
import {
  addLine,
  hasChanges,
  lineMarks,
  linkLine,
  readLines,
  removeLine,
  MAX_SUMMARY,
  saveProblems,
  searchGuess,
  toImportedRecipe,
  type FormLine,
  type Problems,
  type ReviewForm,
} from './review';

const MARK_TEXT = { check: 'Check', not_linked: 'Not linked' } as const;

/**
 * Where every new recipe is checked before it's saved, and where a saved one is edited.
 * The marks say where to look ("Check": Sweep read it from a photo, or couldn't find it
 * word for word in the text; "Not linked": a line too long to be one food). A food Sweep
 * doesn't know shows "New: …" and is added on Save (ADR 0032). Marks never block Save.
 */
export function ReviewScreen({
  start,
  recipeId,
  draftId,
  image = null,
}: {
  start: ReviewForm;
  recipeId: string | null; // editing a saved one
  draftId: string | undefined;
  image?: RecipeImage | null; // its photo now, when editing
}) {
  const t = useTheme();
  const [form, setForm] = useState(start);
  const [tried, setTried] = useState(false); // problems show after the first Save
  const [linking, setLinking] = useState<FormLine | null>(null);
  const [newLine, setNewLine] = useState('');
  const [leave, setLeave] = useState<(() => void) | null>(null);
  const { save, photo: savePhoto } = useImportedRecipeActions();
  const toast = useToast();
  // The photo to save with it (ADR 0031): a new one, 'remove', or null for no change.
  const [photo, setPhoto] = useState<{ file: PickedFile } | 'remove' | null>(null);
  const shown =
    photo === 'remove'
      ? null
      : photo
        ? { thumb_url: photo.file.uri, hero_url: photo.file.uri }
        : image;
  const read = useReadLines();

  const changed =
    hasChanges(start, form) || (recipeId === null && draftId !== undefined) || photo !== null;
  const disablePrevention = usePreventRemove(changed && !save.isSuccess, ({ repeat }) =>
    setLeave(() => repeat),
  );

  // Lines added here are read by the server (amount, unit, Ingredient), like an import's.
  const pending = form.lines.filter((l) => l.pending).map((l) => l.rawText);
  const pendingKey = pending.join('\n');
  useEffect(() => {
    if (!pendingKey || read.isPending) return;
    read.mutate(pendingKey.split('\n'), {
      onSuccess: (lines) => setForm((f) => readLines(f, lines)),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- read once per batch of new lines
  }, [pendingKey]);

  const problems: Problems = tried ? saveProblems(form) : {};
  const set = (change: Partial<ReviewForm>) => setForm((f) => ({ ...f, ...change }));
  const anyCheck = form.lines.some((l) => l.check);

  async function onSave() {
    setTried(true);
    if (Object.keys(saveProblems(form)).length) return;
    try {
      const saved = await save.mutateAsync(saveTap(recipeId, toImportedRecipe(form)));
      if (photo) {
        // The recipe is saved either way; a failed photo can be added from its page.
        await savePhoto
          .mutateAsync(photoTap(saved.id, photo === 'remove' ? null : photo.file))
          .catch(() =>
            toast({ tag: 'Recipes', text: "Saved, but the photo didn't upload. Add it again." }),
          );
      }
      dropDraft(draftId);
      disablePrevention();
      router.replace({ pathname: '/recipes/[id]', params: { id: saved.id } });
    } catch {
      // save.error has the server's message
    }
  }

  return (
    <Screen>
      <Text variant="title" accessibilityRole="header">
        {recipeId ? 'Edit recipe' : 'Check your recipe'}
      </Text>
      <View>
        <RecipeArt
          title={form.title || 'New recipe'}
          image={shown}
          width="100%"
          height={180}
          radius={t.radius.lg}
          iconSize={48}
        />
        <PhotoButton
          hasPhoto={!!shown}
          busy={savePhoto.isPending}
          onPicked={(file) => setPhoto({ file })}
          onRemove={() => setPhoto(image ? 'remove' : null)}
          style={{ position: 'absolute', left: t.space.sm, bottom: t.space.sm }}
        />
      </View>
      {form.moreRecipes ? (
        <Text>This file has more than one recipe: we&apos;ve taken the first.</Text>
      ) : null}
      {anyCheck ? (
        <Text variant="caption" muted>
          Lines marked Check came from a photo, or weren&apos;t found word for word in what you gave
          Sweep. Have a quick look at them.
        </Text>
      ) : null}

      <Field
        label="Name"
        value={form.title}
        onChangeText={(title) => set({ title })}
        maxLength={200}
        error={problems.title}
      />
      <Field
        label="Description (optional)"
        value={form.summary}
        onChangeText={(summary) => set({ summary })}
        multiline
        maxLength={MAX_SUMMARY}
        textAlignVertical="top"
        style={{ minHeight: 72, paddingTop: t.space.sm }}
        error={problems.summary}
      />
      <View style={{ flexDirection: 'row', gap: t.space.md }}>
        <View style={{ flex: 1 }}>
          <Field
            label="Serves"
            value={form.servings}
            onChangeText={(servings) => set({ servings })}
            keyboardType="number-pad"
            maxLength={2}
            error={problems.servings}
          />
        </View>
        <View style={{ flex: 1 }}>
          <Field
            label="Minutes (optional)"
            value={form.minutes}
            onChangeText={(minutes) => set({ minutes })}
            keyboardType="number-pad"
            maxLength={4}
            error={problems.minutes}
          />
        </View>
      </View>

      <View style={{ gap: t.space.xs }}>
        <Text variant="label">Course</Text>
        {form.courseGuess && form.course === form.courseGuess ? (
          <Text variant="caption" muted>
            Sweep&apos;s guess: change it if it&apos;s wrong.
          </Text>
        ) : null}
        <ChoiceChips
          label="Course"
          options={COURSES.map((c) => ({ label: c.one, value: c.value }))}
          value={form.course}
          onChange={(course) => set({ course })}
        />
        <ErrorText message={problems.course} />
        {form.cuisine ? (
          <Text variant="caption" muted>
            Cuisine: {cuisineName(form.cuisine)}
          </Text>
        ) : null}
      </View>

      <View style={{ gap: t.space.sm }}>
        <SectionLabel>Ingredients</SectionLabel>
        {form.lines.map((line) => (
          <LineRow
            key={line.key}
            line={line}
            onLink={() => setLinking(line)}
            onRemove={() => setForm((f) => removeLine(f, line.key))}
          />
        ))}
        <ErrorText message={problems.lines} />
        <Field
          label="Add an ingredient"
          placeholder="e.g. 2 tbsp olive oil"
          value={newLine}
          onChangeText={setNewLine}
          maxLength={300}
          returnKeyType="done"
          onSubmitEditing={() => {
            setForm((f) => addLine(f, newLine));
            setNewLine('');
          }}
        />
        <Button
          title="Add ingredient"
          variant="secondary"
          disabled={!newLine.trim()}
          onPress={() => {
            setForm((f) => addLine(f, newLine));
            setNewLine('');
          }}
        />
        <ErrorText message={read.error?.message} />
      </View>

      <Method form={form} onChange={(method) => set({ method })} />

      <ErrorText message={save.error?.message} />
      <Button title="Save recipe" loading={save.isPending} onPress={onSave} />

      {linking ? (
        <LinkSheet
          name={linking.rawText}
          startQuery={searchGuess(linking.rawText)}
          label={`Ingredient for ${linking.rawText}`}
          current={linking.ingredient}
          title={`Which Ingredient is "${linking.rawText}"?`}
          hint="Sweep uses it to check your Kitchen and Dietary Rules, and for the Shopping List."
          allowNone={false}
          onPick={(ingredient) => {
            if (!ingredient) return;
            setForm((f) => ({
              ...f,
              lines: f.lines.map((l) => (l.key === linking.key ? linkLine(l, ingredient) : l)),
            }));
          }}
          onClose={() => setLinking(null)}
        />
      ) : null}
      {leave ? (
        <ConfirmDialog
          title="Leave without saving?"
          message={recipeId ? 'Your changes will be lost.' : "This recipe won't be saved."}
          confirm="Leave without saving"
          cancel="Keep checking"
          onCancel={() => setLeave(null)}
          onConfirm={() => {
            dropDraft(draftId);
            setLeave(null);
            disablePrevention();
            leave();
          }}
        />
      ) : null}
    </Screen>
  );
}

function LineRow({
  line,
  onLink,
  onRemove,
}: {
  line: FormLine;
  onLink: () => void;
  onRemove: () => void;
}) {
  const t = useTheme();
  const marks = lineMarks(line);
  const linked = line.ingredient ? displayName(line.ingredient.name) : null;
  const added = line.newIngredient ? `New: ${displayName(line.newIngredient)}` : null;
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.sm }}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={[
          line.rawText,
          ...marks.map((m) => MARK_TEXT[m]),
          linked ? `linked to ${linked}` : null,
          added,
          'Change the Ingredient',
        ]
          .filter(Boolean)
          .join(', ')}
        onPress={onLink}
        disabled={line.pending}
        style={({ pressed }) => ({
          flex: 1,
          minHeight: t.touchTarget,
          justifyContent: 'center',
          gap: 2,
          opacity: pressed ? 0.6 : 1,
        })}
      >
        <Text>{line.rawText}</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.xs }}>
          {line.pending ? (
            <Text variant="caption" muted>
              Reading…
            </Text>
          ) : null}
          {linked || added ? (
            <Text variant="caption" muted>
              {linked ?? added}
            </Text>
          ) : null}
          {marks.map((m) => (
            <Tag key={m} kind={m === 'not_linked' ? 'need' : 'soft'}>
              {MARK_TEXT[m]}
            </Tag>
          ))}
        </View>
      </Pressable>
      <PressableScale
        accessibilityRole="button"
        accessibilityLabel={`Remove ${line.rawText}`}
        onPress={onRemove}
        style={{
          minHeight: t.touchTarget,
          minWidth: t.touchTarget,
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Icon icon={X} color={t.colors.textMuted} size={20} />
      </PressableScale>
    </View>
  );
}

/** The steps, or (from a link) where the method lives. Steps aren't reworded by Sweep. */
function Method({ form, onChange }: { form: ReviewForm; onChange: (method: string[]) => void }) {
  const t = useTheme();
  const steps = form.method ?? [];
  if (form.sourceUrl && steps.length === 0) {
    return (
      <View style={{ gap: t.space.xs }}>
        <SectionLabel>Method</SectionLabel>
        <Text>Method on {hostOf(form.sourceUrl)}.</Text>
      </View>
    );
  }
  return (
    <View style={{ gap: t.space.sm }}>
      <SectionLabel>Method</SectionLabel>
      {steps.map((step, i) => (
        <Field
          key={i}
          label={`Step ${i + 1}`}
          value={step}
          onChangeText={(text) => onChange(steps.map((s, j) => (j === i ? text : s)))}
          multiline
          maxLength={2000}
          textAlignVertical="top"
          style={{ minHeight: 72, paddingTop: t.space.sm }}
        />
      ))}
      {steps.length < 40 ? (
        <Button title="Add a step" variant="secondary" onPress={() => onChange([...steps, ''])} />
      ) : null}
    </View>
  );
}

export function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}
