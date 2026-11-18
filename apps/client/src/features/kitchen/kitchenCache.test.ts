import { withoutItem } from './kitchenCache';

const kitchen = {
  version: 3,
  tracked: [{ ingredient: { id: 'rice' } }, { ingredient: { id: 'kale' } }],
  staples: [{ ingredient: { id: 'salt' } }],
};

describe('withoutItem', () => {
  it('takes a Tracked item out, leaving the rest', () => {
    const after = withoutItem(kitchen, 'rice');
    expect(after.tracked.map((i) => i.ingredient.id)).toEqual(['kale']);
    expect(after.staples).toEqual(kitchen.staples);
  });

  it('takes a Staple out', () => {
    expect(withoutItem(kitchen, 'salt').staples).toEqual([]);
  });

  it("doesn't change the original (the cache keeps it for a rollback)", () => {
    withoutItem(kitchen, 'rice');
    expect(kitchen.tracked).toHaveLength(2);
  });
});
