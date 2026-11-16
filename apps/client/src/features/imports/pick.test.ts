import { checkPdf, checkPhotoCount, resizeFor } from './pick';

describe('resizeFor', () => {
  it.each([
    [4032, 3024, { width: 1600 }], // a phone photo, landscape: longest side to 1,600
    [3024, 4032, { height: 1600 }], // portrait
    [1200, 900, null], // already small enough: left as it is
    [1600, 1600, null],
  ])('%i×%i → %j', (width, height, expected) => {
    expect(resizeFor(width, height)).toEqual(expected);
  });
});

describe('checkPhotoCount', () => {
  it.each([0, 1, 3])('%i is fine', (n) => expect(checkPhotoCount(n)).toBeNull());
  it('more than 3 is refused with a reason', () => {
    expect(checkPhotoCount(4)).toBe('Up to 3 photos, one recipe. Pick the pages again.');
  });
});

describe('checkPdf', () => {
  it('a PDF up to 10 MB is fine', () => {
    expect(
      checkPdf({ name: 'ragu.pdf', mimeType: 'application/pdf', size: 10_000_000 }),
    ).toBeNull();
  });
  it('a bigger one is refused before uploading', () => {
    expect(checkPdf({ name: 'ragu.pdf', mimeType: 'application/pdf', size: 10_000_001 })).toBe(
      'That PDF is over 10 MB. Try a smaller copy, or paste the recipe text.',
    );
  });
  it('anything else is refused (the server checks the bytes too)', () => {
    expect(checkPdf({ name: 'ragu.docx', mimeType: 'application/msword', size: 100 })).toBe(
      'Sweep reads PDFs only. For a Word or text file, paste the recipe text.',
    );
  });
  it('a PDF with no type given is judged by its name', () => {
    expect(checkPdf({ name: 'RAGU.PDF', mimeType: undefined, size: 100 })).toBeNull();
  });
});
