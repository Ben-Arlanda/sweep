import type { TextStyle } from 'react-native';

/**
 * A text style for a one-line TextInput. iOS pushes typed text to the bottom of a custom
 * lineHeight instead of centring it, so it sits below the icon beside it. Inputs keep the
 * font and size but drop lineHeight and centre vertically.
 */
export function inputText(type: TextStyle): TextStyle {
  const { lineHeight: _lineHeight, ...rest } = type;
  return { ...rest, paddingVertical: 0, textAlignVertical: 'center' };
}
