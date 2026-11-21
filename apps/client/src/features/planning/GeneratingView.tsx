import { Check } from 'lucide-react-native';
import { View } from 'react-native';

import { BouncingChef } from '@/components/BouncingChef';
import { Icon } from '@/components/Icon';
import { Button, Text } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

import type { Step } from './steps';

/**
 * The Generating card (slice 6e, premium redesign): the bouncing chef, a heading, and a checklist
 * of what Sweep is doing. The list is a polite live region, so screen readers hear each
 * step.
 */
export function GeneratingView({
  title,
  subtitle,
  steps,
  onCancel,
}: {
  title: string;
  subtitle: string;
  steps: Step[];
  onCancel?: () => void;
}) {
  const t = useTheme();
  return (
    <View style={{ padding: t.space.lg, width: '100%', maxWidth: 560, alignSelf: 'center' }}>
      <View
        style={{
          gap: t.space.lg,
          padding: t.space.xl,
          borderRadius: t.radius.lg,
          backgroundColor: t.colors.surface,
          boxShadow: t.shadow.card,
        }}
      >
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.md }}>
          <BouncingChef size={64} />
          <View style={{ flex: 1, gap: 2 }}>
            <Text variant="heading" role="heading" aria-level={1}>
              {title}
            </Text>
            <Text variant="caption" muted>
              {subtitle}
            </Text>
          </View>
        </View>
        <View accessibilityLiveRegion="polite" style={{ gap: 14 }}>
          {steps.map((step) => (
            <View
              key={step.label}
              style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}
              accessibilityLabel={`${step.label}: ${STATE_WORD[step.state]}`}
            >
              <StepMark state={step.state} />
              <Text
                style={{
                  fontSize: 15,
                  lineHeight: 22,
                  fontFamily: step.state === 'active' ? t.fonts.medium : t.fonts.body,
                  color: step.state === 'active' ? t.colors.text : t.colors.textMuted,
                }}
              >
                {step.label}
              </Text>
            </View>
          ))}
        </View>
        {onCancel ? <Button title="Cancel" variant="ghost" compact onPress={onCancel} /> : null}
      </View>
    </View>
  );
}

const STATE_WORD = { done: 'done', active: 'working on it', waiting: 'not started' } as const;

/** Done: a tick. Working: a lime dot in a soft ring (Sweep's AI). Waiting: an empty ring. */
function StepMark({ state }: { state: Step['state'] }) {
  const t = useTheme();
  const box = { width: 16, height: 16, alignItems: 'center', justifyContent: 'center' } as const;
  if (state === 'done') {
    return (
      <View style={box}>
        <Icon icon={Check} size={16} color={t.colors.textMuted} strong />
      </View>
    );
  }
  if (state === 'active') {
    return (
      <View style={box}>
        <View
          style={{
            width: 8,
            height: 8,
            borderRadius: 4,
            backgroundColor: '#9cb51b',
            boxShadow: `0 0 0 4px ${t.colors.actionSoft}`,
          }}
        />
      </View>
    );
  }
  return (
    <View style={box}>
      <View
        style={{
          width: 8,
          height: 8,
          borderRadius: 4,
          borderWidth: 1.5,
          borderColor: t.colors.switchOff,
        }}
      />
    </View>
  );
}
