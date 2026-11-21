import { useState } from 'react';
import { Platform, Text, View, type StyleProp, type TextStyle } from 'react-native';

import { useTheme } from '@/theme/useTheme';

/**
 * Words on a lime marker that hugs each line of text. A background on wrapped text fills
 * the first line to the edge on iOS, so on phones we measure where the lines break and
 * draw one lime box per line. Browsers already draw inline highlights line by line.
 */
export function HighlightLines({
  children,
  style,
  maxFontSizeMultiplier,
}: {
  children: string;
  style: StyleProp<TextStyle>;
  maxFontSizeMultiplier?: number;
}) {
  const t = useTheme();
  const [lines, setLines] = useState<string[] | null>(null);
  const marker = { backgroundColor: t.colors.action, color: t.colors.onAction };

  if (Platform.OS === 'web') {
    return (
      <Text style={style} maxFontSizeMultiplier={maxFontSizeMultiplier}>
        <Text style={marker}>{children}</Text>
      </Text>
    );
  }

  return (
    <View>
      {/* Invisible copy at full width, only to learn where the lines break. */}
      <Text
        aria-hidden
        maxFontSizeMultiplier={maxFontSizeMultiplier}
        style={[style, { position: 'absolute', left: 0, right: 0, opacity: 0 }]}
        onTextLayout={(e) => setLines(e.nativeEvent.lines.map((line) => line.text.trimEnd()))}
      >
        {children}
      </Text>
      {(lines ?? [children]).map((line, i) => (
        <View key={i} style={{ alignSelf: 'flex-start', opacity: lines ? 1 : 0 }}>
          <Text
            numberOfLines={1}
            maxFontSizeMultiplier={maxFontSizeMultiplier}
            style={[style, marker]}
          >
            {line}
          </Text>
        </View>
      ))}
    </View>
  );
}
