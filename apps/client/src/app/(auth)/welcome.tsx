import { Image } from 'expo-image';
import { router, useIsFocused } from 'expo-router';
import { useCallback, useState } from 'react';
import { Text, useWindowDimensions, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '@/components/ui';
import { FitStage } from '@/features/welcome/FitStage';
import { HighlightLines } from '@/features/welcome/HighlightLines';
import { INTRO_MS, Intro } from '@/features/welcome/Intro';
import { WELCOME_SCENE_WIDTH, WelcomeScene } from '@/features/welcome/OnboardingMocks';
import { Rise } from '@/features/welcome/Rise';
import { LANDING, MAX_TEXT_SCALE } from '@/features/welcome/story';
import { hero } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

/**
 * The first thing a signed-out person sees (onboarding direction A, "Clean Slate"): logo,
 * tonight's idea with Sweep's chef, the promise, and two ways in. "Get started" tells the
 * story first; people with an account go straight to sign-in.
 */
// The brand intro plays once per app launch, not every time someone comes back here.
let introPlayed = false;

export default function WelcomeScreen() {
  const t = useTheme();
  const focused = useIsFocused(); // the picture only moves while this screen is showing
  // Short phones get smaller type so everything, buttons included, fits without scrolling.
  const short = useWindowDimensions().height < 700;
  const [intro, setIntro] = useState(!introPlayed);
  const endIntro = useCallback(() => {
    introPlayed = true;
    setIntro(false);
  }, []);
  // While the intro plays, the words wait to rise in until the logo zooms away.
  const delay = intro ? INTRO_MS - 450 : 150;
  const type = {
    color: hero.text,
    fontSize: short ? 26 : 30,
    lineHeight: short ? 31 : 35,
    letterSpacing: -0.8,
  };
  return (
    <View style={{ flex: 1, backgroundColor: t.colors.surface }}>
      <SafeAreaView style={{ flex: 1 }}>
        {/* No scrolling: the picture shrinks so everything else fits on screen. */}
        <View
          style={{
            flex: 1,
            paddingHorizontal: t.space.lg,
            paddingTop: t.space.sm,
            paddingBottom: short ? t.space.md : t.space.xl,
            gap: short ? t.space.md : t.space.lg,
            width: '100%',
            maxWidth: 520,
            alignSelf: 'center',
          }}
        >
          <Wordmark />

          <FitStage contentWidth={WELCOME_SCENE_WIDTH} minHeight={0}>
            <WelcomeScene active={focused && !intro} />
          </FitStage>

          <View style={{ gap: t.space.sm, paddingHorizontal: t.space.md }}>
            <Rise delay={delay}>
              {/* One heading for screen readers; the lime marker is drawn line by line. */}
              <View
                accessible
                accessibilityRole="header"
                accessibilityLabel={`${LANDING.title} ${LANDING.highlight}`}
              >
                <Text maxFontSizeMultiplier={MAX_TEXT_SCALE} style={[t.type.display, type]}>
                  {LANDING.title}
                </Text>
                <HighlightLines
                  maxFontSizeMultiplier={MAX_TEXT_SCALE}
                  style={[t.type.display, type]}
                >
                  {LANDING.highlight}
                </HighlightLines>
              </View>
            </Rise>
            <Rise delay={delay} index={1}>
              <Text
                maxFontSizeMultiplier={MAX_TEXT_SCALE}
                style={[
                  t.type.body,
                  {
                    color: t.colors.textMuted,
                    fontSize: 15,
                    lineHeight: short ? 21 : 22,
                  },
                ]}
              >
                {LANDING.lede}
              </Text>
            </Rise>
          </View>

          <Rise delay={delay} index={2} style={{ gap: t.space.md, paddingHorizontal: t.space.sm }}>
            <Button title="Get started" onPress={() => router.push('/how-it-works')} />
            <Button
              title="I already have an account"
              variant="secondary"
              onPress={() => router.push('/sign-in')}
            />
          </Rise>
        </View>
      </SafeAreaView>
      {intro ? <Intro onDone={endIntro} /> : null}
    </View>
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
      <Text
        maxFontSizeMultiplier={MAX_TEXT_SCALE}
        style={[t.type.heading, { color: hero.text, fontSize: 21, lineHeight: 28 }]}
      >
        Sweep
      </Text>
    </View>
  );
}
