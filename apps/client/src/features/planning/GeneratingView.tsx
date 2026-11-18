import { Check } from 'lucide-react-native';
import { ActivityIndicator, View } from 'react-native';

import { BouncingChef } from '@/components/BouncingChef';
import { Icon } from '@/components/Icon';
import { Button, Text } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

import type { Step } from './steps';

/**
 * The Generating screen (slice 6e): the bouncing chef, a heading and a checklist of what
 * Sweep is doing. The list is a polite live region, so screen readers hear each step.
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
    <View
      style={{
        flex: 1,
        alignItems: 'center',
        gap: t.space.lg,
        paddingHorizontal: t.space.xl,
        paddingTop: t.space.xxl,
        width: '100%',
        maxWidth: 480,
        alignSelf: 'center',
      }}
    >
      <BouncingChef />
      <Text variant="display" role="heading" aria-level={1} style={{ textAlign: 'center' }}>
        {title}
      </Text>
      <Text muted style={{ textAlign: 'center' }}>
        {subtitle}
      </Text>
      <View accessibilityLiveRegion="polite" style={{ alignSelf: 'stretch', gap: t.space.md }}>
        {steps.map((step) => (
          <View
            key={step.label}
            style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.md }}
            accessibilityLabel={`${step.label}: ${STATE_WORD[step.state]}`}
          >
            <StepMark state={step.state} />
            <Text variant="label" muted={step.state === 'waiting'}>
              {step.label}
            </Text>
          </View>
        ))}
      </View>
      {onCancel ? <Button title="Cancel" variant="ghost" compact onPress={onCancel} /> : null}
    </View>
  );
}

const STATE_WORD = { done: 'done', active: 'working on it', waiting: 'not started' } as const;

function StepMark({ state }: { state: Step['state'] }) {
  const t = useTheme();
  const box = { width: 26, height: 26, borderRadius: 13 } as const;
  if (state === 'done') {
    return (
      <View
        style={{
          ...box,
          backgroundColor: t.colors.action,
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Icon icon={Check} size={16} color={t.colors.onAction} strong />
      </View>
    );
  }
  if (state === 'active') {
    return (
      <View style={{ ...box, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator color={t.colors.text} aria-hidden />
      </View>
    );
  }
  return <View style={{ ...box, borderWidth: 2, borderColor: t.colors.border }} />;
}
