import { ruleBreakHint, ruleBreakText } from './ruleBreaks';

it('nothing to say when the recipe can be planned', () => {
  expect(ruleBreakText([])).toBeNull();
  expect(ruleBreakHint([])).toBeNull();
});

it('lists the reasons, up to three', () => {
  expect(ruleBreakText(['soy sauce (gluten free)'])).toBe(
    'Not planned with your Dietary Rules: soy sauce (gluten free).',
  );
  expect(ruleBreakText(['a (x)', 'b (x)', 'c (x)', 'd (x)', 'e (x)'])).toBe(
    'Not planned with your Dietary Rules: a (x), b (x), c (x) and 2 more.',
  );
});

it('suggests linking only when every reason is a line Sweep could not check', () => {
  expect(ruleBreakHint(["satay sauce (couldn't check)"])).toMatch(/link those lines/);
  expect(ruleBreakHint(["satay sauce (couldn't check)", 'soy sauce (gluten free)'])).toBeNull();
});
