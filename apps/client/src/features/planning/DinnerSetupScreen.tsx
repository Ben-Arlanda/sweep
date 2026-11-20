import { router } from 'expo-router';
import { Minus, Plus, Sparkles } from 'lucide-react-native';
import { useState } from 'react';
import { Pressable, ScrollView, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ChoiceChips } from '@/components/ChoiceChips';
import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { Button, Field, Text } from '@/components/ui';
import { usePreferences } from '@/lib/api/diet';
import { useTheme } from '@/theme/useTheme';

import { toParams, type Lean, type Mood } from './ideaRequest';

type Choice = Mood | 'lean';

const CHOICES: { value: Choice; title: string; hint: string }[] = [
  { value: 'surprise', title: 'Surprise me', hint: 'Good ideas from your Kitchen and tastes' },
  { value: 'kitchen', title: 'Use my Kitchen', hint: 'Fewest things to buy first' },
  { value: 'specific', title: 'Something specific', hint: 'e.g. chicken, pasta or a cuisine' },
  { value: 'lean', title: 'Healthy, quick or vegetarian', hint: 'Just for this search' },
];

const TIMES = [
  { label: 'Any time', value: null },
  { label: '20 min', value: 20 },
  { label: '30 min', value: 30 },
  { label: '45 min', value: 45 },
];

/**
 * The Recipes tab's way into Dinner Ideas (slice 6f): an optional mood, Ready in and
 * Serves, then the same ideas screen as Just tonight. Nothing here calls the AI except
 * "Healthy", which has no data to filter on and so asks Sweep.
 */
export function DinnerSetupScreen() {
  const t = useTheme();
  const household = usePreferences().data?.household_size ?? null;
  const [choice, setChoice] = useState<Choice>('surprise');
  const [words, setWords] = useState('');
  const [lean, setLean] = useState<Lean>('quick');
  const [maxMinutes, setMaxMinutes] = useState<number | null>(null);
  const [serves, setServes] = useState<number | null>(null);
  const people = serves ?? household ?? 4;
  const needsWords = choice === 'specific' && !words.trim();

  function find() {
    const params = toParams({
      mood: choice === 'lean' ? 'kitchen' : choice,
      q: choice === 'specific' ? words : '',
      lean: choice === 'lean' ? lean : null,
      maxMinutes,
      serves: people,
    });
    router.push({ pathname: '/tonight', params });
  }

  return (
    <SafeAreaView
      edges={['left', 'right', 'bottom']}
      style={{ flex: 1, backgroundColor: t.colors.background }}
    >
      <ScrollView
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={{
          padding: t.space.lg,
          gap: t.space.lg,
          width: '100%',
          maxWidth: 560,
          alignSelf: 'center',
        }}
      >
        <View
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            gap: t.space.md,
            backgroundColor: t.colors.actionSoft,
            borderRadius: t.radius.lg,
            padding: t.space.lg,
          }}
        >
          <Icon icon={Sparkles} color={t.colors.onActionSoft} />
          <Text
            variant="heading"
            role="heading"
            aria-level={1}
            style={{ flex: 1, color: t.colors.onActionSoft }}
          >
            What are you in the mood for?
          </Text>
        </View>

        <View
          accessibilityRole="radiogroup"
          accessibilityLabel="Mood"
          style={{
            backgroundColor: t.colors.surface,
            borderRadius: t.radius.lg,
            overflow: 'hidden',
            boxShadow: t.shadow.card,
          }}
        >
          {CHOICES.map((c, i) => {
            const on = c.value === choice;
            return (
              <Pressable
                key={c.value}
                accessibilityRole="radio"
                aria-checked={on}
                accessibilityState={{ checked: on }}
                onPress={() => setChoice(c.value)}
                style={{
                  flexDirection: 'row',
                  alignItems: 'center',
                  gap: t.space.md,
                  minHeight: 64,
                  paddingHorizontal: t.space.lg,
                  paddingVertical: t.space.md,
                  borderTopWidth: i === 0 ? 0 : 1,
                  borderTopColor: t.colors.border,
                  backgroundColor: t.colors.surface,
                }}
              >
                <View
                  style={{
                    width: 20,
                    height: 20,
                    borderRadius: 10,
                    borderWidth: on ? 6 : 1.5,
                    borderColor: on ? t.colors.selected : t.colors.switchOff,
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                ></View>
                <View style={{ flex: 1 }}>
                  <Text variant="label">{c.title}</Text>
                  <Text variant="caption" muted>
                    {c.hint}
                  </Text>
                </View>
              </Pressable>
            );
          })}
        </View>

        {choice === 'specific' ? (
          <Field
            label="What do you fancy?"
            placeholder="chicken, pasta, Thai…"
            value={words}
            onChangeText={setWords}
            maxLength={200}
            returnKeyType="search"
            onSubmitEditing={() => !needsWords && find()}
          />
        ) : null}
        {choice === 'lean' ? (
          <ChoiceChips
            label="Just for this search"
            value={lean}
            options={[
              {
                label: 'Healthy',
                value: 'healthy' as const,
                accessibilityLabel: 'Healthy (asks Sweep)',
              },
              {
                label: 'Quick',
                value: 'quick' as const,
                accessibilityLabel: 'Quick, under 30 minutes',
              },
              { label: 'Vegetarian', value: 'vegetarian' as const },
            ]}
            onChange={setLean}
          />
        ) : null}

        <View style={{ gap: t.space.sm }}>
          <Text variant="label" aria-hidden>
            Ready in
          </Text>
          <ChoiceChips
            label="Ready in"
            size="small"
            fill
            options={TIMES.map((o) => ({
              ...o,
              accessibilityLabel: o.value ? `Ready in ${o.label}` : o.label,
            }))}
            value={maxMinutes}
            onChange={setMaxMinutes}
          />
        </View>

        <View
          style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}
        >
          <Text variant="label" aria-hidden>
            Serves
          </Text>
          <View
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              borderRadius: t.radius.pill,
              borderWidth: 1,
              borderColor: t.colors.border,
              backgroundColor: t.colors.surface,
            }}
          >
            <Stepper
              icon={Minus}
              label="Fewer people"
              disabled={people <= 1}
              onPress={() => setServes(people - 1)}
            />
            <Text
              variant="label"
              accessibilityLiveRegion="polite"
              accessibilityLabel={`Serves ${people}`}
              style={{ minWidth: 28, textAlign: 'center' }}
            >
              {people}
            </Text>
            <Stepper
              icon={Plus}
              label="More people"
              disabled={people >= 24}
              onPress={() => setServes(people + 1)}
            />
          </View>
        </View>

        <Button title="Find dinner ideas" icon={Sparkles} disabled={needsWords} onPress={find} />
      </ScrollView>
    </SafeAreaView>
  );
}

function Stepper({
  icon,
  label,
  disabled,
  onPress,
}: {
  icon: typeof Plus;
  label: string;
  disabled: boolean;
  onPress: () => void;
}) {
  const t = useTheme();
  return (
    <PressableScale
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={onPress}
      style={{
        width: t.touchTarget,
        height: t.touchTarget,
        alignItems: 'center',
        justifyContent: 'center',
        opacity: disabled ? 0.4 : 1,
      }}
    >
      <Icon icon={icon} size={20} color={t.colors.text} />
    </PressableScale>
  );
}
