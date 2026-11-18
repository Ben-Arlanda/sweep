/// <reference types="jest" />
import { isPlaceFilter } from './places';

test('only All and the three Places are filters', () => {
  expect(['all', 'fridge', 'freezer', 'cupboard'].every(isPlaceFilter)).toBe(true);
  expect(isPlaceFilter('pantry')).toBe(false);
});
