import { router } from 'expo-router';
import { useRef, useState } from 'react';
import {
  ScrollView,
  View,
  type NativeScrollEvent,
  type NativeSyntheticEvent,
  type ScrollViewInstance,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Tag } from '@/components/Pill';
import { Button, Text } from '@/components/ui';
import { StoryMock } from '@/features/welcome/StoryMocks';
import { STORY } from '@/features/welcome/story';
import { useTheme } from '@/theme/useTheme';

/**
 * "How Sweep works": four pages you swipe through (or tap Next), one per part of the
 * loop: shop, Cabinet, ask, plan. Skip is always there. The last page leads to sign-in.
 *
 * It's a sideways ScrollView with `pagingEnabled`, which snaps to whole pages. We work
 * out the current page from how far it has scrolled, so swiping and the Next button
 * always agree.
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
    setPage(index); // don't wait for the scroll event, so the button updates at once
  }

  const signIn = () => router.replace('/sign-in');

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.colors.background }}>
      <View
        style={{
          flexDirection: 'row',
          justifyContent: 'flex-end',
          paddingHorizontal: t.space.md,
          minHeight: t.touchTarget,
        }}
      >
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
                      padding: t.space.xl,
                      paddingTop: t.space.sm,
                      gap: t.space.xl,
                      width: '100%',
                      maxWidth: 520,
                      alignSelf: 'center',
                    }}
                  >
                    <View aria-hidden importantForAccessibility="no-hide-descendants">
                      {/* A new key when the page comes on screen replays its animation. */}
                      <StoryMock key={active ? 'on' : 'off'} story={story.key} active={active} />
                    </View>
                    <View style={{ gap: t.space.sm }}>
                      <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.sm }}>
                        <Text variant="label" muted>
                          {story.eyebrow}
                        </Text>
                        {story.upcoming ? <Tag tint="butter">Coming soon</Tag> : null}
                      </View>
                      <Text variant="title" accessibilityRole="header">
                        {story.title}
                      </Text>
                      <Text muted style={{ fontSize: 17, lineHeight: 24 }}>
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
          gap: t.space.lg,
          width: '100%',
          maxWidth: 520,
          alignSelf: 'center',
        }}
      >
        <Dots count={STORY.length} current={page} />
        {last ? (
          <Button title="Get started" onPress={signIn} />
        ) : (
          <Button title="Next" onPress={() => goTo(page + 1)} />
        )}
      </View>
    </SafeAreaView>
  );
}

function Dots({ count, current }: { count: number; current: number }) {
  const t = useTheme();
  return (
    <View
      // One image with a text label, so screen readers say "Page 2 of 4", not 4 dots.
      role="img"
      aria-label={`Page ${current + 1} of ${count}`}
      style={{ flexDirection: 'row', justifyContent: 'center', gap: 6 }}
    >
      {Array.from({ length: count }, (_, i) => (
        <View
          key={i}
          style={{
            width: i === current ? 22 : 8,
            height: 8,
            borderRadius: 4,
            backgroundColor: i === current ? t.colors.text : t.colors.border,
          }}
        />
      ))}
    </View>
  );
}
