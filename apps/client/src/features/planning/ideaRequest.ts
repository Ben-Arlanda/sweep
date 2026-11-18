/**
 * What the Dinner ideas setup asked for (slice 6f), carried to the shared Dinner Ideas
 * screen as route params, then turned into the `/dinner-ideas` query. Pure, so tested.
 */
import type { components } from '@/lib/api/schema';

export type Mood = components['schemas']['Mood'];
/** A one-off lean for this search. Healthy has no data, so Sweep is asked instead. */
export type Lean = 'healthy' | 'quick' | 'vegetarian';
/** The chips on the ideas screen. */
export type IdeaFilter = 'all' | 'quick' | 'kitchen' | 'vegetarian';

export type IdeaRequest = {
  mood: Mood;
  q: string;
  lean: Lean | null;
  maxMinutes: number | null;
  serves: number | null;
};

const MOODS: Mood[] = ['kitchen', 'surprise', 'specific'];
const LEANS: Lean[] = ['healthy', 'quick', 'vegetarian'];
const QUICK = 30;

type Params = Record<string, string | string[] | undefined>;

export function toParams(r: IdeaRequest): Record<string, string> {
  return {
    mood: r.mood,
    ...(r.q.trim() ? { q: r.q.trim() } : {}),
    ...(r.lean ? { lean: r.lean } : {}),
    ...(r.maxMinutes ? { max: String(r.maxMinutes) } : {}),
    ...(r.serves ? { serves: String(r.serves) } : {}),
  };
}

const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);

function count(v: string | string[] | undefined, max: number): number | null {
  const n = Number(one(v));
  return Number.isInteger(n) && n > 0 && n <= max ? n : null;
}

/** Route params back to a request. Anything odd (an edited link) becomes the default. */
export function fromParams(p: Params): IdeaRequest {
  const q = one(p.q)?.trim().slice(0, 200) ?? '';
  const asked = MOODS.find((m) => m === one(p.mood)) ?? 'kitchen';
  return {
    mood: asked === 'specific' && !q ? 'kitchen' : asked,
    q: asked === 'specific' ? q : '',
    lean: LEANS.find((l) => l === one(p.lean)) ?? null,
    maxMinutes: count(p.max, 1440),
    serves: count(p.serves, 24),
  };
}

type Query = {
  mood: Mood;
  q?: string;
  max_minutes?: number;
  nothing_to_buy?: boolean;
  vegetarian?: boolean;
};

/** The request plus the chip picked on the ideas screen, as `/dinner-ideas` params. */
export function ideaQuery(r: IdeaRequest, filter: IdeaFilter): Query {
  const limits = [r.maxMinutes, filter === 'quick' || r.lean === 'quick' ? QUICK : null].filter(
    (n): n is number => n !== null,
  );
  return {
    mood: r.mood,
    ...(r.mood === 'specific' ? { q: r.q } : {}),
    ...(limits.length ? { max_minutes: Math.min(...limits) } : {}),
    ...(filter === 'kitchen' ? { nothing_to_buy: true } : {}),
    ...(filter === 'vegetarian' || r.lean === 'vegetarian' ? { vegetarian: true } : {}),
  };
}
