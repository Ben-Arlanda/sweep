import { parseHouseholdSize } from './form';

describe('parseHouseholdSize', () => {
  it.each([
    ['', { value: null, error: null }],
    ['  ', { value: null, error: null }],
    ['4', { value: 4, error: null }],
    [' 12 ', { value: 12, error: null }],
  ])('%j is fine', (text, expected) => {
    expect(parseHouseholdSize(text)).toEqual(expected);
  });

  it.each(['0', '21', '2.5', 'four', '-3'])('%j is rejected with a reason', (text) => {
    expect(parseHouseholdSize(text)).toEqual({
      value: null,
      error: 'Enter a whole number from 1 to 20.',
    });
  });
});
