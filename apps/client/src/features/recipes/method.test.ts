import { cookSteps, isMethodView, metaParts, viewsOf } from './method';

const stages = [
  { title: 'Soften the onion', minutes: 10, steps: ['Heat the oil.', 'Cook the onion.'] },
  { title: 'Simmer', minutes: 25, steps: ['Add the tomatoes and simmer.'] },
];
const seed = {
  method: ['Soften the onion in the oil.', 'Simmer with the tomatoes.'],
  stages,
  prep_minutes: 20,
  cook_minutes: 155,
  total_minutes: 175,
  difficulty: 'easy' as const,
  servings: 4,
  course: 'main' as const,
};
const imported = {
  ...seed,
  stages: null,
  prep_minutes: null,
  cook_minutes: null,
  difficulty: null,
  total_minutes: 40,
};

test('a recipe with stages offers both views, Detailed first', () => {
  expect(viewsOf(seed)).toEqual(['detailed', 'quick']);
  expect(viewsOf(imported)).toEqual(['quick']);
  expect(viewsOf({ ...seed, stages: [] })).toEqual(['quick']);
});

test('Cook Mode walks the stages step by step, naming each stage', () => {
  expect(cookSteps(seed, 'detailed')).toEqual([
    { stage: 'Soften the onion', text: 'Heat the oil.' },
    { stage: 'Soften the onion', text: 'Cook the onion.' },
    { stage: 'Simmer', text: 'Add the tomatoes and simmer.' },
  ]);
});

test('Cook Mode in the Quick View uses the short steps, with no stage names', () => {
  expect(cookSteps(seed, 'quick')).toEqual([
    { stage: null, text: 'Soften the onion in the oil.' },
    { stage: null, text: 'Simmer with the tomatoes.' },
  ]);
  // Without stages there is only the Quick View, whatever was remembered.
  expect(cookSteps(imported, 'detailed').map((s) => s.stage)).toEqual([null, null]);
  expect(cookSteps({ ...imported, method: null }, 'quick')).toEqual([]);
});

test('the meta line splits prep and cook time, without how hard it is', () => {
  expect(metaParts(seed)).toEqual(['Prep 20 min', 'Cook 2 h 35 min', 'Serves 4', 'Main']);
  expect(metaParts(imported)).toEqual(['40 min', 'Serves 4', 'Main']);
  expect(metaParts({ ...seed, prep_minutes: 0 })).toEqual(['Cook 2 h 35 min', 'Serves 4', 'Main']);
});

test('only a known view is remembered', () => {
  expect(isMethodView('quick')).toBe(true);
  expect(isMethodView('detailed')).toBe(true);
  expect(isMethodView('fast')).toBe(false);
  expect(isMethodView(null)).toBe(false);
});
