import type { components } from '@/lib/api/schema';

type Line = Pick<
  components['schemas']['RecipeIngredientOut'],
  'raw_text' | 'quantity' | 'unit' | 'note' | 'optional'
> & { ingredient: { name: string } | null };

/** "Chicken breast": the Ingredient's name, capitalised; the line as written if unlinked. */
export function lineName(line: Line) {
  const name = line.ingredient?.name;
  return name ? name.charAt(0).toUpperCase() + name.slice(1) : line.raw_text;
}

/** "600 g", or the whole line when it has no amount we understood. */
function lineAmount(line: Line) {
  if (!line.ingredient) return null;
  if (line.quantity === null) return line.raw_text;
  return [line.quantity, line.unit].filter(Boolean).join(' ');
}

/** Under the name: "200 g · or andouille sausage · sliced" (the server joins notes with "; "). */
export function lineCaption(line: Line) {
  const notes = line.note ? line.note.split('; ') : [];
  return [lineAmount(line), ...notes, line.optional ? 'optional' : null]
    .filter(Boolean)
    .join(' · ');
}

/** An Ingredient Group's name above its first line, else null (ADR 0033). */
export function groupHeading<T>(lines: T[], i: number, group: (line: T) => string | null) {
  const name = group(lines[i]);
  return name && (i === 0 || group(lines[i - 1]) !== name) ? name : null;
}
