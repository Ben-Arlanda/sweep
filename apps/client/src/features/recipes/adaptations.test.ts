/// <reference types="jest" />
import { swapLine, swapsOf } from './adaptations';

describe('Recipe Adaptations', () => {
  it('reads a Swap as plain words, new line first', () => {
    expect(swapLine({ replaces: '500 g beef mince', raw_text: '400 g brown lentils' })).toBe(
      '400 g brown lentils instead of 500 g beef mince',
    );
  });

  it("finds the Swaps in an Adaptation's lines, in recipe order", () => {
    const lines = [
      { raw_text: '1 onion', replaces: null },
      { raw_text: '400 g brown lentils', replaces: '500 g beef mince' },
      { raw_text: '2 tbsp olive oil' }, // older responses leave `replaces` out
      { raw_text: '1 cup veg stock', replaces: '1 cup beef stock' },
    ];
    expect(swapsOf(lines)).toEqual([
      { replaces: '500 g beef mince', raw_text: '400 g brown lentils' },
      { replaces: '1 cup beef stock', raw_text: '1 cup veg stock' },
    ]);
    expect(swapsOf([{ raw_text: '1 onion', replaces: null }])).toEqual([]);
  });
});
