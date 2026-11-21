import { Image } from 'expo-image';
import { router, useIsFocused } from 'expo-router';
import { ScrollView, Text, useWindowDimensions, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '@/components/ui';
import { FitStage } from '@/features/welcome/FitStage';
import { WELCOME_SCENE_WIDTH, WelcomeScene } from '@/features/welcome/OnboardingMocks';
import { Rise } from '@/features/welcome/Rise';
import { LANDING } from '@/features/welcome/story';
import { hero } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

/**
 * The first thing a signed-out person sees (onboarding direction A, "Clean Slate"): logo,
 * tonight's idea with Sweep's chef, the promise, and two ways in. "Get started" tells the
 * story first; people with an account go straight to sign-in.
 */
export default function WelcomeScreen() {
  const t = useTheme();
  const focused = useIsFocused(); // the picture only moves while this screen is showing
  // Short phones get smaller type so everything, buttons included, fits without scrolling.
  const short = useWindowDimensions().height < 700;
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.colors.surface }}>
      <ScrollView
        contentContainerStyle={{
          flexGrow: 1,
          paddingHorizontal: t.space.lg,
          paddingTop: t.space.sm,
          paddingBottom: t.space.xl,
          gap: short ? t.space.md : t.space.xl,
          width: '100%',
          maxWidth: 520,
          alignSelf: 'center',
        }}
      >
        <Wordmark />

        <FitStage contentWidth={WELCOME_SCENE_WIDTH}>
          <WelcomeScene active={focused} />
        </FitStage>

        <View style={{ gap: t.space.sm, paddingHorizontal: t.space.md }}>
          <Rise delay={150}>
            <Text
              accessibilityRole="header"
              style={[
                t.type.display,
                {
                  color: hero.text,
                  fontSize: short ? 28 : 32,
                  lineHeight: short ? 33 : 37,
                  letterSpacing: -0.8,
                },
              ]}
            >
              {LANDING.title}{' '}
              <Text style={{ backgroundColor: hero.highlight, color: hero.onHighlight }}>
                {LANDING.highlight}
              </Text>
            </Text>
          </Rise>
          <Rise delay={150} index={1}>
            <Text
              style={[
                t.type.body,
                {
                  color: t.colors.textMuted,
                  fontSize: short ? 15 : 16,
                  lineHeight: short ? 22 : 24,
                },
              ]}
            >
              {LANDING.lede}
            </Text>
          </Rise>
        </View>

        <Rise delay={150} index={2} style={{ gap: t.space.md, paddingHorizontal: t.space.sm }}>
          <Button title="Get started" onPress={() => router.push('/how-it-works')} />
          <Button
            title="I already have an account"
            variant="secondary"
            onPress={() => router.push('/sign-in')}
          />
        </Rise>
      </ScrollView>
    </SafeAreaView>
  );
}

function Wordmark() {
  const t = useTheme();
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.sm,
        paddingHorizontal: t.space.sm,
      }}
    >
      <Image
        aria-hidden
        source={require('../../../assets/images/sweep-logo.png')}
        style={{ width: 34, height: 34 }}
        contentFit="contain"
      />
      <Text style={[t.type.heading, { color: hero.text, fontSize: 21, lineHeight: 28 }]}>
        Sweep
      </Text>
    </View>
  );
}
