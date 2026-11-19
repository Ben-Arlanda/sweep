/// <reference types="jest" />
import { stepsFor, WEEK_STEPS } from './steps';

const states = (tools: string[], finished = false) =>
  stepsFor(WEEK_STEPS, tools, finished).map((s) => s.state);

test('before any tool, the first step is the one working', () => {
  expect(states([])).toEqual(['active', 'waiting', 'waiting']);
});

test('choosing recipes means the Kitchen check is done', () => {
  expect(states(['get_kitchen', 'recipes_from_kitchen', 'set_planned_meal'])).toEqual([
    'done',
    'active',
    'waiting',
  ]);
});

test('working out the shopping is the last step, and never jumps back', () => {
  expect(states(['recipes_from_kitchen', 'check_kitchen_coverage', 'get_recipe'])).toEqual([
    'done',
    'done',
    'active',
  ]);
});

test('every step is done once the plan arrives, and unknown tools count as the first', () => {
  expect(states(['something_new'])).toEqual(['active', 'waiting', 'waiting']);
  expect(states([], true)).toEqual(['done', 'done', 'done']);
});
