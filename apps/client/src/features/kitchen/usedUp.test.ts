import { goneText, undoSteps, type Gone } from './usedUp';

const cheese: Gone = {
  ingredientId: 'i-cheese',
  name: 'goat cheese',
  kind: 'tracked',
  quantity: '150',
  place: 'freezer',
  listId: 'l1',
  listItemId: 'li1',
};
const milk: Gone = {
  ...cheese,
  ingredientId: 'i-milk',
  name: 'milk',
  kind: 'staple',
  quantity: null,
};

describe('goneText', () => {
  it('says where it went', () => {
    expect(goneText(cheese)).toBe('Goat cheese used up, and on your list');
    expect(goneText(milk)).toBe('Milk ran out, and is on your list');
  });
  it('says so when it was already on the list', () => {
    expect(goneText({ ...milk, listItemId: null })).toBe(
      'Milk ran out. It was already on your list',
    );
  });
});

describe('undoSteps', () => {
  it('a Tracked item comes back with its amount and its Place, and leaves the list', () => {
    expect(undoSteps(cheese)).toEqual([
      { do: 'setAmount', ingredientId: 'i-cheese', quantity: '150' },
      { do: 'setPlace', ingredientId: 'i-cheese', place: 'freezer' },
      { do: 'removeFromList', listId: 'l1', itemId: 'li1' },
    ]);
  });
  it('a Staple is "have" again', () => {
    expect(undoSteps(milk)).toEqual([
      { do: 'have', ingredientId: 'i-milk' },
      { do: 'removeFromList', listId: 'l1', itemId: 'li1' },
    ]);
  });
  it("never removes a list item it didn't add", () => {
    expect(undoSteps({ ...milk, listItemId: null })).toEqual([
      { do: 'have', ingredientId: 'i-milk' },
    ]);
  });
});
