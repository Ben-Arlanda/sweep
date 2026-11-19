import { useEffect, useRef, type ReactNode } from 'react';
import { Modal, Platform, Pressable, ScrollView, View, type HostInstance } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Text } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

/**
 * A bottom sheet. On a phone the thumb is already at the bottom, so the choices are too.
 *
 * `Modal` makes it a real dialog: screen readers stay inside it, and on web it traps
 * focus and closes on Escape (`onRequestClose`). `label` names the dialog for screen
 * readers; `title` is the visible heading.
 */
export function Sheet({
  label,
  title,
  header,
  onClose,
  children,
}: {
  label: string;
  title: string;
  /** Replaces the plain title, e.g. a picture, name and close button. */
  header?: ReactNode;
  onClose: () => void;
  children: ReactNode;
}) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const sheet = useRef<HostInstance>(null);

  // On web, Modal draws its own role="dialog" element but gives it no name, and has no
  // prop for one (Lighthouse: aria-dialog-name). Name it from inside once it's on screen.
  useEffect(() => {
    if (Platform.OS !== 'web') return;
    const node = sheet.current as unknown as HTMLElement | null;
    // aria-modal, not role: Modal only adds role="dialog" after it has opened.
    node?.closest('[aria-modal]')?.setAttribute('aria-label', label);
  }, [label]);

  return (
    <Modal transparent animationType="slide" onRequestClose={onClose}>
      <View style={{ flex: 1, justifyContent: 'flex-end' }}>
        {/* The dimmed screen behind. Tapping it closes, like every sheet; it's hidden
            from screen readers, which use the sheet's own Done button instead. */}
        <Pressable
          onPress={onClose}
          accessible={false}
          focusable={false}
          aria-hidden
          style={{
            position: 'absolute',
            inset: 0,
            backgroundColor: 'rgba(18, 26, 46, 0.36)',
          }}
        />
        <View
          ref={sheet}
          accessibilityViewIsModal
          style={{
            maxHeight: '85%',
            backgroundColor: t.colors.sheet,
            borderTopLeftRadius: t.radius.xl,
            borderTopRightRadius: t.radius.xl,
            paddingTop: 10,
            paddingBottom: Math.max(insets.bottom, t.space.xxl),
            boxShadow: '0 -8px 32px -8px rgba(18, 26, 46, 0.25)',
          }}
        >
          {/* The grab handle: tells people this is a sheet. Decorative only. */}
          <View
            aria-hidden
            style={{
              alignSelf: 'center',
              width: 36,
              height: 5,
              borderRadius: 3,
              backgroundColor: t.colors.switchOff,
              opacity: 0.5,
              marginBottom: 14,
            }}
          />
          <ScrollView
            contentContainerStyle={{
              paddingHorizontal: t.space.lg,
              gap: 14,
            }}
            keyboardShouldPersistTaps="handled"
          >
            {header ?? (
              <Text
                accessibilityRole="header"
                style={{
                  fontFamily: t.fonts.display,
                  fontSize: 21,
                  lineHeight: 26,
                  letterSpacing: -0.2,
                  color: t.colors.text,
                }}
              >
                {title}
              </Text>
            )}
            {children}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}
