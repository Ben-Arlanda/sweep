import { lineCaption } from './lines';

const sausage = {
  raw_text: '200 g andouille or smoked sausage (sliced)',
  ingredient: { name: 'smoked sausage' },
  quantity: '200',
  unit: 'g',
  note: 'or andouille sausage; sliced 0.5 cm thick',
  optional: false,
};

describe('lineCaption', () => {
  it('shows the amount, then each part of the note (ADR 0032)', () => {
    expect(lineCaption(sausage)).toBe('200 g · or andouille sausage · sliced 0.5 cm thick');
  });

  it('adds optional last, and works without an amount or note', () => {
    expect(lineCaption({ ...sausage, quantity: null, note: null, optional: true })).toBe(
      '200 g andouille or smoked sausage (sliced) · optional',
    );
    expect(lineCaption({ ...sausage, note: null })).toBe('200 g');
  });

  it('a line with no Ingredient (water) shows just its note', () => {
    expect(lineCaption({ ...sausage, ingredient: null, note: 'boiling' })).toBe('boiling');
  });
});
