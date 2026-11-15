import { additionLine, formatAddition, formatDay } from './format';

describe('formatDay', () => {
  it('reads an ISO date as a local day, not UTC midnight', () => {
    // new Date('2026-11-16') is midnight UTC, which is still the 15th in the Americas.
    expect(formatDay('2026-11-16')).toBe('Mon 16 Nov');
  });

  it('falls back to the raw text if it is not a date', () => {
    expect(formatDay('soon')).toBe('soon');
  });
});

describe('formatAddition', () => {
  it.each([
    [{ name: 'eggs', quantity: 6, unit: 'count' }, '6 eggs'],
    [{ name: 'canned tomatoes', quantity: 1200, unit: 'g' }, '1.2 kg canned tomatoes'],
    [{ name: 'coriander', quantity: 1, unit: 'bunch' }, '1 bunch coriander'],
    [{ name: 'garlic', quantity: null, unit: null }, 'garlic'],
  ])('%j → %s', (item, expected) => {
    expect(formatAddition(item)).toBe(expected);
  });
});

describe('additionLine', () => {
  it('says how much is already on the list, since the addition is the extra', () => {
    expect(additionLine({ name: 'sausages', quantity: 4, unit: 'count', on_list: '4' })).toBe(
      '4 more sausages (4 on the list)',
    );
    expect(additionLine({ name: 'rice', quantity: 300, unit: 'g', on_list: '500 g' })).toBe(
      '300 g more rice (500 g on the list)',
    );
  });

  it('is just the addition when nothing is on the list', () => {
    expect(additionLine({ name: 'eggs', quantity: 6, unit: 'count', on_list: null })).toBe(
      '6 eggs',
    );
  });
});
