import { useEffect, useRef } from 'react';
import { Modal, Platform, View, type HostInstance } from 'react-native';

import { Button, Text } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

/**
 * "Are you sure?" in the app's own look. Not `Alert.alert`: on web that does nothing,
 * and its buttons can't be styled to show which choice loses work.
 *
 * Like the Sheet, `Modal` keeps screen readers inside it and closes on Escape / Back
 * (that counts as Cancel, the safe choice). Cancel comes first, so it's what a
 * screen reader reaches first too.
 */
export function ConfirmDialog({
  title,
  message,
  confirm,
  cancel = 'Cancel',
  onConfirm,
  onCancel,
  busy,
}: {
  title: string;
  message: string;
  confirm: string; // says what happens: "Discard changes", "Delete recipe"
  cancel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  busy?: boolean;
}) {
  const t = useTheme();
  const box = useRef<HostInstance>(null);

  // Same as the Sheet: give web's role="dialog" a name.
  useEffect(() => {
    if (Platform.OS !== 'web') return;
    const node = box.current as unknown as HTMLElement | null;
    node?.closest('[aria-modal]')?.setAttribute('aria-label', title);
  }, [title]);

  return (
    <Modal transparent animationType="fade" onRequestClose={onCancel}>
      <View
        style={{
          flex: 1,
          justifyContent: 'center',
          padding: t.space.lg,
          backgroundColor: 'rgba(0,0,0,0.55)',
        }}
      >
        <View
          ref={box}
          accessibilityViewIsModal
          style={{
            alignSelf: 'center',
            width: '100%',
            maxWidth: 420,
            gap: t.space.md,
            padding: t.space.lg,
            borderRadius: t.radius.xl,
            backgroundColor: t.colors.background,
          }}
        >
          <Text variant="heading" accessibilityRole="header">
            {title}
          </Text>
          <Text>{message}</Text>
          <View style={{ gap: t.space.sm }}>
            <Button title={cancel} variant="secondary" onPress={onCancel} />
            <Button title={confirm} variant="danger" loading={busy} onPress={onConfirm} />
          </View>
        </View>
      </View>
    </Modal>
  );
}
