/// <reference types="jest" />
import { newIngredientName, normalise } from './addNew';

test.each([
  ['Chicken  Thighs!', 'chicken thighs'],
  ['  Kale ', 'kale'],
  ['half-and-half', 'half-and-half'],
  ['!!!', ''],
])('normalises %p like the server does', (typed, expected) => {
  expect(normalise(typed)).toBe(expected);
});

test('offers to add a name nothing matches exactly', () => {
  expect(newIngredientName('Chocolate', ['dark chocolate', 'milk chocolate'])).toBe('chocolate');
});

test('does not offer a name that is already there, however it was typed', () => {
  expect(newIngredientName('Rice!', ['rice', 'brown rice'])).toBeNull();
});

test.each(['k', '  ', '!!', 'x'.repeat(81)])('does not offer %p', (typed) => {
  expect(newIngredientName(typed, [])).toBeNull();
});
