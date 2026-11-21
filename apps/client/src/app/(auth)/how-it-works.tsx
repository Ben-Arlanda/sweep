import { router } from 'expo-router';
import { ArrowLeft } from 'lucide-react-native';
import { useRef, useState } from 'react';
import {
  ScrollView,
  Text,
  View,
  type NativeScrollEvent,
  type NativeSyntheticEvent,
  type ScrollViewInstance,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { Button } from '@/components/ui';
import { OnboardingMock } from '@/features/welcome/OnboardingMocks';
import { STORY } from '@/features/welcome/story';
import { hero } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

/**
 * "How Sweep works" (direction A, "Clean Slate"): one page per feature, each playing a
 * small live copy of the real screen, then "All in one" with the ways in. Swipe or tap
 * Next; Skip is always there.
 *
 * It's a sideways ScrollView with `pagingEnabled`, which snaps to whole pages. We work
 * out the current page from how far it has scrolled, so swiping and the buttons agree.
 */
export default function HowItWorksScreen() {
  const t = useTheme();
  const scroller = useRef<ScrollViewInstance>(null);
  const [width, setWidth] = useState(0);
  const [page, setPage] = useState(0);
  const last = page === STORY.length - 1;

  function onScroll(e: NativeSyntheticEvent<NativeScrollEvent>) {
    if (!width) return;
    const next = Math.round(e.nativeEvent.contentOffset.x / width);
    if (next !== page) setPage(Math.min(Math.max(next, 0), STORY.length - 1));
  }

  function goTo(index: number) {
    scroller.current?.scrollTo({ x: index * width, animated: true });
    setPage(index); // don't wait for the scroll event, so the buttons update at once
  }

  const back = () => (page === 0 ? router.back() : goTo(page - 1));
  const signIn = () => router.replace('/sign-in');

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.colors.surface }}>
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingHorizontal: t.space.md,
          minHeight: t.touchTarget + 8,
        }}
      >
        <PressableScale
          accessibilityRole="button"
          accessibilityLabel="Back"
          onPress={back}
          style={{
            width: t.touchTarget,
            height: t.touchTarget,
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Icon icon={ArrowLeft} size={22} color={t.colors.text} />
        </PressableScale>
        {last ? null : <Button title="Skip" variant="ghost" compact onPress={signIn} />}
      </View>

      <ScrollView
        ref={scroller}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onScroll={onScroll}
        scrollEventThrottle={16}
        onLayout={(e) => setWidth(e.nativeEvent.layout.width)}
        style={{ flex: 1 }}
      >
        {width
          ? STORY.map((story, i) => {
              const active = i === page;
              return (
                <View
                  key={story.key}
                  // Only the page on screen is read out; the others are off to the side.
                  aria-hidden={!active}
                  importantForAccessibility={active ? 'auto' : 'no-hide-descendants'}
                  style={{ width }}
                >
                  <ScrollView
                    contentContainerStyle={{
                      paddingHorizontal: t.space.lg,
                      paddingTop: t.space.xs,
                      gap: t.space.xl,
                      width: '100%',
                      maxWidth: 520,
                      alignSelf: 'center',
                    }}
                  >
                    <View
                      aria-hidden
                      importantForAccessibility="no-hide-descendants"
                      style={{
                        backgroundColor: t.colors.background,
                        borderRadius: 32,
                        padding: t.space.lg,
                        minHeight: 360,
                        justifyContent: 'center',
                      }}
                    >
                      <OnboardingMock story={story.key} active={active} />
                    </View>
                    <View style={{ gap: t.space.sm, paddingHorizontal: t.space.md }}>
                      <Text
                        accessibilityRole="header"
                        style={[
                          t.type.display,
                          {
                            color: t.colors.text,
                            fontSize: 32,
                            lineHeight: 37,
                            letterSpacing: -0.8,
                          },
                        ]}
                      >
                        {story.title}
                        {story.highlight ? (
                          <>
                            {'\n'}
                            <Text
                              style={{ backgroundColor: hero.highlight, color: hero.onHighlight }}
                            >
                              {story.highlight}
                            </Text>
                          </>
                        ) : null}
                      </Text>
                      <Text
                        style={[
                          t.type.body,
                          { color: t.colors.textMuted, fontSize: 16, lineHeight: 24 },
                        ]}
                      >
                        {story.body}
                      </Text>
                    </View>
                  </ScrollView>
                </View>
              );
            })
          : null}
      </ScrollView>

      <View
        style={{
          padding: t.space.xl,
          paddingTop: t.space.md,
          gap: t.space.md,
          width: '100%',
          maxWidth: 520,
          alignSelf: 'center',
        }}
      >
        {last ? (
          <>
            <Button title="Get started" onPress={signIn} />
            <Button title="I already have an account" variant="secondary" onPress={signIn} />
          </>
        ) : (
          <>
            <Bars count={STORY.length - 1} current={page} />
            <Button title="Next" onPress={() => goTo(page + 1)} />
          </>
        )}
      </View>
    </SafeAreaView>
  );
}

/** Progress through the feature pages: the current one is a longer ink bar. */
function Bars({ count, current }: { count: number; current: number }) {
  const t = useTheme();
  return (
    <View
      // One image with a text label, so screen readers say "Step 2 of 5", not 5 bars.
      role="img"
      aria-label={`Step ${current + 1} of ${count}`}
      style={{ flexDirection: 'row', justifyContent: 'center', gap: 6, paddingBottom: t.space.xs }}
    >
      {Array.from({ length: count }, (_, i) => (
        <View
          key={i}
          style={{
            width: i === current ? 32 : 18,
            height: 4,
            borderRadius: 2,
            backgroundColor: i === current ? t.colors.text : t.colors.border,
          }}
        />
      ))}
    </View>
  );
}
