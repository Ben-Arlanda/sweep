import { photoUrl } from './photo';

const IMAGE = {
  thumb_url: 'https://images.unsplash.com/p?ixid=a&w=360',
  hero_url: 'https://images.unsplash.com/p?ixid=a&w=960',
  author: 'Ana Cook',
  author_url: 'https://unsplash.com/@anacook?utm_source=sweep&utm_medium=referral',
  source: 'Unsplash',
  source_url: 'https://unsplash.com/?utm_source=sweep&utm_medium=referral',
};

test('the recipe page uses the large photo, everything else the small one', () => {
  expect(photoUrl(IMAGE, true)).toBe(IMAGE.hero_url);
  expect(photoUrl(IMAGE, false)).toBe(IMAGE.thumb_url);
});

test('no photo means the emoji art', () => {
  expect(photoUrl(null, true)).toBeNull();
  expect(photoUrl(undefined, false)).toBeNull();
});
