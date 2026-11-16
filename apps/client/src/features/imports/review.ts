/**
 * The review screen's rules (slice 4d), as pure functions.
 *
 * Every way a recipe comes in (paste, photo, link, file, typed, or editing one already
 * saved) ends on the same screen, so they all become one `ReviewForm` first. Nothing is
 * stored until Save; the marks only tell a person where to look, and never block Save.
 */
import type { Course } from '@/features/recipes/courses';
import type { components } from '@/lib/api/schema';

type Draft = components['schemas']['ImportDraftOut'];
type DraftLine = components['schemas']['DraftLineOut'];
type SavedLine = components['schemas']['RecipeIngredientOut'];
type Recipe = components['schemas']['RecipeOut'];
type Ingredient = components['schemas']['IngredientOut'];
export type ImportedRecipeIn = components['schemas']['ImportedRecipeIn'];

export type FormLine = {
  key: string; // stable across edits, for React lists ("1 egg" can be there twice)
  rawText: string;
  ingredient: Ingredient | null;
  needsReview: boolean; // unmatched, and something people shop for
  check: boolean; // Sweep wants a person to look: from a photo, or not found in the text
  memberLinked: boolean; // chosen in the Link sheet: the server must keep this choice
  pending: boolean; // just added: the server hasn't read it yet
};

export type ReviewForm = {
  title: string;
  servings: string; // as typed; checked by saveProblems
  minutes: string;
  course: Course | null;
  courseGuess: Course | null; // Sweep's guess, labelled on screen; null when editing
  cuisine: string | null;
  lines: FormLine[];
  method: string[] | null;
  sourceUrl: string | null;
  moreRecipes: boolean;
};

export type Mark = 'check' | 'not_linked';

let nextKey = 0;
const key = () => `line-${++nextKey}`;

function fromLine(line: DraftLine | SavedLine, check: boolean): FormLine {
  return {
    key: key(),
    rawText: line.raw_text,
    ingredient: line.ingredient,
    needsReview: line.needs_review,
    check,
    memberLinked: line.parse_method === 'member',
    pending: false,
  };
}

const numberText = (n: number | null) => (n === null ? '' : String(n));

export function formFromDraft(draft: Draft): ReviewForm {
  return {
    title: draft.title ?? '',
    servings: numberText(draft.servings),
    minutes: numberText(draft.total_minutes),
    course: draft.course,
    courseGuess: draft.course,
    cuisine: draft.cuisine,
    lines: draft.lines.map((l) => fromLine(l, l.check)),
    method: draft.method,
    sourceUrl: draft.source_url,
    moreRecipes: draft.more_recipes,
  };
}

/** Editing a saved one: same screen, no guess, and no Check (that was about the import). */
export function formFromRecipe(recipe: Recipe): ReviewForm {
  return {
    title: recipe.title,
    servings: numberText(recipe.servings),
    minutes: numberText(recipe.total_minutes),
    course: recipe.course,
    courseGuess: null,
    cuisine: recipe.cuisine,
    lines: recipe.ingredients.map((l) => fromLine(l, false)),
    method: recipe.method,
    sourceUrl: recipe.source_url,
    moreRecipes: false,
  };
}

/** Typed from nothing (the Type door). */
export function emptyForm(): ReviewForm {
  return {
    title: '',
    servings: '',
    minutes: '',
    course: null,
    courseGuess: null,
    cuisine: null,
    lines: [],
    method: [],
    sourceUrl: null,
    moreRecipes: false,
  };
}

export function lineMarks(line: FormLine): Mark[] {
  const marks: Mark[] = [];
  if (line.check) marks.push('check');
  if (!line.ingredient && line.needsReview) marks.push('not_linked');
  return marks;
}

/** The Member picked it in the Link sheet: they've looked, so the marks go. */
export function linkLine(line: FormLine, ingredient: Ingredient): FormLine {
  return { ...line, ingredient, needsReview: false, check: false, memberLinked: true };
}

export function addLine(form: ReviewForm, text: string): ReviewForm {
  const rawText = text.trim();
  if (!rawText) return form;
  const added: FormLine = {
    key: key(),
    rawText,
    ingredient: null,
    needsReview: false,
    check: false,
    memberLinked: false,
    pending: true,
  };
  return { ...form, lines: [...form.lines, added] };
}

/** The server's reading of lines that were `pending`, in the same order. */
export function readLines(form: ReviewForm, read: SavedLine[]): ReviewForm {
  const queue = [...read];
  return {
    ...form,
    lines: form.lines.map((l) => {
      if (!l.pending) return l;
      const r = queue.shift();
      return r ? { ...fromLine(r, false), key: l.key } : l;
    }),
  };
}

export function removeLine(form: ReviewForm, lineKey: string): ReviewForm {
  return { ...form, lines: form.lines.filter((l) => l.key !== lineKey) };
}

export type Problems = Partial<
  Record<'title' | 'servings' | 'minutes' | 'course' | 'lines', string>
>;

const wholeNumber = (text: string) => (/^\d+$/.test(text.trim()) ? Number(text.trim()) : null);

export function saveProblems(form: ReviewForm): Problems {
  const problems: Problems = {};
  if (!form.title.trim()) problems.title = 'Give it a name.';
  const servings = wholeNumber(form.servings);
  if (servings === null || servings < 1 || servings > 50) {
    problems.servings = 'How many does it serve? A number from 1 to 50.';
  }
  if (form.minutes.trim()) {
    const minutes = wholeNumber(form.minutes);
    if (minutes === null || minutes < 1 || minutes > 1440) {
      problems.minutes = 'Minutes: a whole number up to 1440, or leave it empty.';
    }
  }
  if (!form.course) problems.course = 'Pick a Course.';
  if (form.lines.length === 0) problems.lines = 'Add at least one ingredient.';
  return problems;
}

/** Only call once saveProblems is empty. */
export function toImportedRecipe(form: ReviewForm): ImportedRecipeIn {
  const method = (form.method ?? []).map((s) => s.trim()).filter(Boolean);
  return {
    title: form.title.trim(),
    servings: Number(form.servings.trim()),
    total_minutes: form.minutes.trim() ? Number(form.minutes.trim()) : null,
    course: form.course as Course,
    cuisine: form.cuisine,
    lines: form.lines.map((l) => ({
      raw_text: l.rawText,
      // Only a Member's own choice: the server matches the rest the same way it did.
      ingredient_id: l.memberLinked && l.ingredient ? l.ingredient.id : null,
    })),
    method: method.length ? method : null,
    source_url: form.sourceUrl,
  };
}

/** For "leave without saving?": compares what would be saved, not the keys. */
export function hasChanges(start: ReviewForm, now: ReviewForm): boolean {
  const comparable = (f: ReviewForm) =>
    JSON.stringify({
      ...f,
      courseGuess: null,
      lines: f.lines.map((l) => [l.rawText, l.ingredient?.id ?? null, l.memberLinked]),
    });
  return comparable(start) !== comparable(now);
}

const UNIT =
  /^(g|kg|ml|l|cups?|tbsp|tsp|tablespoons?|teaspoons?|x|pinch|handful|bunch|cloves?|cans?|tins?|jars?|packets?|sachets?|bottles?|of)$/i;

/** What the Link sheet's search starts with: the line without its amount, unit or note. */
export function searchGuess(line: string): string {
  const words = line
    .split(',')[0]
    .replace(/\([^)]*\)/g, ' ')
    .trim()
    .split(/\s+/);
  while (words.length && (/^[\d/.½⅓⅔¼¾⅛-]+[a-z]*$/i.test(words[0]) || UNIT.test(words[0]))) {
    words.shift();
  }
  return words.join(' ') || line.trim();
}
