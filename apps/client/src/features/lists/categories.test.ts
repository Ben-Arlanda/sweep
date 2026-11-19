import { listSections } from './categories';

const item = (id: string, category: string | null) => ({
  id,
  ingredient: category ? { category } : null,
});

describe('listSections', () => {
  it('groups items by food category in the order you walk a shop', () => {
    const sections = listSections([
      item('ice cream', 'frozen'),
      item('apples', 'produce'),
      item('milk', 'dairy'),
      item('bananas', 'produce'),
    ]);
    expect(sections.map((s) => [s.label, s.items.map((i) => i.id)])).toEqual([
      ['Fruit & Veg', ['apples', 'bananas']],
      ['Dairy & Eggs', ['milk']],
      ['Frozen', ['ice cream']],
    ]);
  });

  it('puts unlinked items and unknown categories under Other, last', () => {
    const sections = listSections([
      item('tape', null),
      item('kombu', 'mystery'),
      item('salt', 'spices'),
    ]);
    expect(sections.map((s) => [s.category, s.items.map((i) => i.id)])).toEqual([
      ['spices', ['salt']],
      ['other', ['tape', 'kombu']],
    ]);
  });

  it('leaves out empty categories', () => {
    expect(listSections([])).toEqual([]);
  });
});
