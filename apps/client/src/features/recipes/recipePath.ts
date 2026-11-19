import { useSegments } from 'expo-router';

/** Recipe links stay in the stack they're in: the Recipes tab, or above Home and the plans. */
export function useRecipePath() {
  const segments: string[] = useSegments();
  return segments.includes('(tabs)') ? ('/recipes/[id]' as const) : ('/recipe/[id]' as const);
}
