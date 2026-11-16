import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';

import { Button, ErrorText, Loading, Screen, Text } from '@/components/ui';
import { findDraft } from '@/features/imports/drafts';
import { emptyForm, formFromDraft, formFromRecipe } from '@/features/imports/review';
import { ReviewScreen } from '@/features/imports/ReviewScreen';
import { useRecipe } from '@/lib/api/recipes';

/**
 * /recipes/review?draft=… (from the Add Sheet), ?edit=<recipe id>, or nothing (Type).
 * The form is built once, from whichever it is; after that the screen owns it.
 */
export default function ReviewRoute() {
  const { draft: draftId, edit } = useLocalSearchParams<{ draft?: string; edit?: string }>();
  if (edit) return <EditRecipe id={edit} />;
  if (draftId) return <FromDraft draftId={draftId} />;
  return <NewRecipe />;
}

function NewRecipe() {
  const [start] = useState(emptyForm);
  return <ReviewScreen start={start} recipeId={null} draftId={undefined} />;
}

function FromDraft({ draftId }: { draftId: string }) {
  const [draft] = useState(() => findDraft(draftId));
  const [start] = useState(() => (draft ? formFromDraft(draft) : null));
  if (!start) {
    // Drafts live in memory only: a reload (or an old link) finds nothing.
    return (
      <Screen>
        <Text variant="title" accessibilityRole="header">
          This recipe wasn&apos;t saved
        </Text>
        <Text>Sweep keeps a recipe you&apos;re checking only until you save or leave it.</Text>
        <Button title="Back to recipes" onPress={() => router.replace('/recipes')} />
      </Screen>
    );
  }
  return <ReviewScreen start={start} recipeId={null} draftId={draftId} />;
}

function EditRecipe({ id }: { id: string }) {
  const recipe = useRecipe(id);
  if (recipe.isPending) return <Loading />;
  if (recipe.isError) {
    return (
      <Screen>
        <ErrorText message={recipe.error.message} />
        <Button title="Try again" onPress={() => recipe.refetch()} />
      </Screen>
    );
  }
  return <ReviewScreen start={formFromRecipe(recipe.data)} recipeId={id} draftId={undefined} />;
}
