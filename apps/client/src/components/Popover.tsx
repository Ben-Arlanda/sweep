import { useEffect, useRef, useState, type ReactNode, type RefObject } from 'react';
import {
  Modal,
  Platform,
  Pressable,
  useWindowDimensions,
  View,
  type HostInstance,
} from 'react-native';

import { useTheme } from '@/theme/useTheme';

export type Anchor = { x: number; y: number; width: number; height: number };

/** Where a button is on screen, so a popover can open under it. */
export function measureAnchor(ref: RefObject<HostInstance | null>): Promise<Anchor> {
  return new Promise((resolve) => {
    if (!ref.current) return resolve({ x: 0, y: 0, width: 0, height: 0 });
    ref.current.measureInWindow((x, y, width, height) => resolve({ x, y, width, height }));
  });
}

/**
 * A small card that opens under the button that opened it, with a pointer to it.
 *
 * It's a `Modal` (like Sheet): it sits above everything on every platform, keeps screen
 * readers inside it, and closes on Escape or a tap outside. Near the bottom of the
 * screen it opens above the button instead.
 */
export function Popover({
  anchor,
  label,
  width = 264,
  onClose,
  children,
}: {
  anchor: Anchor;
  label: string;
  width?: number;
  onClose: () => void;
  children: ReactNode;
}) {
  const t = useTheme();
  const screen = useWindowDimensions();
  const card = useRef<HostInstance>(null);
  const [height, setHeight] = useState(0);

  useEffect(() => {
    if (Platform.OS !== 'web') return;
    const node = card.current as unknown as HTMLElement | null;
    node?.closest('[aria-modal]')?.setAttribute('aria-label', label);
  }, [label]);

  const gap = 10;
  const edge = t.space.md;
  const w = Math.min(width, screen.width - edge * 2);
  const anchorMid = anchor.x + anchor.width / 2;
  const left = Math.max(edge, Math.min(anchorMid - w + 48, screen.width - w - edge));
  const below = anchor.y + anchor.height + gap;
  const flip = height > 0 && below + height > screen.height - edge;
  const top = flip ? anchor.y - gap - height : below;
  const arrowLeft = Math.max(16, Math.min(anchorMid - left - 8, w - 32));

  return (
    <Modal transparent animationType="fade" onRequestClose={onClose}>
      <Pressable
        onPress={onClose}
        accessible={false}
        focusable={false}
        aria-hidden
        style={{ position: 'absolute', inset: 0, backgroundColor: 'rgba(0,0,0,0.08)' }}
      />
      <View
        ref={card}
        accessibilityViewIsModal
        onLayout={(e) => setHeight(e.nativeEvent.layout.height)}
        style={{
          position: 'absolute',
          top,
          left,
          width: w,
          opacity: height ? 1 : 0, // measured first, so it never flashes in the wrong spot
          backgroundColor: t.colors.surface,
          borderRadius: t.radius.lg,
          padding: t.space.md,
          gap: t.space.sm,
          boxShadow: t.shadow.raised,
          borderWidth: t.scheme === 'dark' ? 1 : 0,
          borderColor: t.colors.border,
        }}
      >
        <View
          aria-hidden
          style={{
            position: 'absolute',
            left: arrowLeft,
            [flip ? 'bottom' : 'top']: -7,
            width: 16,
            height: 16,
            borderRadius: 3,
            backgroundColor: t.colors.surface,
            transform: [{ rotate: '45deg' }],
          }}
        />
        {children}
      </View>
    </Modal>
  );
}
