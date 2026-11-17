/// <reference types="jest" />
import { adaptedTitle, swapLine, swapsOf } from './adaptations';

describe('Recipe Adaptations', () => {
  it("names a proposed Adaptation the way it'll be saved", () => {
    // The server sends the parent's title and the label separately (ADR 0021).
    expect(adaptedTitle({ title: "Mum's ragu", adaptation: { label: 'with brown lentils' } })).toBe(
      "Mum's ragu · with brown lentils",
    );
    expect(adaptedTitle({ title: "Mum's ragu", adaptation: null })).toBe("Mum's ragu");
    expect(adaptedTitle({ title: "Mum's ragu" })).toBe("Mum's ragu");
  });

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
