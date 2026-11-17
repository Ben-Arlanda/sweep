/// <reference types="jest" />
import { allowedKinds, editable, kindOf, quickPicks } from './amount';

test('each unit belongs to one kind', () => {
  expect([kindOf('g'), kindOf('kg'), kindOf('ml'), kindOf('L'), kindOf('count')]).toEqual([
    'weight',
    'weight',
    'volume',
    'volume',
    'count',
  ]);
});

test('weight and volume swap only when the density is known; count never does', () => {
  expect([...allowedKinds('g', null)]).toEqual(['weight']);
  expect([...allowedKinds('g', '1.03')].sort()).toEqual(['volume', 'weight']);
  expect([...allowedKinds('count', '1')]).toEqual(['count']);
});

test('the sheet starts in a readable unit', () => {
  expect(editable('1500', 'g')).toEqual({ value: '1.5', unit: 'kg' });
  expect(editable('250', 'ml')).toEqual({ value: '250', unit: 'ml' });
  expect(editable('6', 'count')).toEqual({ value: '6', unit: 'count' });
  expect(editable(null, 'g')).toEqual({ value: '', unit: 'g' });
});

test('quick picks match the design for grams', () => {
  expect(quickPicks('g')).toEqual(['10', '25', '50', '100']);
});
