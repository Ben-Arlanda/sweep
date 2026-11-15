/// <reference types="jest" />
import { SUGGESTIONS, starterMessage } from './starters';

test.each([
  ['week', "Plan dinners for this week from what's in my Kitchen."],
  ['tonight', "What can I cook tonight with what's in my Kitchen?"],
])('the %s button starts with a Kitchen-first message', (start, expected) => {
  expect(starterMessage(start)).toBe(expected);
});

test.each([undefined, '', 'other', ['week', 'tonight']])(
  'nothing else starts a plan: %p',
  (start) => {
    expect(starterMessage(start)).toBeNull();
  },
);

test('the chat suggestions start from the Kitchen', () => {
  expect(SUGGESTIONS.filter((s) => s.includes('Kitchen')).length).toBeGreaterThanOrEqual(2);
});
