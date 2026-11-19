import { useKeepAwake } from 'expo-keep-awake';
import { ArrowLeft, ArrowRight, X } from 'lucide-react-native';
import { useEffect, useRef, useState } from 'react';
import { Modal, Platform, View, type HostInstance } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { Button, Text } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

import type { CookStep } from './method';

/**
 * Cook Mode (ADR 0028): the whole screen, one step at a time in big text, for reading
 * from across the bench. The screen stays awake while it's open. Escape / Back closes.
 */
export function CookMode({
  title,
  steps,
  onClose,
}: {
  title: string;
  steps: CookStep[];
  onClose: () => void;
}) {
  useKeepAwake(); // mounted only while open, so the screen sleeps again after
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const [at, setAt] = useState(0);
  const box = useRef<HostInstance>(null);
  const step = steps[at];
  const last = at === steps.length - 1;

  // Give web's role="dialog" a name, as the Sheet does.
  useEffect(() => {
    if (Platform.OS !== 'web') return;
    const node = box.current as unknown as HTMLElement | null;
    node?.closest('[aria-modal]')?.setAttribute('aria-label', `Cook Mode: ${title}`);
  }, [title]);

  if (!step) return null;
  return (
    <Modal animationType="slide" onRequestClose={onClose}>
      <View
        ref={box}
        accessibilityViewIsModal
        style={{
          flex: 1,
          backgroundColor: t.colors.surface,
          paddingTop: insets.top + t.space.sm,
          paddingBottom: insets.bottom + t.space.lg,
          paddingHorizontal: Math.max(insets.left, insets.right, t.space.lg),
          gap: t.space.lg,
        }}
      >
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.md }}>
          <View style={{ flex: 1, gap: 2 }}>
            <Text variant="caption" muted numberOfLines={1}>
              {title}
            </Text>
            <Text variant="label" style={{ fontVariant: ['tabular-nums'] }}>
              Step {at + 1} of {steps.length}
            </Text>
          </View>
          <PressableScale
            accessibilityRole="button"
            accessibilityLabel="Close Cook Mode"
            onPress={onClose}
            style={{
              width: t.touchTarget,
              height: t.touchTarget,
              borderRadius: t.touchTarget / 2,
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: t.colors.fill,
            }}
          >
            <Icon icon={X} color={t.colors.text} strong />
          </PressableScale>
        </View>

        <View
          role="progressbar"
          aria-label="Progress"
          aria-valuemin={1}
          aria-valuemax={steps.length}
          aria-valuenow={at + 1}
          style={{ height: 6, borderRadius: 3, backgroundColor: t.colors.fill }}
        >
          <View
            style={{
              width: `${((at + 1) / steps.length) * 100}%`,
              height: 6,
              borderRadius: 3,
              backgroundColor: t.colors.selected,
            }}
          />
        </View>

        <View accessibilityLiveRegion="polite" style={{ flex: 1, gap: t.space.md }}>
          {step.stage ? (
            <Text variant="heading" accessibilityRole="header">
              {step.stage}
            </Text>
          ) : null}
          <Text style={{ fontSize: 26, lineHeight: 38 }}>{step.text}</Text>
        </View>

        <View style={{ flexDirection: 'row', gap: t.space.sm }}>
          <View style={{ flex: 1 }}>
            <Button
              title="Back"
              icon={ArrowLeft}
              variant="secondary"
              disabled={at === 0}
              onPress={() => setAt(at - 1)}
            />
          </View>
          <View style={{ flex: 1 }}>
            <Button
              title={last ? 'Done' : 'Next'}
              icon={last ? undefined : ArrowRight}
              onPress={() => (last ? onClose() : setAt(at + 1))}
            />
          </View>
        </View>
      </View>
    </Modal>
  );
}
