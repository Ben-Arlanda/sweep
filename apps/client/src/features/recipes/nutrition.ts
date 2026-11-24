/**
 * A recipe's Nutrition per serve, worked out by the API from AUSNUT (ADR 0035), set out
 * like an Australian label: kJ with Cal, whole numbers, % Daily Intake of an 8,700 kJ diet.
 */
import type { components } from '@/lib/api/schema';

type Nutrients = components['schemas']['Nutrients'];
type Nutrition = components['schemas']['Nutrition'];

const KJ_PER_CAL = 4.184;

/** Label order; the reference values are FSANZ's Daily Intake for an average adult. */
const ROWS: {
  key: keyof Nutrients;
  label: string;
  unit: 'g' | 'mg';
  reference: number;
  sub?: boolean;
}[] = [
  { key: 'protein_g', label: 'Protein', unit: 'g', reference: 50 },
  { key: 'fat_g', label: 'Fat', unit: 'g', reference: 70 },
  { key: 'saturated_fat_g', label: 'Saturated', unit: 'g', reference: 24, sub: true },
  { key: 'carbs_g', label: 'Carbohydrate', unit: 'g', reference: 310 },
  { key: 'sugars_g', label: 'Sugars', unit: 'g', reference: 90, sub: true },
  { key: 'fibre_g', label: 'Fibre', unit: 'g', reference: 30 },
  { key: 'sodium_mg', label: 'Sodium', unit: 'mg', reference: 2300 },
];

export type NutritionRow = {
  label: string;
  sub: boolean; // shown under the row above it ("Saturated" under "Fat")
  amount: string;
  spoken: string;
  percent: number;
};

export function calories(kj: number): number {
  return Math.round(kj / KJ_PER_CAL);
}

const whole = (n: number) => Math.round(n).toLocaleString('en-AU');

export function nutritionRows(per: Nutrients): NutritionRow[] {
  const kj = whole(per.energy_kj);
  const cal = whole(calories(per.energy_kj));
  const energy = {
    label: 'Energy',
    sub: false,
    amount: `${kj} kJ (${cal} Cal)`,
    spoken: `${kj} kilojoules, ${cal} calories`,
    percent: Math.round((per.energy_kj / 8700) * 100),
  };
  return [
    energy,
    ...ROWS.map(({ key, label, unit, reference, sub }) => {
      const value = per[key];
      const tiny = value > 0 && Math.round(value) === 0;
      const word = unit === 'g' ? 'gram' : 'milligram';
      const n = Math.round(value);
      return {
        label,
        sub: !!sub,
        amount: tiny ? `<1 ${unit}` : `${whole(value)} ${unit}`,
        spoken: tiny ? `less than 1 ${word}` : `${whole(value)} ${word}${n === 1 ? '' : 's'}`,
        percent: Math.round((value / reference) * 100),
      };
    }),
  ];
}

/** The big number on the Nutrition tab ("500", over "Cal Nutrition"); null when unavailable. */
export function nutritionTabValue(nutrition: Nutrition): string | null {
  return nutrition.available && nutrition.per_serve
    ? whole(calories(nutrition.per_serve.energy_kj))
    : null;
}

/** The big number on the Method tab: "35m", "1h 30m", "2h". */
export function methodTabValue(recipe: {
  prep_minutes: number | null;
  cook_minutes: number | null;
  total_minutes: number | null;
}): string | null {
  const split =
    recipe.prep_minutes !== null || recipe.cook_minutes !== null
      ? (recipe.prep_minutes ?? 0) + (recipe.cook_minutes ?? 0)
      : null;
  const minutes = recipe.total_minutes ?? split;
  if (!minutes) return null;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h === 0 ? `${m}m` : m === 0 ? `${h}h` : `${h}h ${m}m`;
}

/** "Doesn't include ginger and lemongrass.": lines with amounts we couldn't count. */
export function leftOutText(names: string[]): string | null {
  if (names.length === 0) return null;
  const list =
    names.length === 1 ? names[0] : `${names.slice(0, -1).join(', ')} and ${names.at(-1)}`;
  return `Doesn't include ${list}.`;
}

/** About 3 lines on a phone: longer summaries start folded, with See more. */
export function needsSeeMore(summary: string): boolean {
  return summary.length > 140;
}
