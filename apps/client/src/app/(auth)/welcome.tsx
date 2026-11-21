import { Image } from 'expo-image';
import { router } from 'expo-router';
import { Heart } from 'lucide-react-native';
import { useState } from 'react';
import { ScrollView, Text, useWindowDimensions, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Icon } from '@/components/Icon';
import { Button } from '@/components/ui';
import { Rise } from '@/features/welcome/Rise';
import { PHOTOS } from '@/features/welcome/photos';
import { LANDING } from '@/features/welcome/story';
import { hero } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

/**
 * The first thing a signed-out person sees: logo, the promise, Sweep's chef, and two ways
 * in. "Get started" tells the story first; people with an account go straight to sign-in.
 */
const SCENE_RATIO = 1.3; // width : height of the chef-and-card scene

export default function WelcomeScreen() {
  const t = useTheme();
  // Short phones get smaller type so everything, buttons included, fits without scrolling.
  const short = useWindowDimensions().height < 700;
  const [space, setSpace] = useState({ width: 0, height: 0 });
  const sceneWidth = Math.min(space.width, space.height * SCENE_RATIO);
  return (
    <View style={{ flex: 1, backgroundColor: hero.background, backgroundImage: hero.glow }}>
      <SafeAreaView style={{ flex: 1 }}>
        <ScrollView
          contentContainerStyle={{
            flexGrow: 1,
            paddingHorizontal: t.space.xl,
            paddingVertical: t.space.lg,
            gap: short ? t.space.md : t.space.lg,
            width: '100%',
            maxWidth: 560,
            alignSelf: 'center',
          }}
        >
          <Wordmark />

          <View style={{ gap: t.space.md, marginTop: short ? 0 : t.space.md }}>
            <Rise delay={150}>
              <Text
                accessibilityRole="header"
                style={[
                  t.type.display,
                  {
                    color: hero.text,
                    fontSize: short ? 34 : 40,
                    lineHeight: short ? 40 : 48,
                    letterSpacing: -1,
                  },
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
              <Text
                style={[
                  t.type.body,
                  { color: hero.textMuted, fontSize: short ? 16 : 17, lineHeight: short ? 23 : 25 },
                ]}
              >
                {LANDING.lede}
              </Text>
            </Rise>
          </View>

          <Rise
            delay={150}
            index={2}
            style={{ flex: 1, minHeight: 120, marginHorizontal: -t.space.xl }}
          >
            {/* Takes whatever height is left; the scene shrinks to fit it. */}
            <View
              style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}
              onLayout={(e) => setSpace(e.nativeEvent.layout)}
            >
              {sceneWidth > 0 && <ChefWithRecipe width={sceneWidth} />}
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

/** Sweep's chef beside a tilted recipe card, like the Recipes tab. Decorative. */
function ChefWithRecipe({ width }: { width: number }) {
  const t = useTheme();
  return (
    <View
      aria-hidden
      importantForAccessibility="no-hide-descendants"
      style={{ width, aspectRatio: SCENE_RATIO }}
    >
      <View
        style={{
          position: 'absolute',
          right: '5%',
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
          source={{ uri: PHOTOS.chanaMasala }}
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
          left: '6%',
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
