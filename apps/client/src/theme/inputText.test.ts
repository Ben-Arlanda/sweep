/// <reference types="jest" />
import { inputText } from './inputText';

test('keeps the font, drops lineHeight, centres the text', () => {
  expect(inputText({ fontFamily: 'Urbanist', fontSize: 16, lineHeight: 23 })).toEqual({
    fontFamily: 'Urbanist',
    fontSize: 16,
    paddingVertical: 0,
    textAlignVertical: 'center',
  });
});
