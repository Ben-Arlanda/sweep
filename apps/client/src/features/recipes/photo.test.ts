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

test("a Member's own photo is served by the API, so its link gets the API's address", () => {
  const own = { thumb_url: '/recipe-photos/h/r/p/thumb.webp?expires=1&sig=a', hero_url: '/x' };
  expect(photoUrl(own, false, 'http://192.168.1.9:8000')).toBe(
    'http://192.168.1.9:8000/recipe-photos/h/r/p/thumb.webp?expires=1&sig=a',
  );
});

test('no photo means the food icon', () => {
  expect(photoUrl(null, true)).toBeNull();
  expect(photoUrl(undefined, false)).toBeNull();
});
