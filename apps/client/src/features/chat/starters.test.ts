/// <reference types="jest" />
import { planMessage, requestPlan, requestStart, SUGGESTIONS, takeStart } from './starters';

test('"Just tonight" starts a free chat with a Kitchen-first message', () => {
  requestStart('tonight');

  expect(takeStart()).toEqual({
    text: "What can I cook tonight with what's in my Kitchen?",
    plan: null,
  });
});

test('the "Plan my week" sheet hands over the mode and days with its message', () => {
  requestPlan('new', ['2026-11-17', '2026-11-16']);

  expect(takeStart()).toEqual({
    text: 'Plan new recipes to shop for, for Mon 16 and Tue 17 Nov.',
    plan: { mode: 'new', days: ['2026-11-16', '2026-11-17'] },
  });
});

test.each([
  ['kitchen', ['2026-11-18'], "Plan dinner from what's in my Kitchen, for Wed 18 Nov."],
  [
    'kitchen',
    ['2026-11-16', '2026-11-17', '2026-11-18'],
    "Plan dinners from what's in my Kitchen, for Mon 16, Tue 17 and Wed 18 Nov.",
  ],
  [
    'new',
    ['2026-11-30', '2026-12-01'],
    'Plan new recipes to shop for, for Mon 30 Nov and Tue 1 Dec.',
  ],
] as const)('the message names the days (%s, %j)', (mode, days, expected) => {
  expect(planMessage(mode, [...days])).toBe(expected);
});

test('a request is used once, so a reload or second visit sends nothing', () => {
  requestStart('tonight');
  takeStart();

  expect(takeStart()).toBeNull();
});

test('nothing is pending unless a button asked', () => {
  expect(takeStart()).toBeNull();
});

test('the chat suggestions start from the Kitchen', () => {
  expect(SUGGESTIONS.filter((s) => s.includes('Kitchen')).length).toBeGreaterThanOrEqual(2);
});
