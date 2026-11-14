import { Tile } from '@/components/Tile';

/** Home board tile into the Recipe Knowledge Base. */
export function RecipesTile() {
  return (
    <Tile href="/recipes" tint="butter" emoji="📖" title="Recipes" subtitle="Find something to cook" />
  );
}
