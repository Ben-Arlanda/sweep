import { Image } from 'expo-image';
import { router } from 'expo-router';
import { Heart } from 'lucide-react-native';
import { ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Icon } from '@/components/Icon';
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

          <Rise delay={150} index={2} style={{ flex: 1, justifyContent: 'center' }}>
            <ChefWithRecipe />
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

/** A real library photo (Beef pho), hotlinked like every recipe photo (ADR 0029). */
const PHO_PHOTO =
  'https://images.unsplash.com/photo-1582878826629-29b7ad1cdc43?ixid=M3wxMTM5MTAxfDB8MXxzZWFyY2h8Mnx8QmVlZiUyMHBoJUUxJUJCJTlGfGVufDF8MHx8fDE3OTUxNDI3MDd8MA&ixlib=rb-4.1.0&w=720&h=540&fit=crop&crop=entropy&fm=webp&q=55';

/** Sweep's chef beside a tilted recipe card, like the Recipes tab. Decorative. */
function ChefWithRecipe() {
  const t = useTheme();
  return (
    <View
      aria-hidden
      importantForAccessibility="no-hide-descendants"
      style={{ width: '100%', aspectRatio: 1.45 }}
    >
      <View
        style={{
          position: 'absolute',
          right: 0,
          top: '6%',
          width: '58%',
          padding: 8,
          borderRadius: t.radius.xl,
          backgroundColor: t.colors.surface,
          borderWidth: 1,
          borderColor: t.colors.border,
          transform: [{ rotate: '5deg' }],
          boxShadow: '0 12px 28px rgba(18, 26, 46, 0.12)',
        }}
      >
        <Image
          source={{ uri: PHO_PHOTO }}
          style={{ width: '100%', aspectRatio: 4 / 3, borderRadius: t.radius.lg }}
          contentFit="cover"
          transition={200}
        />
        <View
          style={{
            position: 'absolute',
            top: 16,
            right: 16,
            width: 32,
            height: 32,
            borderRadius: 16,
            backgroundColor: t.colors.surface,
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Icon icon={Heart} size={17} color={t.colors.text} />
        </View>
      </View>

      <Image
        source={require('../../../assets/images/welcome-chef.webp')}
        style={{
          position: 'absolute',
          left: '4%',
          bottom: '2%',
          width: '55%',
          aspectRatio: 640 / 622,
        }}
        contentFit="contain"
      />

      {/* Three little lime "ta-da" lines over the chef's hat. */}
      {[
        { left: '6%', top: '22%', rotate: '-40deg' },
        { left: '12%', top: '12%', rotate: '-15deg' },
        { left: '20%', top: '8%', rotate: '10deg' },
      ].map((s, i) => (
        <View
          key={i}
          style={{
            position: 'absolute',
            left: s.left as `${number}%`,
            top: s.top as `${number}%`,
            width: 6,
            height: 20,
            borderRadius: 3,
            backgroundColor: hero.highlight,
            transform: [{ rotate: s.rotate }],
          }}
        />
      ))}
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
