import type { components } from '@/lib/api/schema';

import {
  addLine,
  formFromDraft,
  formFromRecipe,
  hasChanges,
  lineMarks,
  linkLine,
  removeLine,
  saveProblems,
  searchGuess,
  toImportedRecipe,
  type ReviewForm,
} from './review';

type Draft = components['schemas']['ImportDraftOut'];
type DraftLine = components['schemas']['DraftLineOut'];
type Recipe = components['schemas']['RecipeOut'];
type Ingredient = components['schemas']['IngredientOut'];

const ONION = { id: 'i-onion', name: 'onion' } as Ingredient;
const SHALLOT = { id: 'i-shallot', name: 'shallots' } as Ingredient;

function line(raw: string, changes: Partial<DraftLine> = {}): DraftLine {
  return {
    raw_text: raw,
    ingredient: ONION,
    quantity: '1',
    unit: null,
    base_quantity: '1',
    note: null,
    optional: false,
    needs_review: false,
    parse_method: 'rule',
    check: false,
    ...changes,
  };
}

const DRAFT: Draft = {
  title: "Mum's Beef Ragu",
  servings: 4,
  total_minutes: 120,
  course: 'main',
  cuisine: 'italian',
  lines: [
    line('1 onion'),
    line('2 shallots', { ingredient: null, needs_review: true }),
    line('50 saffron threads', { check: true, ingredient: null, needs_review: true }),
    line('water', { ingredient: null, needs_review: false }), // nobody shops for it
  ],
  method: ['Brown the mince.', 'Simmer.'],
  source_url: null,
  more_recipes: false,
};

describe('formFromDraft', () => {
  it("pre-selects Sweep's Course guess and remembers it was a guess", () => {
    const form = formFromDraft(DRAFT);
    expect(form.course).toBe('main');
    expect(form.courseGuess).toBe('main');
    expect(form.servings).toBe('4');
    expect(form.minutes).toBe('120');
  });

  it('keeps missing numbers empty, never 0', () => {
    const form = formFromDraft({ ...DRAFT, servings: null, total_minutes: null });
    expect(form.servings).toBe('');
    expect(form.minutes).toBe('');
  });

  it('gives every line its own key, even two the same', () => {
    const form = formFromDraft({ ...DRAFT, lines: [line('1 egg'), line('1 egg')] });
    expect(new Set(form.lines.map((l) => l.key)).size).toBe(2);
  });
});

describe('lineMarks', () => {
  const [onion, shallots, saffron, water] = formFromDraft(DRAFT).lines;

  it('a matched line from the text has no mark', () => {
    expect(lineMarks(onion)).toEqual([]);
  });

  it('an unmatched line is Not linked', () => {
    expect(lineMarks(shallots)).toEqual(['not_linked']);
  });

  it('a line not found in the text is Check, and can be Not linked too', () => {
    expect(lineMarks(saffron)).toEqual(['check', 'not_linked']);
  });

  it("something nobody shops for isn't Not linked", () => {
    expect(lineMarks(water)).toEqual([]);
  });

  it('linking a line by hand clears both marks: a person has looked at it', () => {
    expect(lineMarks(linkLine(saffron, SHALLOT))).toEqual([]);
  });
});

describe('saveProblems', () => {
  const ok = formFromDraft(DRAFT);

  it('a complete form can be saved, marks or not', () => {
    expect(saveProblems(ok)).toEqual({});
  });

  it.each<[string, Partial<ReviewForm>, string]>([
    ['title', { title: '   ' }, 'Give it a name.'],
    ['servings', { servings: '' }, 'How many does it serve? A number from 1 to 50.'],
    ['servings', { servings: '0' }, 'How many does it serve? A number from 1 to 50.'],
    ['servings', { servings: '2.5' }, 'How many does it serve? A number from 1 to 50.'],
    ['servings', { servings: '51' }, 'How many does it serve? A number from 1 to 50.'],
    ['minutes', { minutes: 'ages' }, 'Minutes: a whole number up to 1440, or leave it empty.'],
    ['course', { course: null }, 'Pick a Course.'],
    ['lines', { lines: [] }, 'Add at least one ingredient.'],
  ])('%s: %j', (field, change, message) => {
    expect(saveProblems({ ...ok, ...change })).toEqual({ [field]: message });
  });

  it('minutes are optional', () => {
    expect(saveProblems({ ...ok, minutes: '' })).toEqual({});
  });
});

describe('toImportedRecipe', () => {
  it('sends what the Member sees, with numbers as numbers', () => {
    const body = toImportedRecipe({ ...formFromDraft(DRAFT), title: '  Ragu  ', minutes: '' });
    expect(body).toMatchObject({
      title: 'Ragu',
      servings: 4,
      total_minutes: null,
      course: 'main',
      cuisine: 'italian',
      method: ['Brown the mince.', 'Simmer.'],
      source_url: null,
    });
  });

  it('sends an Ingredient only for lines the Member linked (the server matches the rest)', () => {
    const form = formFromDraft(DRAFT);
    const linked = {
      ...form,
      lines: form.lines.map((l, i) => (i === 1 ? linkLine(l, SHALLOT) : l)),
    };
    expect(toImportedRecipe(linked).lines).toEqual([
      { raw_text: '1 onion', ingredient_id: null },
      { raw_text: '2 shallots', ingredient_id: 'i-shallot' },
      { raw_text: '50 saffron threads', ingredient_id: null },
      { raw_text: 'water', ingredient_id: null },
    ]);
  });

  it('drops empty method steps, and sends no method when none are left', () => {
    const form = { ...formFromDraft(DRAFT), method: ['  ', ''] };
    expect(toImportedRecipe(form).method).toBeNull();
  });
});

describe('editing a saved Imported Recipe', () => {
  const recipe = {
    id: 'r1',
    kind: 'imported',
    title: 'Ragu',
    summary: '',
    cuisine: null,
    course: 'main',
    servings: 4,
    total_minutes: null,
    ingredients: [
      line('1 onion', { parse_method: 'member' }),
      line('2 shallots', { ingredient: null, needs_review: true }),
    ],
    method: null,
    source_url: 'https://example.com/ragu',
    licence: null,
    attribution: null,
  } as unknown as Recipe;

  it("keeps a Member's earlier link, and isn't a guess", () => {
    const form = formFromRecipe(recipe);
    expect(form.courseGuess).toBeNull();
    expect(toImportedRecipe(form).lines[0]).toEqual({
      raw_text: '1 onion',
      ingredient_id: 'i-onion',
    });
    expect(form.sourceUrl).toBe('https://example.com/ragu');
  });

  it('shows Not linked still, but never Check (that was about the import)', () => {
    expect(formFromRecipe(recipe).lines.map(lineMarks)).toEqual([[], ['not_linked']]);
  });
});

describe('hasChanges', () => {
  const start = formFromDraft(DRAFT);

  it('an untouched form has none', () => {
    expect(hasChanges(start, formFromDraft(DRAFT))).toBe(false);
  });

  it.each<[string, (f: ReviewForm) => ReviewForm]>([
    ['title', (f) => ({ ...f, title: 'Other' })],
    ['a link', (f) => ({ ...f, lines: f.lines.map((l, i) => (i ? l : linkLine(l, SHALLOT))) })],
    ['a removed line', (f) => removeLine(f, f.lines[0].key)],
    ['an added line', (f) => addLine(f, '1 egg')],
  ])('%s is a change', (_, change) => {
    expect(hasChanges(start, change(start))).toBe(true);
  });
});

describe('addLine', () => {
  it('trims, skips empty text, and adds at the end unlinked', () => {
    const start = formFromDraft(DRAFT);
    expect(addLine(start, '   ')).toBe(start);
    const added = addLine(start, '  1 egg ');
    expect(added.lines.at(-1)).toMatchObject({ rawText: '1 egg', ingredient: null, pending: true });
  });
});

describe('searchGuess', () => {
  it.each([
    ['2 shallots, sliced', 'shallots'],
    ['1/2 tsp cooking salt', 'cooking salt'],
    ['1 1/2 cups (150g) cheddar, shredded', 'cheddar'],
    ['4 x 180g salmon fillets', 'salmon fillets'],
    ['½ cup pickled jalapeño', 'pickled jalapeño'],
    ['Parsley, to serve', 'Parsley'],
    ['3', '3'], // nothing left: keep what was written
  ])('%j → %j', (line, guess) => {
    expect(searchGuess(line)).toBe(guess);
  });
});
