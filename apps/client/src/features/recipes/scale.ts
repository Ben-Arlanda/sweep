/**
 * Serves: a recipe's amounts for a different number of people. Plain maths, rounded the
 * way a cook measures: tidy grams, spoon fractions, half an onion at the least.
 */
const METRIC = new Set(['g', 'kg', 'ml', 'l']);
const SPOONS = new Set(['tsp', 'tbsp', 'cup']);
const FRACTIONS: [number, string][] = [
  [1 / 8, '⅛'],
  [1 / 4, '¼'],
  [1 / 3, '⅓'],
  [1 / 2, '½'],
  [2 / 3, '⅔'],
  [3 / 4, '¾'],
];

type Scalable = {
  quantity: string | null;
  unit: string | null;
  base_quantity: string | null;
  note: string | null;
};

/** The line for `factor` times its servings (2 = twice as many people). */
export function scaleLine<T extends Scalable>(line: T, factor: number): T {
  if (factor === 1 || line.quantity === null) return line;
  const amount = Number(line.quantity) * factor;
  const [quantity, unit] = METRIC.has(line.unit ?? '')
    ? metric(amount, line.unit as string)
    : [nearest(amount, SPOONS.has(line.unit ?? '') ? 'spoon' : 'count'), line.unit];
  return {
    ...line,
    quantity: String(quantity),
    unit,
    base_quantity:
      line.base_quantity === null ? null : String(round(Number(line.base_quantity) * factor, 3)),
    note: line.note === null ? null : scaleNote(line.note, factor),
  };
}

/** "1½", "⅔", "600": how a scaled amount reads beside its unit. */
export function formatQuantity(quantity: string, unit: string | null): string {
  const n = Number(quantity);
  if (METRIC.has(unit ?? '')) return String(round(n, 2));
  const whole = Math.floor(n + 1e-9);
  const rest = n - whole;
  const fraction = FRACTIONS.find(([f]) => Math.abs(f - rest) < 0.02);
  if (!fraction) return String(round(n, 2));
  return whole ? `${whole}${fraction[1]}` : fraction[1];
}

// "about 600 g", "350 ml": a total that grows with the recipe. "400 g each" is a size.
const NOTE_METRIC = /(\d+(?:\.\d+)?)\s*(kg|g|ml|l)\b(?!\s+each)/gi;
// "1 1/2 cups", "2 tbsp". Centimetres aren't touched: "cut into 1.5 cm pieces" stays.
const NOTE_SPOONS = /(\d+\s+\d+\/\d+|\d+\/\d+|\d+(?:\.\d+)?)\s*(cups?|tbsp|tsp)\b/gi;

function scaleNote(note: string, factor: number): string {
  return note
    .replace(NOTE_METRIC, (_, n: string, unit: string) => {
      const [q, u] = metric(Number(n) * factor, unit.toLowerCase());
      return `${q} ${u}`;
    })
    .replace(NOTE_SPOONS, (_, n: string, unit: string) => {
      const q = String(nearest(parseAmount(n) * factor, 'spoon'));
      const base = unit.toLowerCase().replace(/s$/, '');
      return `${formatQuantity(q, base)} ${unitText(base, q)}`;
    });
}

/** "1 1/2" → 1.5, "3/4" → 0.75, "2.5" → 2.5. */
function parseAmount(text: string): number {
  return text
    .trim()
    .split(/\s+/)
    .reduce((sum, part) => {
      const [top, bottom] = part.split('/');
      return sum + (bottom ? Number(top) / Number(bottom) : Number(top));
    }, 0);
}

const IRREGULAR: Record<string, string> = { leaf: 'leaves', loaf: 'loaves' };

/** "cups" past one; g, ml, tsp and tbsp never change. */
export function unitText(unit: string, quantity: string): string {
  if (METRIC.has(unit) || unit === 'tsp' || unit === 'tbsp' || Number(quantity) <= 1) return unit;
  if (IRREGULAR[unit]) return IRREGULAR[unit];
  return /(ch|sh|s|x)$/.test(unit) ? `${unit}es` : `${unit}s`;
}

/** Grams and millilitres to tidy numbers; past 1000 into kg or L, below 1 kg back to g. */
function metric(amount: number, unit: string): [number, string] {
  const small = unit === 'kg' || unit === 'l' ? amount * 1000 : amount;
  const base = unit === 'kg' || unit === 'g' ? 'g' : 'ml';
  if (small >= 1000) return [round(small / 1000, 2), base === 'g' ? 'kg' : 'l'];
  const step = small < 10 ? 0.5 : small < 100 ? 5 : 10;
  return [Math.max(step, Math.round(small / step) * step), base];
}

/** Spoons to the nearest kitchen fraction (at least ⅛); counts to halves below 2, then whole. */
function nearest(amount: number, kind: 'spoon' | 'count'): number {
  if (kind === 'count')
    return amount < 1.75 ? Math.max(0.5, Math.round(amount * 2) / 2) : Math.round(amount);
  const whole = Math.floor(amount);
  const options = [0, ...FRACTIONS.map(([f]) => f), 1].map((f) => whole + f);
  const best = options.reduce((a, b) => (Math.abs(b - amount) < Math.abs(a - amount) ? b : a));
  return Math.max(1 / 8, best);
}

function round(n: number, places: number): number {
  return Number(n.toFixed(places));
}
