import { leftOutText, needsSeeMore, nutritionRows } from './nutrition';

const perServe = {
  energy_kj: 2092,
  protein_g: 34.4,
  fat_g: 20.6,
  saturated_fat_g: 6.2,
  carbs_g: 41.5,
  sugars_g: 0.3,
  fibre_g: 5,
  sodium_mg: 812.4,
};

test('energy reads as kJ with Cal after it, both whole and with commas', () => {
  expect(nutritionRows(perServe)[0]).toEqual({
    label: 'Energy',
    sub: false,
    amount: '2,092 kJ (500 Cal)',
    spoken: '2,092 kilojoules, 500 calories',
    percent: 24, // of 8,700 kJ
  });
});

test('the eight nutrients come in label order, with saturated and sugars under their parents', () => {
  const rows = nutritionRows(perServe);
  expect(rows.map((r) => r.label)).toEqual([
    'Energy',
    'Protein',
    'Fat',
    'Saturated',
    'Carbohydrate',
    'Sugars',
    'Fibre',
    'Sodium',
  ]);
  expect(rows.filter((r) => r.sub).map((r) => r.label)).toEqual(['Saturated', 'Sugars']);
});

test('amounts are whole numbers, and % Daily Intake uses the Australian reference values', () => {
  const byLabel = Object.fromEntries(nutritionRows(perServe).map((r) => [r.label, r]));
  expect(byLabel.Protein).toMatchObject({ amount: '34 g', percent: 69 }); // of 50 g
  expect(byLabel.Sodium).toMatchObject({ amount: '812 mg', percent: 35, spoken: '812 milligrams' });
  expect(byLabel.Fibre).toMatchObject({ amount: '5 g', percent: 17 }); // of 30 g
});

test('a little that rounds to nothing says less than 1', () => {
  const sugars = nutritionRows(perServe).find((r) => r.label === 'Sugars');
  expect(sugars).toMatchObject({ amount: '<1 g', percent: 0, spoken: 'less than 1 gram' });
  const none = nutritionRows({ ...perServe, sugars_g: 0 }).find((r) => r.label === 'Sugars');
  expect(none?.amount).toBe('0 g');
});

test('lines we could not count are named in a sentence', () => {
  expect(leftOutText([])).toBeNull();
  expect(leftOutText(['ginger'])).toBe("Doesn't include ginger.");
  expect(leftOutText(['ginger', 'curry leaves', 'lemongrass'])).toBe(
    "Doesn't include ginger, curry leaves and lemongrass.",
  );
});

test('only a long summary gets See more', () => {
  expect(needsSeeMore('Golden chicken with lemon.')).toBe(false);
  expect(needsSeeMore('word '.repeat(40))).toBe(true);
});
