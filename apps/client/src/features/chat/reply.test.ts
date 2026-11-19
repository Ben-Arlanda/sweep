/// <reference types="jest" />
import { replyBlocks } from './reply';

test('numbered options become list items with bold titles', () => {
  const blocks = replyBlocks(
    'Quick ones:\n\n1. **Chicken fajitas**: 30 min · needs 6 things\n2. **Pad thai**: 25 min',
  );

  expect(blocks).toEqual([
    { kind: 'text', spans: [{ text: 'Quick ones:', bold: false }] },
    {
      kind: 'item',
      marker: '1',
      spans: [
        { text: 'Chicken fajitas', bold: true },
        { text: ': 30 min · needs 6 things', bold: false },
      ],
    },
    {
      kind: 'item',
      marker: '2',
      spans: [
        { text: 'Pad thai', bold: true },
        { text: ': 25 min', bold: false },
      ],
    },
  ]);
});

test('dash bullets become bullet items', () => {
  expect(replyBlocks('- eggs')).toEqual([
    { kind: 'item', marker: '•', spans: [{ text: 'eggs', bold: false }] },
  ]);
});

test('an unclosed ** is shown as typed', () => {
  expect(replyBlocks('2 ** 3')).toEqual([
    { kind: 'text', spans: [{ text: '2 ** 3', bold: false }] },
  ]);
});

test('links and images stay plain text (slice 10: nothing in a reply loads or opens)', () => {
  const text = 'See ![x](https://evil.example/?d=1) and [here](https://evil.example)';
  expect(replyBlocks(text)).toEqual([{ kind: 'text', spans: [{ text, bold: false }] }]);
});
