import { TINT_NAMES, type TintName } from './tokens';

/**
 * A stable pastel for anything with an id or a name: a list, a Member, an Ingredient.
 *
 * Same input, same colour, on every device, with nothing stored. That's what lets Bob's
 * avatar be sky-blue on Alice's phone too. It's a simple string hash (djb2), which is
 * fine here: we only need an even-ish spread over 5 colours, not security.
 */
export function tintFor(key: string): TintName {
  let h = 5381;
  for (let i = 0; i < key.length; i++) h = ((h << 5) + h + key.charCodeAt(i)) | 0;
  return TINT_NAMES[Math.abs(h) % TINT_NAMES.length];
}

/** Initials for an avatar: "Alice Smith" → "AS", "bob" → "B". */
export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return parts
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join('');
}
