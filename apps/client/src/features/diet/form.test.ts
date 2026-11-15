import { budgetText, parseBudget, parseHouseholdSize } from './form';

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

describe('parseBudget', () => {
  it.each([
    ['', null],
    ['150', '150.00'],
    ['$150', '150.00'],
    ['$ 1,250.5', '1250.50'],
    ['99.99', '99.99'],
  ])('%j → %j', (text, value) => {
    expect(parseBudget(text)).toEqual({ value, error: null });
  });

  it.each(['0', '-5', '10001', '12.345', 'lots'])('%j is rejected', (text) => {
    expect(parseBudget(text).error).toBe('Enter an amount up to $10,000, like 150 or 150.50.');
  });
});

describe('budgetText', () => {
  it('shows a saved budget without trailing zero cents', () => {
    expect(budgetText('150.00')).toBe('150');
    expect(budgetText('99.50')).toBe('99.50');
    expect(budgetText(null)).toBe('');
  });
});
