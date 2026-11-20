import { addedByText } from './addedBy';

const names = new Map([
  ['me', { display_name: 'Ben' }],
  ['alex', { display_name: 'Alex' }],
]);

test('who added an item, in plain words', () => {
  expect(addedByText({ added_by: 'member', added_by_member_id: 'me' }, 'me', names)).toBe(
    'Added by you',
  );
  expect(addedByText({ added_by: 'member', added_by_member_id: 'alex' }, 'me', names)).toBe(
    'Added by Alex',
  );
  expect(addedByText({ added_by: 'agent', added_by_member_id: null }, 'me', names)).toBe(
    'Added by Sweep',
  );
});

test("someone who has left the Household isn't named", () => {
  expect(addedByText({ added_by: 'member', added_by_member_id: 'gone' }, 'me', names)).toBe(
    'Added by a former member',
  );
  expect(addedByText({ added_by: 'member', added_by_member_id: null }, 'me', names)).toBe(
    'Added by a former member',
  );
});
