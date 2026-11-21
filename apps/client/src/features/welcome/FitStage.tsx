import { useState, type ReactNode } from 'react';
import { View } from 'react-native';

import { useTheme } from '@/theme/useTheme';

/**
 * The grey panel holding an onboarding picture. It takes whatever height the page has
 * left and shrinks the picture to fit, so the words and buttons below never need a
 * scroll, on any phone. Decorative: screen readers skip it.
 */
export function FitStage({
  children,
  minHeight = 160,
  contentWidth,
}: {
  children: ReactNode;
  minHeight?: number;
  /** A picture drawn at a fixed width (its pieces placed by hand) also shrinks to fit across. */
  contentWidth?: number;
}) {
  const t = useTheme();
  const [room, setRoom] = useState({ width: 0, height: 0 }); // what the page leaves for the panel
  const [natural, setNatural] = useState(0); // the picture's own height with padding, unscaled
  const pad = t.space.lg;
  const across = contentWidth && room.width ? (room.width - pad * 2) / contentWidth : 1;
  const scale = room.height && natural ? Math.min(1, room.height / natural, across) : 1;

  return (
    <View
      aria-hidden
      importantForAccessibility="no-hide-descendants"
      style={{ flex: 1, minHeight, justifyContent: 'center' }}
      onLayout={(e) => setRoom(e.nativeEvent.layout)}
    >
      <View
        style={{
          height: natural ? natural * scale : undefined,
          backgroundColor: t.colors.background,
          borderRadius: 32,
          overflow: 'hidden',
          opacity: natural ? 1 : 0, // hidden for the one frame before it's measured
        }}
      >
        <View
          onLayout={(e) => setNatural(e.nativeEvent.layout.height)}
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: 0,
            padding: pad,
            alignItems: 'center',
            transform: [{ scale }],
            transformOrigin: 'top center',
          }}
        >
          <View style={{ width: contentWidth ?? '100%' }}>{children}</View>
        </View>
      </View>
    </View>
  );
}
