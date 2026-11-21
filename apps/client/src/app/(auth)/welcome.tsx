import { Image } from 'expo-image';
import { router } from 'expo-router';
import { ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '@/components/ui';
import { Rise } from '@/features/welcome/Rise';
import { LANDING } from '@/features/welcome/story';
import { hero } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

/**
 * The first thing a signed-out person sees: logo, the promise, Sweep's chef, and two ways
 * in. "Get started" tells the story first; people with an account go straight to sign-in.
 */
export default function WelcomeScreen() {
  const t = useTheme();
  return (
    <View style={{ flex: 1, backgroundColor: hero.background, backgroundImage: hero.glow }}>
      <SafeAreaView style={{ flex: 1 }}>
        <ScrollView
          contentContainerStyle={{
            flexGrow: 1,
            paddingHorizontal: t.space.xl,
            paddingVertical: t.space.lg,
            gap: t.space.lg,
            width: '100%',
            maxWidth: 560,
            alignSelf: 'center',
          }}
        >
          <Wordmark />

          <View style={{ gap: t.space.md, marginTop: t.space.md }}>
            <Rise delay={150}>
              <Text
                accessibilityRole="header"
                style={[
                  t.type.display,
                  { color: hero.text, fontSize: 40, lineHeight: 48, letterSpacing: -1 },
                ]}
              >
                {LANDING.title}
                {'\n'}
                <Text style={{ backgroundColor: hero.highlight, color: hero.onHighlight }}>
                  {LANDING.highlight}
                </Text>
              </Text>
            </Rise>
            <Rise delay={150} index={1}>
              <Text style={[t.type.body, { color: hero.textMuted, fontSize: 17, lineHeight: 25 }]}>
                {LANDING.lede}
              </Text>
            </Rise>
          </View>

          {/* The food strip has a gap in the middle; the chef stands in it. */}
          <Rise
            delay={150}
            index={2}
            style={{ flex: 1, justifyContent: 'flex-end', alignItems: 'center' }}
          >
            <View aria-hidden style={{ width: '88%', aspectRatio: 1400 / 466 }}>
              <Image
                source={require('../../../assets/images/welcome-food.webp')}
                style={{ position: 'absolute', inset: 0 }}
                contentFit="contain"
              />
              <Image
                source={require('../../../assets/images/chef-blink.webp')}
                style={{
                  position: 'absolute',
                  bottom: '6%',
                  alignSelf: 'center',
                  width: '46%',
                  aspectRatio: 1,
                }}
                contentFit="contain"
              />
            </View>
          </Rise>

          <Rise delay={150} index={3} style={{ gap: t.space.sm }}>
            <Button title="Get started" onPress={() => router.push('/how-it-works')} />
            <Button
              title="I already have an account"
              variant="secondary"
              onPress={() => router.push('/sign-in')}
            />
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
      <Image
        aria-hidden
        source={require('../../../assets/images/sweep-logo.png')}
        style={{ width: 36, height: 36 }}
        contentFit="contain"
      />
      <Text style={[t.type.heading, { color: hero.text, fontSize: 22, lineHeight: 28 }]}>
        Sweep
      </Text>
    </View>
  );
}
