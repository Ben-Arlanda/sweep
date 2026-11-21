import { router, Stack, useLocalSearchParams } from 'expo-router';
import {
  ArrowLeftRight,
  CalendarDays,
  ShoppingCart,
  CalendarCheck,
  ChevronRight,
  ShieldCheck,
  Sparkles,
} from 'lucide-react-native';
import { useState } from 'react';
import { ScrollView, View } from 'react-native';
import Animated, { ReduceMotion, ZoomIn } from 'react-native-reanimated';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { Button, Text } from '@/components/ui';
import { requestPlan } from '@/features/chat/starters';
import { PlanSheet } from '@/features/mealPlan/PlanSheet';
import { useTheme } from '@/theme/useTheme';

import type { LucideIcon } from 'lucide-react-native';

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`;

/**
 * After a plan is saved (slice 6e): "Dinner planned!" for one dinner, "Plan saved!"
 * for a week. Says what changed, then what you might do next.
 */
export function PlannedScreen() {
  const t = useTheme();
  const params = useLocalSearchParams<{
    kind?: string;
    title?: string;
    meals?: string;
    items?: string;
    /** Planned for another day ("Thu 20 Nov"), not tonight. */
    when?: string;
  }>();
  const week = params.kind === 'week';
  const meals = Number(params.meals ?? 0);
  const items = Number(params.items ?? 0);
  const [planning, setPlanning] = useState(false);

  return (
    <SafeAreaView
      edges={['left', 'right', 'bottom']}
      style={{ flex: 1, backgroundColor: t.colors.background }}
    >
      <Stack.Screen options={{ title: week ? 'Plan saved' : 'Dinner planned' }} />
      <ScrollView
        contentContainerStyle={{
          padding: t.space.lg,
          gap: t.space.md,
          width: '100%',
          maxWidth: 480,
          alignSelf: 'center',
        }}
      >
        <Animated.View
          entering={ZoomIn.springify().reduceMotion(ReduceMotion.System)}
          aria-hidden
          style={{
            alignSelf: 'center',
            width: 112,
            height: 112,
            borderRadius: 36,
            backgroundColor: t.colors.actionSoft,
            alignItems: 'center',
            justifyContent: 'center',
            marginTop: t.space.lg,
          }}
        >
          <Icon icon={CalendarCheck} size={56} color={t.colors.onActionSoft} />
        </Animated.View>
        <Text variant="display" role="heading" aria-level={1} style={{ textAlign: 'center' }}>
          {week ? 'Plan saved!' : 'Dinner planned!'}
        </Text>
        <Text style={{ textAlign: 'center' }} accessibilityLiveRegion="polite">
          {week
            ? `${plural(meals, 'dinner')} added to your week and ${plural(items, 'thing')} to your Shopping List.`
            : `${params.title ?? 'Dinner'} is set for ${params.when ?? 'tonight'}.`}
        </Text>

        <Button
          title={week || params.when ? 'View my week' : 'View tonight’s meal'}
          variant="dark"
          icon={CalendarDays}
          onPress={() =>
            week || params.when ? router.replace('/meal-plan') : router.dismissTo('/')
          }
        />
        <Button
          title="See Shopping List"
          icon={ShoppingCart}
          variant="secondary"
          onPress={() => router.replace('/lists')}
        />

        <Text variant="heading" role="heading" aria-level={2} style={{ marginTop: t.space.md }}>
          What&apos;s next?
        </Text>
        {week ? (
          <>
            <Next
              icon={ArrowLeftRight}
              title="Swap a meal"
              detail="Change any dinner"
              onPress={() => router.replace('/meal-plan')}
            />
            <Next
              icon={ShieldCheck}
              title="Dietary Rules"
              detail="What Sweep plans around"
              onPress={() => router.push('/dietary-rules')}
            />
            <Next
              icon={Sparkles}
              title="Ask Sweep"
              detail="“Make Thursday vegetarian”"
              onPress={() => router.push('/plan')}
            />
          </>
        ) : (
          <>
            <Next
              icon={ArrowLeftRight}
              title="Swap this meal"
              detail="Choose a different recipe"
              onPress={() => router.replace('/tonight')}
            />
            <Next
              icon={Sparkles}
              title="Plan the rest of the week"
              detail="Add more dinners"
              onPress={() => setPlanning(true)}
            />
          </>
        )}
      </ScrollView>
      {planning ? (
        <PlanSheet
          onClose={() => setPlanning(false)}
          onPick={(mode, days) => {
            requestPlan(mode, days);
            router.replace('/plan-week');
          }}
        />
      ) : null}
    </SafeAreaView>
  );
}

function Next({
  icon,
  title,
  detail,
  onPress,
}: {
  icon: LucideIcon;
  title: string;
  detail: string;
  onPress: () => void;
}) {
  const t = useTheme();
  return (
    <PressableScale
      accessibilityRole="button"
      accessibilityLabel={`${title}. ${detail}`}
      onPress={onPress}
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.md,
        minHeight: 64,
        paddingHorizontal: t.space.lg,
        backgroundColor: t.colors.surface,
        borderRadius: t.radius.md,
        boxShadow: t.shadow.card,
      }}
    >
      <Icon icon={icon} color={t.colors.text} />
      <View style={{ flex: 1 }}>
        <Text variant="label">{title}</Text>
        <Text variant="caption" muted>
          {detail}
        </Text>
      </View>
      <Icon icon={ChevronRight} color={t.colors.text} />
    </PressableScale>
  );
}
