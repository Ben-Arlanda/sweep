/// <reference types="jest" />
/// <reference types="node" />
// (Node types only in this file: it reads the API's data files from the repo.)
import { readFileSync, readdirSync } from 'fs';
import { join } from 'path';

import { CATEGORY_EMOJI, INGREDIENT_EMOJI, ingredientEmoji, recipeEmoji } from './foodEmoji';

// The API's reference data, read straight from the repo: when someone adds an Ingredient
// or a Seed Recipe there, these tests make sure it gets an emoji here too.
const API_DATA = join(__dirname, '../../../../services/api/app/data');

const ingredientNames = [
  ...readFileSync(join(API_DATA, 'ingredients.py'), 'utf8').matchAll(/SeedIngredient\(\s*"([^"]+)"/g),
].map((m) => m[1]);

const recipeTitles = readdirSync(join(API_DATA, 'recipes'))
  .filter((f) => f.endsWith('.toml'))
  .flatMap((f) =>
    [...readFileSync(join(API_DATA, 'recipes', f), 'utf8').matchAll(/^title = "(.+)"$/gm)].map(
      (m) => m[1],
    ),
  );

test('found the API data (guards against a wrong path making the next tests pass trivially)', () => {
  expect(ingredientNames.length).toBeGreaterThan(200);
  expect(recipeTitles.length).toBeGreaterThan(150);
});

test('every Ingredient has its own emoji', () => {
  expect(ingredientNames.filter((name) => !(name in INGREDIENT_EMOJI))).toEqual([]);
});

test('every Seed Recipe gets a specific emoji, not the plate fallback', () => {
  expect(recipeTitles.filter((title) => recipeEmoji(title) === '🍽️')).toEqual([]);
});

test('falls back to the category, then a basket', () => {
  expect(ingredientEmoji({ name: 'dragon fruit', category: 'produce' })).toBe(CATEGORY_EMOJI.produce);
  expect(ingredientEmoji({ name: 'mystery', category: 'unknown' })).toBe('🛒');
  expect(ingredientEmoji(null)).toBe('🛒'); // a free-text list item
});

test.each([
  ['Chicken katsu curry', '🍛'], // the dish beats the meat
  ['Fish tacos', '🌮'],
  ['Tropical fruit salad', '🍓'],
  ['Greek salad', '🥗'],
  ['Spaghetti bolognese', '🍝'],
])('%s → %s', (title, emoji) => {
  expect(recipeEmoji(title)).toBe(emoji);
});
