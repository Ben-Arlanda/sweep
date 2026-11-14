import { router } from 'expo-router';
import { ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { PressableScale } from '@/components/PressableScale';
import { DriftingCards } from '@/features/welcome/DriftingCards';
import { Rise } from '@/features/welcome/Rise';
import { LANDING } from '@/features/welcome/story';
import { hero } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

/**
 * The first thing a signed-out person sees: the brand at full volume (ink, lime glow,
 * drifting cards) and two ways in. "Get started" tells the story first; people who
 * already have an account go straight to sign-in.
 */
export default function WelcomeScreen() {
  const t = useTheme();
  return (
    <View
      style={{
        flex: 1,
        backgroundColor: hero.background,
        backgroundImage: hero.glow,
      }}
    >
      <SafeAreaView style={{ flex: 1 }}>
        <ScrollView
          contentContainerStyle={{
            flexGrow: 1,
            padding: t.space.xl,
            gap: t.space.xl,
            width: '100%',
            maxWidth: 560,
            alignSelf: 'center',
          }}
        >
          <Wordmark />
          <View style={{ flex: 1, justifyContent: 'center' }}>
            <DriftingCards />
          </View>

          <View style={{ gap: t.space.md }}>
            <Rise delay={300}>
              <Text
                accessibilityRole="header"
                style={[t.type.display, { color: hero.text, fontSize: 40, lineHeight: 44 }]}
              >
                {LANDING.title}{' '}
                <Text style={{ backgroundColor: hero.highlight, color: hero.onHighlight }}>
                  {LANDING.highlight}
                </Text>
              </Text>
            </Rise>
            <Rise delay={300} index={1}>
              <Text style={[t.type.body, { color: hero.textMuted, fontSize: 17, lineHeight: 24 }]}>
                {LANDING.lede}
              </Text>
            </Rise>
          </View>

          <Rise delay={300} index={2} style={{ gap: t.space.sm }}>
            <HeroButton title="Get started" primary onPress={() => router.push('/how-it-works')} />
            <HeroButton title="I already have an account" onPress={() => router.push('/sign-in')} />
          </Rise>
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

function Wordmark() {
  const t = useTheme();
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.sm }}>
      <View
        aria-hidden
        style={{ width: 14, height: 14, borderRadius: 7, backgroundColor: hero.highlight }}
      />
      <Text style={[t.type.heading, { color: hero.text }]}>Sweep</Text>
    </View>
  );
}

/** The ui Button is themed for light and dark screens; this one is for the ink hero. */
function HeroButton({
  title,
  onPress,
  primary,
}: {
  title: string;
  onPress: () => void;
  primary?: boolean;
}) {
  const t = useTheme();
  return (
    <PressableScale
      accessibilityRole="button"
      onPress={onPress}
      style={{
        minHeight: t.touchTarget + 8,
        borderRadius: t.radius.pill,
        alignItems: 'center',
        justifyContent: 'center',
        paddingHorizontal: t.space.xl,
        backgroundColor: primary ? hero.highlight : 'transparent',
        borderWidth: primary ? 0 : 1.5,
        borderColor: hero.border,
      }}
    >
      <Text
        style={[
          t.type.label,
          {
            fontFamily: t.fonts.displayBold,
            fontSize: 17,
            color: primary ? hero.onHighlight : hero.text,
          },
        ]}
      >
        {title}
      </Text>
    </PressableScale>
  );
}
