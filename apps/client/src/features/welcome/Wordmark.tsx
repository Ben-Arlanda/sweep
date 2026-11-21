import { Image } from 'expo-image';
import { Text, View } from 'react-native';

import { useTheme } from '@/theme/useTheme';

import { MAX_TEXT_SCALE } from './story';

/** The brand mark on the signed-out screens: the navy S logo, then the name. */
export function Wordmark({ inset = true }: { inset?: boolean }) {
  const t = useTheme();
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.sm,
        paddingHorizontal: inset ? t.space.sm : 0,
      }}
    >
      <Image
        aria-hidden
        source={require('../../../assets/images/sweep-logo.png')}
        style={{ width: 34, height: 34 }}
        contentFit="contain"
      />
      <Text
        maxFontSizeMultiplier={MAX_TEXT_SCALE}
        style={[t.type.heading, { color: t.colors.text, fontSize: 21, lineHeight: 28 }]}
      >
        Sweep
      </Text>
    </View>
  );
}
