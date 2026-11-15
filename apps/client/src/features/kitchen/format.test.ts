/// <reference types="jest" />
import { displayName, formatAmount } from './format';

test.each([
  ['1500', 'g', '1.5 kg'],
  ['500', 'g', '500 g'],
  ['2500', 'ml', '2.5 L'],
  ['250', 'ml', '250 ml'],
  ['6', 'count', '6'],
  ['1000', 'g', '1 kg'],
  [null, 'g', 'Some'],
])('shows %s %s as %s', (quantity, unit, expected) => {
  expect(formatAmount(quantity, unit)).toBe(expected);
});

test.each([
  ['greek yoghurt', 'Greek yoghurt'],
  ['salt', 'Salt'],
  ['', ''],
])('displays %j as %j', (name, expected) => {
  expect(displayName(name)).toBe(expected);
});
