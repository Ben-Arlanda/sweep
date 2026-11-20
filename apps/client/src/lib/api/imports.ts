/**
 * Imported Recipes (slice 4d): "Your recipes", reading a recipe in through a door, and
 * saving, editing or deleting one.
 *
 * Reading (paste, link, photo, file) stores nothing: it returns a draft for the review
 * screen. Each read is one model call that costs money and counts toward the Member's
 * 20 an hour, so a read never retries by itself. The person taps again if they want.
 * The server's message says what went wrong ("try again in 12 minutes", "no recipe on
 * that page, paste the text instead"), so screens show it as it is.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { randomUUID } from 'expo-crypto';

import type { ImportedRecipeIn } from '@/features/imports/review';

import { api, unwrap } from './client';
import { mealPlanKeys } from './mealPlan';
import { recipeKeys } from './recipes';
import type { components } from './schema';
import { appendFile, type PickedFile } from './upload';

export type { PickedFile };

export type ImportDraft = components['schemas']['ImportDraftOut'];
export type ImportedRecipe = components['schemas']['ImportedRecipeOut'];
type SavedLine = components['schemas']['RecipeIngredientOut'];

export const importKeys = {
  mine: ['recipes', 'imported'] as const, // under 'recipes': a save refreshes both
};

/** This Household's own recipes, newest first, each with any Dietary Rule it can't pass. */
export function useImportedRecipes() {
  return useQuery({
    queryKey: importKeys.mine,
    queryFn: async () => unwrap(await api.GET('/recipes/imported')),
  });
}

// openapi-fetch would turn the body into JSON; FormData must go as it is, so the
// browser (or React Native) sets the multipart boundary itself.
const asIs = (body: unknown) => body as BodyInit;

export type Door =
  | { door: 'paste'; text: string }
  | { door: 'link'; url: string }
  | { door: 'photo'; photos: PickedFile[] }
  | { door: 'file'; file: PickedFile };

async function read(input: Door): Promise<ImportDraft> {
  switch (input.door) {
    case 'paste':
      return unwrap(await api.POST('/recipes/imports/paste', { body: { text: input.text } }));
    case 'link':
      return unwrap(await api.POST('/recipes/imports/link', { body: { url: input.url } }));
    case 'photo': {
      const form = new FormData();
      for (const photo of input.photos) await appendFile(form, 'photos', photo);
      return unwrap(
        await api.POST('/recipes/imports/photo', {
          body: form as never,
          bodySerializer: asIs,
        }),
      );
    }
    case 'file': {
      const form = new FormData();
      await appendFile(form, 'file', input.file);
      return unwrap(
        await api.POST('/recipes/imports/file', { body: form as never, bodySerializer: asIs }),
      );
    }
  }
}

/** One door's read. No retry: see the file comment. */
export function useReadRecipe() {
  return useMutation({ mutationFn: read, retry: false });
}

/** Lines typed or added on the review screen, read the same way as an import's. */
export function useReadLines() {
  return useMutation({
    retry: false,
    mutationFn: async (lines: string[]): Promise<SavedLine[]> =>
      unwrap(await api.POST('/recipes/lines', { body: { lines } })),
  });
}

type SaveVars = { id: string | null; body: ImportedRecipeIn; idempotencyKey: string };

/** Make the variables at tap time, so a retry of one tap can't save twice. */
export const saveTap = (id: string | null, body: ImportedRecipeIn): SaveVars => ({
  id,
  body,
  idempotencyKey: randomUUID(),
});

export function useImportedRecipeActions() {
  const queryClient = useQueryClient();
  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: recipeKeys.all }); // lists, search, the recipe
  };

  const save = useMutation({
    onSettled: refresh,
    mutationFn: async ({ id, body, idempotencyKey }: SaveVars) => {
      const header = { 'Idempotency-Key': idempotencyKey };
      return id
        ? unwrap(
            await api.PUT('/recipes/imported/{recipe_id}', {
              params: { path: { recipe_id: id }, header },
              body,
            }),
          )
        : unwrap(await api.POST('/recipes/imported', { params: { header }, body }));
    },
  });

  const remove = useMutation({
    onSettled: async () => {
      await refresh();
      // Its Planned Meals go with it (the database cascades the delete).
      await queryClient.invalidateQueries({ queryKey: mealPlanKeys.all });
    },
    mutationFn: async ({ id, idempotencyKey }: { id: string; idempotencyKey: string }) => {
      unwrap(
        await api.DELETE('/recipes/imported/{recipe_id}', {
          params: { path: { recipe_id: id }, header: { 'Idempotency-Key': idempotencyKey } },
        }),
      );
    },
  });

  // A recipe's own photo (ADR 0031): a file adds or replaces it, null removes it.
  const photo = useMutation({
    onSettled: async () => {
      await refresh();
      await queryClient.invalidateQueries({ queryKey: mealPlanKeys.all }); // plans show it
    },
    mutationFn: async ({ id, file, idempotencyKey }: PhotoVars) => {
      const params = { path: { recipe_id: id }, header: { 'Idempotency-Key': idempotencyKey } };
      if (!file) {
        return unwrap(await api.DELETE('/recipes/imported/{recipe_id}/photo', { params }));
      }
      const form = new FormData();
      await appendFile(form, 'photo', file);
      return unwrap(
        await api.PUT('/recipes/imported/{recipe_id}/photo', {
          params,
          body: form as never,
          bodySerializer: asIs,
        }),
      );
    },
  });

  return { save, remove, photo };
}

type PhotoVars = { id: string; file: PickedFile | null; idempotencyKey: string };

/** Make the variables at tap time, like `saveTap`. */
export const photoTap = (id: string, file: PickedFile | null): PhotoVars => ({
  id,
  file,
  idempotencyKey: randomUUID(),
});
