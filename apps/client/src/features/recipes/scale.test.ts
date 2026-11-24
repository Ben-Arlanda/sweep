import { formatQuantity, scaleLine, unitText } from './scale';

const line = (quantity: string | null, unit: string | null, extra = {}) => ({
  raw_text: 'a line',
  ingredient: { name: 'onion' },
  quantity,
  unit,
  base_quantity: quantity,
  note: null as string | null,
  optional: false,
  ...extra,
});

describe('scaleLine', () => {
  it('leaves a line alone at its own servings', () => {
    const l = line('2', null);
    expect(scaleLine(l, 1)).toBe(l);
  });

  it('scales counts to halves below 2 and whole ones above, never below a half', () => {
    expect(scaleLine(line('1', null), 1.5).quantity).toBe('1.5');
    expect(scaleLine(line('3', null), 2 / 4).quantity).toBe('1.5');
    expect(scaleLine(line('1', null), 1 / 4).quantity).toBe('0.5');
    expect(scaleLine(line('3', null), 6 / 4).quantity).toBe('5'); // never 4½ eggs
    expect(scaleLine(line('3', 'clove'), 5 / 4).quantity).toBe('4');
  });

  it('scales spoons and cups to kitchen fractions', () => {
    expect(scaleLine(line('1', 'tsp'), 1 / 4).quantity).toBe('0.25');
    expect(scaleLine(line('0.25', 'cup'), 1 / 2).quantity).toBe('0.125');
    expect(scaleLine(line('1', 'tbsp'), 2 / 3).quantity).toBe(String(2 / 3));
  });

  it('rounds weights to tidy numbers and moves to kg past 1000 g', () => {
    expect(scaleLine(line('400', 'g'), 6 / 4)).toMatchObject({ quantity: '600', unit: 'g' });
    expect(scaleLine(line('150', 'ml'), 3 / 4).quantity).toBe('110');
    expect(scaleLine(line('35', 'g'), 1 / 2).quantity).toBe('20');
    expect(scaleLine(line('600', 'g'), 2)).toMatchObject({ quantity: '1.2', unit: 'kg' });
    expect(scaleLine(line('750', 'ml'), 2)).toMatchObject({ quantity: '1.5', unit: 'l' });
    expect(scaleLine(line('1', 'kg'), 1 / 4)).toMatchObject({ quantity: '250', unit: 'g' });
  });

  it('scales the exact base amount too, so the Kitchen check stays right', () => {
    expect(scaleLine(line('400', 'g'), 1.5).base_quantity).toBe('600');
    expect(scaleLine(line(null, null, { base_quantity: null }), 2).base_quantity).toBeNull();
  });

  it('scales "about 600 g" in a note, but not a size like "400 g each"', () => {
    const breasts = line('2', null, { note: 'about 600 g' });
    expect(scaleLine(breasts, 2).note).toBe('about 1.2 kg');
    const cans = line('2', 'can', { note: '400 g each' });
    expect(scaleLine(cans, 2).note).toBe('400 g each');
  });

  it('scales cups and spoons in a note, written as kitchen fractions', () => {
    const rice = line('4', 'cup', { note: 'from about 1 1/2 cups raw' });
    expect(scaleLine(rice, 6 / 4).note).toBe('from about 2¼ cups raw');
    const cut = line('600', 'g', { note: 'cut into 1.5 cm pieces' });
    expect(scaleLine(cut, 2).note).toBe('cut into 1.5 cm pieces');
  });

  it('leaves a line with no amount as written', () => {
    const salt = line(null, null, { raw_text: 'Salt, to taste' });
    expect(scaleLine(salt, 2)).toMatchObject({ quantity: null, raw_text: 'Salt, to taste' });
  });
});

describe('unitText', () => {
  it('makes units plural past one, except metric and spoons', () => {
    expect(unitText('cup', '6')).toBe('cups');
    expect(unitText('clove', '1')).toBe('clove');
    expect(unitText('bunch', '2')).toBe('bunches');
    expect(unitText('leaf', '3')).toBe('leaves');
    expect(unitText('tbsp', '3')).toBe('tbsp');
    expect(unitText('g', '600')).toBe('g');
  });
});

describe('formatQuantity', () => {
  it('shows kitchen fractions for spoons, cups and counts', () => {
    expect(formatQuantity('0.25', 'tsp')).toBe('¼');
    expect(formatQuantity('1.5', null)).toBe('1½');
    expect(formatQuantity(String(2 / 3), 'cup')).toBe('⅔');
    expect(formatQuantity('0.333', 'cup')).toBe('⅓');
  });

  it('shows weights and volumes as plain numbers', () => {
    expect(formatQuantity('1.25', 'kg')).toBe('1.25');
    expect(formatQuantity('600', 'g')).toBe('600');
  });
});
