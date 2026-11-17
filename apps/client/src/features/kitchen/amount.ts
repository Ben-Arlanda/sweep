/**
 * The item sheet's amount picker: Weight / Volume / Count, a number and a unit, plus
 * quick picks. The server converts what's typed to the Ingredient's own unit (ADR 0024);
 * these helpers only decide what the sheet offers.
 */
export type Kind = 'weight' | 'volume' | 'count';
export type Unit = 'g' | 'kg' | 'ml' | 'L' | 'count';

export const KINDS: readonly { kind: Kind; label: string }[] = [
  { kind: 'weight', label: 'Weight' },
  { kind: 'volume', label: 'Volume' },
  { kind: 'count', label: 'Count' },
];

export const UNITS: Record<Kind, readonly Unit[]> = {
  weight: ['g', 'kg'],
  volume: ['ml', 'L'],
  count: ['count'],
};

const QUICK: Record<Unit, readonly string[]> = {
  g: ['10', '25', '50', '100'],
  kg: ['0.5', '1', '2', '5'],
  ml: ['50', '100', '250', '500'],
  L: ['0.5', '1', '2', '3'],
  count: ['1', '2', '6', '12'],
};

export function kindOf(unit: string): Kind {
  if (unit === 'g' || unit === 'kg') return 'weight';
  if (unit === 'ml' || unit === 'L') return 'volume';
  return 'count';
}

/** Kinds that convert honestly: the Ingredient's own, plus weight ↔ volume with a density. */
export function allowedKinds(baseUnit: string, gramsPerMl: string | null | undefined): Set<Kind> {
  const own = kindOf(baseUnit);
  const kinds = new Set<Kind>([own]);
  if (gramsPerMl && own !== 'count') kinds.add(own === 'weight' ? 'volume' : 'weight');
  return kinds;
}

export function quickPicks(unit: Unit): readonly string[] {
  return QUICK[unit];
}

export function unitLabel(unit: Unit): string {
  return unit === 'count' ? 'items' : unit;
}

/** Where the sheet starts: 1500 g reads as 1.5 kg, 250 ml stays 250 ml. */
export function editable(quantity: string | null, baseUnit: string): { value: string; unit: Unit } {
  const base = (['g', 'ml', 'count'].includes(baseUnit) ? baseUnit : 'count') as Unit;
  if (quantity === null) return { value: '', unit: base };
  const n = Number(quantity);
  const trim = (x: number) => String(Number(x.toFixed(3)));
  if (base === 'g' && n >= 1000) return { value: trim(n / 1000), unit: 'kg' };
  if (base === 'ml' && n >= 1000) return { value: trim(n / 1000), unit: 'L' };
  return { value: trim(n), unit: base };
}
