/// <reference types="jest" />
import { requestStart, SUGGESTIONS, takeStart } from './starters';

test.each([
  ['week', "Plan this week's dinners, using what's in my Kitchen first."],
  ['tonight', "What can I cook tonight with what's in my Kitchen?"],
] as const)('the %s button starts with a Kitchen-first message', (start, expected) => {
  requestStart(start);

  expect(takeStart()).toBe(expected);
});

test('a request is used once, so a reload or second visit sends nothing', () => {
  requestStart('week');
  takeStart();

  expect(takeStart()).toBeNull();
});

test('nothing is pending unless a button asked', () => {
  expect(takeStart()).toBeNull();
});

test('the chat suggestions start from the Kitchen', () => {
  expect(SUGGESTIONS.filter((s) => s.includes('Kitchen')).length).toBeGreaterThanOrEqual(2);
});
