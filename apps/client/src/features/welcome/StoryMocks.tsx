/**
 * Small pictures of the app for the "how it works" pages, built from the real components
 * (FoodThumb, Pill, StatusBadge, Avatar) so they always look like the real screens.
 *
 * They're illustrations: screen readers skip them (see StoryPager), because each page's
 * heading and text already say what the picture shows.
 */
import { useEffect, useState, type ReactNode } from 'react';
import { View } from 'react-native';
import Animated, { FadeInDown, ReduceMotion } from 'react-native-reanimated';

import { Avatar } from '@/components/Avatar';
import { Checkbox } from '@/components/Checkbox';
import { FoodThumb } from '@/components/FoodThumb';
import { Pill, StatusBadge, Tag } from '@/components/Pill';
import { Text } from '@/components/ui';
import type { StatusName, TintName } from '@/theme/tokens';
import { tintFor } from '@/theme/tint';
import { useTheme } from '@/theme/useTheme';

import { Rise } from './Rise';
import type { StoryKey } from './story';

const ALICE = { id: 'alice', name: 'Alice' };
const BOB = { id: 'bob', name: 'Bob' };

export function StoryMock({ story, active }: { story: StoryKey; active: boolean }) {
  switch (story) {
    case 'shop':
      return <ShopMock active={active} />;
    case 'cabinet':
      return <CabinetMock />;
    case 'ask':
      return <AskMock />;
    case 'plan':
      return <PlanMock />;
  }
}

function Panel({ tint, title, caption, children }: {
  tint: TintName;
  title: string;
  caption: string;
  children: ReactNode;
}) {
  const t = useTheme();
  const c = t.tints[tint];
  return (
    <View style={{ backgroundColor: c.bg, borderRadius: t.radius.xl, padding: t.space.md, gap: t.space.sm }}>
      <View style={{ paddingHorizontal: t.space.xs, paddingTop: t.space.xs }}>
        <Text variant="heading" style={{ color: c.text }}>
          {title}
        </Text>
        <Text variant="caption" style={{ color: c.text }}>
          {caption}
        </Text>
      </View>
      {children}
    </View>
  );
}

function Row({ children }: { children: ReactNode }) {
  const t = useTheme();
  return (
    <View
      style={{
        backgroundColor: t.colors.surface,
        borderRadius: t.radius.md,
        padding: t.space.sm,
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.sm,
      }}
    >
      {children}
    </View>
  );
}

function Name({ name, caption, done }: { name: string; caption?: ReactNode; done?: boolean }) {
  return (
    <View style={{ flex: 1, minWidth: 0 }}>
      <Text
        variant="label"
        numberOfLines={1}
        muted={done}
        style={done ? { textDecorationLine: 'line-through' } : undefined}
      >
        {name}
      </Text>
      {caption ? (
        <Text variant="caption" muted numberOfLines={1}>
          {caption}
        </Text>
      ) : null}
    </View>
  );
}

/** Bob ticks the chicken a moment after the page appears, and it goes to the Cabinet. */
function ShopMock({ active }: { active: boolean }) {
  const t = useTheme();
  const [ticked, setTicked] = useState(false);

  useEffect(() => {
    if (!active) return; // the pager remounts this (new key) each time it comes on screen
    const timer = setTimeout(() => setTicked(true), 1200);
    return () => clearTimeout(timer);
  }, [active]);

  const items = [
    { emoji: '🍗', name: 'Chicken thighs', why: 'For Mon traybake', qty: '1.5 kg', tint: 'blush', by: ALICE },
    { emoji: '🌿', name: 'Coriander', why: 'Tue tacos', qty: '1 bunch', tint: 'mint', by: BOB },
    { emoji: '🥣', name: 'Greek yoghurt', why: 'Thu curry', qty: '500 g', tint: 'sky', by: ALICE },
  ] as const;

  return (
    <View style={{ gap: t.space.md }}>
      <Panel tint="butter" title="Weekly shop" caption="4 to buy · from this week's plan">
        {items.map((item, i) => {
          const done = ticked && i === 0;
          return (
            <Rise key={item.name} index={i}>
              <Row>
                <FoodThumb emoji={item.emoji} tint={item.tint} size={36} />
                <Name
                  name={item.name}
                  done={done}
                  caption={
                    <>
                      {item.by.name} · {item.why}
                    </>
                  }
                />
                {done ? (
                  <Animated.View entering={FadeInDown.springify().reduceMotion(ReduceMotion.System)}>
                    <Tag tint={tintFor(BOB.id)}>Bob ✓</Tag>
                  </Animated.View>
                ) : (
                  <Pill tint={item.tint}>{item.qty}</Pill>
                )}
                <Checkbox checked={done} size={24} />
              </Row>
            </Rise>
          );
        })}
      </Panel>
      <View style={{ minHeight: 40 }}>
        {ticked ? (
          <Animated.View
            entering={FadeInDown.springify().damping(14).reduceMotion(ReduceMotion.System)}
            style={{
              alignSelf: 'center',
              backgroundColor: t.colors.inverse,
              borderRadius: t.radius.pill,
              paddingHorizontal: t.space.lg,
              paddingVertical: t.space.sm,
            }}
          >
            <Text variant="label" style={{ color: t.colors.onInverse }}>
              Chicken thighs added to the Cabinet
            </Text>
          </Animated.View>
        ) : null}
      </View>
    </View>
  );
}

function CabinetMock() {
  const items: { emoji: string; name: string; note: string; tint: TintName; status: StatusName }[] = [
    { emoji: '🍗', name: 'Chicken thighs', note: 'Just bought · 1.5 kg', tint: 'blush', status: 'confirmed' },
    { emoji: '🍋', name: 'Lemons', note: '4 · 9 days ago', tint: 'butter', status: 'estimated' },
    { emoji: '🧄', name: 'Garlic', note: 'Not seen for 3 weeks', tint: 'lilac', status: 'unknown' },
    { emoji: '🧂', name: 'Salt', note: 'Staple', tint: 'sky', status: 'runOut' },
  ];
  return (
    <Panel tint="mint" title="Cabinet" caption="12 tracked · 2 to check">
      {items.map((item, i) => (
        <Rise key={item.name} index={i}>
          <Row>
            <FoodThumb emoji={item.emoji} tint={item.tint} size={36} />
            <Name name={item.name} caption={item.note} />
            <StatusBadge status={item.status} />
          </Row>
        </Rise>
      ))}
    </Panel>
  );
}

function AskMock() {
  const t = useTheme();
  const ideas: { emoji: string; title: string; meta: string; tint: TintName; have: string; need?: string }[] = [
    { emoji: '🍋', title: 'Lemon herb chicken traybake', meta: '35 min · serves 4', tint: 'blush', have: '5 of 6 in Cabinet', need: 'Need: yoghurt' },
    { emoji: '🌮', title: 'Chicken & coriander tacos', meta: '25 min · serves 4', tint: 'mint', have: 'All in Cabinet' },
    { emoji: '🍛', title: 'Quick chicken curry', meta: '40 min · serves 4', tint: 'butter', have: '4 of 7', need: 'Need 3' },
  ];
  return (
    <View style={{ gap: t.space.sm }}>
      <Rise style={{ alignSelf: 'flex-end', maxWidth: '85%' }}>
        <View style={{ backgroundColor: t.colors.inverse, borderRadius: t.radius.lg, padding: t.space.md }}>
          <Text style={{ color: t.colors.onInverse }}>What can we make tonight? Under 40 min.</Text>
        </View>
      </Rise>
      {ideas.map((idea, i) => (
        <Rise key={idea.title} index={i + 1}>
          <View
            style={{
              backgroundColor: t.tints[idea.tint].bg,
              borderRadius: t.radius.lg,
              padding: t.space.sm,
              flexDirection: 'row',
              alignItems: 'center',
              gap: t.space.md,
            }}
          >
            <FoodThumb emoji={idea.emoji} tint={idea.tint} size={44} onWhite />
            <View style={{ flex: 1, minWidth: 0, gap: 2 }}>
              <Text variant="label" style={{ color: t.tints[idea.tint].text }} numberOfLines={1}>
                {idea.title}
              </Text>
              <Text variant="caption" style={{ color: t.tints[idea.tint].text }}>
                {idea.meta}
              </Text>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.xs }}>
                <Tag>{idea.have}</Tag>
                {idea.need ? <Tag kind="need">{idea.need}</Tag> : null}
              </View>
            </View>
          </View>
        </Rise>
      ))}
    </View>
  );
}

function PlanMock() {
  const t = useTheme();
  const days: { day: string; meal: string; tint: TintName; cook: typeof ALICE; need?: number }[] = [
    { day: 'Mon', meal: 'Lemon chicken traybake', tint: 'blush', cook: ALICE, need: 1 },
    { day: 'Tue', meal: 'Chicken tacos', tint: 'mint', cook: BOB },
    { day: 'Thu', meal: 'Chickpea curry', tint: 'butter', cook: ALICE, need: 3 },
    { day: 'Fri', meal: 'Pizza night', tint: 'sky', cook: BOB, need: 4 },
  ];
  return (
    <Panel tint="lilac" title="This week" caption="7 dinners · dairy-free Thu">
      {days.map((d, i) => (
        <Rise key={d.day} index={i}>
          <View
            style={{
              backgroundColor: t.tints[d.tint].bg,
              borderRadius: t.radius.md,
              padding: t.space.sm,
              flexDirection: 'row',
              alignItems: 'center',
              gap: t.space.sm,
            }}
          >
            <Text style={[t.type.pill, { width: 32, color: t.tints[d.tint].text }]}>
              {d.day.toUpperCase()}
            </Text>
            <Text variant="label" style={{ flex: 1, color: t.tints[d.tint].text }} numberOfLines={1}>
              {d.meal}
            </Text>
            <Avatar id={d.cook.id} name={d.cook.name} size={22} />
            {d.need ? <Tag kind="need">{`Need ${d.need}`}</Tag> : <Tag>Have all</Tag>}
          </View>
        </Rise>
      ))}
      <Rise index={days.length}>
        <View
          style={{
            borderWidth: 1.5,
            borderStyle: 'dashed',
            borderColor: t.tints.lilac.text,
            borderRadius: t.radius.md,
            padding: t.space.sm,
          }}
        >
          <Text variant="label" style={{ color: t.tints.lilac.text }}>
            Draft plan · 14 items to buy · 18 from your Cabinet
          </Text>
        </View>
      </Rise>
    </Panel>
  );
}
