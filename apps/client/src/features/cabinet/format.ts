/**
 * How Cabinet amounts read on screen. The API always sends the Ingredient's base unit
 * (g, ml or count); people read "1.5 kg" more easily than "1500 g".
 */
export function formatAmount(quantity: string | null, unit: string): string {
  if (quantity === null) return 'Some';
  const n = Number(quantity);
  const trim = (x: number) => String(Number(x.toFixed(2)));
  if (unit === 'g') return n >= 1000 ? `${trim(n / 1000)} kg` : `${trim(n)} g`;
  if (unit === 'ml') return n >= 1000 ? `${trim(n / 1000)} L` : `${trim(n)} ml`;
  return trim(n);
}

/** Ingredient names are stored lowercase ("greek yoghurt"); show them as "Greek yoghurt". */
export function displayName(name: string): string {
  return name.charAt(0).toUpperCase() + name.slice(1);
}
