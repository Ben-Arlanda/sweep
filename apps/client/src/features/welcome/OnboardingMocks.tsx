import { Image } from 'expo-image';
import {
  ArrowLeftRight,
  Calendar,
  Check,
  Clipboard,
  Clock,
  FileText,
  Heart,
  Image as ImageIcon,
  Link,
  MoreHorizontal,
  Pencil,
  Refrigerator,
  Search,
  ShoppingBasket,
  Sparkles,
  type LucideIcon,
} from 'lucide-react-native';
import type { ReactNode } from 'react';
import { Text, View, type DimensionValue, type StyleProp, type ViewStyle } from 'react-native';
import Animated, {
  interpolateColor,
  useAnimatedStyle,
  type SharedValue,
} from 'react-native-reanimated';

import { Icon } from '@/components/Icon';
import { useTheme } from '@/theme/useTheme';

import { shownAt } from './loop';
import { PHOTOS } from './photos';
import type { StoryKey } from './story';
import { useLoop } from './useLoop';

type Loop = SharedValue<number>;

/**
 * The picture on each onboarding page (direction A, "Clean Slate"): a small copy of the
 * real screen, playing its feature on a loop. Decorative: the page's words say what it is.
 */
export function OnboardingMock({ story, active }: { story: StoryKey; active: boolean }) {
  const p = useLoop(active);
  const Mock = MOCKS[story];
  return <Mock p={p} />;
}

const MOCKS: Record<StoryKey, (props: { p: Loop }) => ReactNode> = {
  snap: SnapMock,
  ideas: IdeasMock,
  recipes: RecipesMock,
  plan: PlanMock,
  list: ListMock,
  sync: SyncMock,
};

const ROW_LINE = '#edf0f5';

// ---------- building blocks ----------

/** Fades and lifts its children in while the clock is inside [start, end]. */
function Show({
  p,
  start,
  end = 0.94,
  style,
  children,
}: {
  p: Loop;
  start: number;
  end?: number;
  style?: StyleProp<ViewStyle>;
  children: ReactNode;
}) {
  const shown = useAnimatedStyle(() => {
    const o = shownAt(p.get(), start, end);
    return { opacity: o, transform: [{ translateY: (1 - o) * 10 }] };
  });
  return <Animated.View style={[style, shown]}>{children}</Animated.View>;
}

function Card({ style, children }: { style?: StyleProp<ViewStyle>; children: ReactNode }) {
  const t = useTheme();
  return (
    <View
      style={[
        {
          backgroundColor: t.colors.surface,
          borderRadius: 20,
          borderWidth: 1,
          borderColor: t.colors.border,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}

function Tick({ size = 22 }: { size?: number }) {
  const t = useTheme();
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: size / 2,
        backgroundColor: t.colors.action,
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Icon icon={Check} size={size * 0.6} color={t.colors.onAction} strong />
    </View>
  );
}

function Label({
  children,
  muted,
  size = 15,
  lines = 1,
}: {
  children: ReactNode;
  muted?: boolean;
  size?: number;
  lines?: number;
}) {
  const t = useTheme();
  return (
    <Text
      numberOfLines={lines}
      style={{
        fontFamily: muted ? t.fonts.body : t.fonts.displayBold,
        fontSize: size,
        lineHeight: size + 5,
        color: muted ? t.colors.textMuted : t.colors.text,
      }}
    >
      {children}
    </Text>
  );
}

function Eyebrow({ children }: { children: ReactNode }) {
  const t = useTheme();
  return (
    <Text
      style={{
        fontFamily: t.fonts.displayBold,
        fontSize: 12,
        letterSpacing: 0.6,
        color: t.colors.textMuted,
        paddingHorizontal: 4,
      }}
    >
      {children}
    </Text>
  );
}

function SuggestedPill() {
  const t = useTheme();
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        alignSelf: 'flex-start',
        height: 26,
        paddingHorizontal: 10,
        borderRadius: t.radius.pill,
        backgroundColor: t.colors.action,
      }}
    >
      <Icon icon={Sparkles} size={13} color={t.colors.onAction} />
      <Text style={[t.type.pill, { color: t.colors.onAction }]}>Suggested by Sweep</Text>
    </View>
  );
}

/** A button's look without being one: the mock is a picture, not controls. */
function FakeButton({
  title,
  primary,
  flex = 1,
}: {
  title: string;
  primary?: boolean;
  flex?: number;
}) {
  const t = useTheme();
  return (
    <View
      style={{
        flex,
        height: 38,
        borderRadius: t.radius.pill,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: primary ? t.colors.action : t.colors.surface,
        borderWidth: 1,
        borderColor: t.colors.border,
      }}
    >
      <Text style={{ fontFamily: t.fonts.displayBold, fontSize: 13, color: t.colors.text }}>
        {title}
      </Text>
    </View>
  );
}

function Chip({ title, selected }: { title: string; selected?: boolean }) {
  const t = useTheme();
  return (
    <View
      style={{
        height: 32,
        paddingHorizontal: 13,
        borderRadius: t.radius.pill,
        justifyContent: 'center',
        backgroundColor: selected ? t.colors.selected : t.colors.surface,
        borderWidth: 1,
        borderColor: selected ? t.colors.selected : t.colors.border,
      }}
    >
      <Text
        style={{
          fontFamily: t.fonts.body,
          fontSize: 13,
          color: selected ? t.colors.onSelected : t.colors.text,
        }}
      >
        {title}
      </Text>
    </View>
  );
}

function Photo({ uri, height, width }: { uri: string; height: number; width?: DimensionValue }) {
  const t = useTheme();
  return (
    <Image
      source={{ uri }}
      style={{ width: width ?? '100%', height, borderRadius: 14, backgroundColor: t.colors.fill }}
      contentFit="cover"
      transition={200}
    />
  );
}

// ---------- 1 · Snap your Kitchen ----------

// What's in the fridge photo, so the list matches the picture.
const SEEN = [
  { name: 'Milk', qty: '1 L' },
  { name: 'Eggs', qty: '6' },
  { name: 'Chicken breasts', qty: '500 g' },
  { name: 'Carrots', qty: '4' },
];

// Where the photo's own scan line and camera button sit, as fractions of its size.
const FRIDGE_RATIO = 1448 / 1086;
const SCAN_LINE_Y = 0.425;
const CAMERA = { x: 0.5, y: 0.882, size: 0.12 };

function SnapMock({ p }: { p: Loop }) {
  const t = useTheme();
  // The photo's scan line glows brighter and softer, as if it's reading the shelves.
  const glow = useAnimatedStyle(() => ({
    opacity: 0.35 + 0.65 * (0.5 - 0.5 * Math.cos(p.get() * Math.PI * 6)),
  }));
  // A ring pulses out from the camera button.
  const ring = useAnimatedStyle(() => {
    const r = (p.get() * 3) % 1;
    return { opacity: 1 - r, transform: [{ scale: 1 + r * 0.6 }] };
  });
  return (
    <View style={{ gap: t.space.md }}>
      <View style={{ borderRadius: 20, overflow: 'hidden', backgroundColor: t.colors.fill }}>
        <Image
          source={require('../../../assets/images/onboarding-fridge.webp')}
          style={{ width: '100%', aspectRatio: FRIDGE_RATIO }}
          contentFit="cover"
        />
        <Animated.View
          style={[
            {
              position: 'absolute',
              left: '8%',
              right: '8%',
              top: `${SCAN_LINE_Y * 100}%`,
              height: 3,
              marginTop: -1.5,
              borderRadius: 2,
              backgroundColor: '#9dffb8',
              boxShadow: '0px 0px 14px 5px rgba(80, 230, 130, 0.75)',
            },
            glow,
          ]}
        />
        <Animated.View
          style={[
            {
              position: 'absolute',
              left: `${(CAMERA.x - CAMERA.size / 2) * 100}%`,
              top: `${CAMERA.y * 100}%`,
              width: `${CAMERA.size * 100}%`,
              aspectRatio: 1,
              marginTop: `${(-CAMERA.size / 2) * 100}%`,
              borderRadius: 999,
              borderWidth: 2,
              borderColor: 'rgba(80, 230, 130, 0.9)',
            },
            ring,
          ]}
        />
      </View>
      <Card style={{ paddingHorizontal: 14, paddingVertical: 4 }}>
        <View style={{ paddingTop: 8, paddingBottom: 2 }}>
          <Label muted size={13}>
            Check what Sweep saw
          </Label>
        </View>
        {SEEN.map((item, i) => (
          <Show key={item.name} p={p} start={0.08 + i * 0.08}>
            <View style={{ height: 38, flexDirection: 'row', alignItems: 'center', gap: 12 }}>
              <Tick />
              <View style={{ flex: 1 }}>
                <Label>{item.name}</Label>
              </View>
              <Label muted size={13}>
                {item.qty}
              </Label>
            </View>
          </Show>
        ))}
      </Card>
    </View>
  );
}

// ---------- 2 · Dinner ideas ----------

function IdeasMock({ p }: { p: Loop }) {
  const t = useTheme();
  // "Use my Kitchen" gets picked, then the idea arrives and gets a heart.
  const pick = useAnimatedStyle(() => {
    const on = shownAt(p.get(), 0.15, 0.97, 0.04);
    return {
      backgroundColor: interpolateColor(on, [0, 1], [t.colors.surface, t.colors.selected]),
      borderColor: interpolateColor(on, [0, 1], [t.colors.border, t.colors.selected]),
    };
  });
  const pickText = useAnimatedStyle(() => ({
    color: interpolateColor(
      shownAt(p.get(), 0.15, 0.97, 0.04),
      [0, 1],
      [t.colors.text, t.colors.onSelected],
    ),
  }));
  const beat = useAnimatedStyle(() => ({
    transform: [{ scale: 1 + 0.25 * shownAt(p.get(), 0.62, 0.72, 0.05) }],
  }));
  const hearted = useAnimatedStyle(() => ({ opacity: shownAt(p.get(), 0.64, 0.97, 0.02) }));

  return (
    <View style={{ gap: t.space.md }}>
      <View style={{ flexDirection: 'row', gap: 8, overflow: 'hidden' }}>
        <Chip title="All" />
        <Chip title="Under 30 min" />
        <Animated.View
          style={[
            {
              height: 32,
              paddingHorizontal: 13,
              borderRadius: t.radius.pill,
              justifyContent: 'center',
              borderWidth: 1,
            },
            pick,
          ]}
        >
          <Animated.Text style={[{ fontFamily: t.fonts.body, fontSize: 13 }, pickText]}>
            Use my Kitchen
          </Animated.Text>
        </Animated.View>
        <Chip title="Vegetarian" />
      </View>
      <Show p={p} start={0.25} end={0.97}>
        <Card style={{ padding: 10, gap: 8 }}>
          <View>
            <Photo uri={PHOTOS.dhalCurry} height={130} />
            <Animated.View
              style={[
                {
                  position: 'absolute',
                  top: 8,
                  right: 8,
                  width: 32,
                  height: 32,
                  borderRadius: 16,
                  backgroundColor: t.colors.surface,
                  alignItems: 'center',
                  justifyContent: 'center',
                },
                beat,
              ]}
            >
              <Icon icon={Heart} size={17} color={t.colors.text} />
              <Animated.View style={[{ position: 'absolute' }, hearted]}>
                <Icon icon={Heart} size={17} color={t.colors.danger} fill={t.colors.danger} />
              </Animated.View>
            </Animated.View>
          </View>
          <View style={{ paddingHorizontal: 4, gap: 6 }}>
            <Label size={17}>Sri Lankan dhal curry</Label>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
              <Icon icon={Clock} size={14} color={t.colors.textMuted} />
              <Label muted size={13}>
                35 min · Serves 4
              </Label>
            </View>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
              <Tick size={20} />
              <Label muted size={13}>
                Uses 7 kitchen items
              </Label>
            </View>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
              <Tick size={20} />
              <Label muted size={13}>
                Nothing to buy
              </Label>
            </View>
            <View style={{ flexDirection: 'row', gap: 8, marginTop: 2 }}>
              <FakeButton title="Cook this tonight" primary flex={2} />
              <FakeButton title="Recipe" />
            </View>
          </View>
        </Card>
      </Show>
    </View>
  );
}

// ---------- 3 · Recipes ----------

const SOURCES: { icon: LucideIcon; title: string; caption: string }[] = [
  { icon: Clipboard, title: 'Paste text', caption: 'From a website, message or notes' },
  { icon: ImageIcon, title: 'Photos', caption: 'Up to 3 pages of a cookbook or a card' },
  { icon: Link, title: 'Link', caption: 'A recipe page on the web' },
  { icon: FileText, title: 'PDF', caption: 'A saved or printed recipe' },
  { icon: Pencil, title: 'Type it in', caption: 'Start from a blank recipe' },
];

// About the width of "quick vegetarian dinner", so the cursor sits right after it.
const TYPED_WIDTH = 172;

function RecipesMock({ p }: { p: Loop }) {
  const t = useTheme();
  // The search types itself out, holds, then clears.
  const typed = useAnimatedStyle(() => {
    const v = p.get();
    const r = v < 0.08 ? 0 : v < 0.48 ? (v - 0.08) / 0.4 : v < 0.9 ? 1 : 0;
    return { maxWidth: r * TYPED_WIDTH };
  });
  const caret = useAnimatedStyle(() => ({ opacity: Math.floor(p.get() * 12) % 2 === 0 ? 1 : 0 }));
  return (
    <View style={{ gap: 10 }}>
      <Card
        style={{
          height: 44,
          borderRadius: t.radius.pill,
          flexDirection: 'row',
          alignItems: 'center',
          gap: 10,
          paddingHorizontal: 14,
        }}
      >
        <Icon icon={Search} size={18} color={t.colors.textMuted} />
        <Animated.View style={[{ overflow: 'hidden' }, typed]}>
          <Text
            numberOfLines={1}
            style={{
              fontFamily: t.fonts.body,
              fontSize: 15,
              color: t.colors.text,
              width: TYPED_WIDTH,
            }}
          >
            quick vegetarian dinner
          </Text>
        </Animated.View>
        <Animated.View
          style={[{ width: 2, height: 16, backgroundColor: t.colors.text, marginLeft: -8 }, caret]}
        />
      </Card>
      <View style={{ flexDirection: 'row', gap: 8 }}>
        <View
          style={{
            flex: 1,
            height: 42,
            borderRadius: t.radius.pill,
            backgroundColor: t.colors.action,
            borderWidth: 1,
            borderColor: t.colors.border,
            flexDirection: 'row',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
          }}
        >
          <Icon icon={Sparkles} size={16} color={t.colors.onAction} />
          <Text style={{ fontFamily: t.fonts.displayBold, fontSize: 14, color: t.colors.onAction }}>
            Find dinner ideas
          </Text>
        </View>
        <Card
          style={{
            width: 42,
            height: 42,
            borderRadius: 12,
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Icon icon={Heart} size={18} color={t.colors.text} />
        </Card>
      </View>
      <Card style={{ padding: 8 }}>
        <View style={{ paddingHorizontal: 8, paddingTop: 4, paddingBottom: 2 }}>
          <Label>Add a recipe</Label>
        </View>
        {SOURCES.map((s, i) => (
          <SourceRow key={s.title} p={p} index={i} {...s} />
        ))}
      </Card>
    </View>
  );
}

function SourceRow({
  p,
  index,
  icon,
  title,
  caption,
}: {
  p: Loop;
  index: number;
  icon: LucideIcon;
  title: string;
  caption: string;
}) {
  const t = useTheme();
  // Each way in lights up in turn.
  const lit = useAnimatedStyle(() => ({
    backgroundColor: interpolateColor(
      shownAt(p.get(), 0.1 + index * 0.16, 0.26 + index * 0.16, 0.03),
      [0, 1],
      [t.colors.surface, t.colors.actionSoft],
    ),
  }));
  return (
    <Animated.View
      style={[
        {
          flexDirection: 'row',
          alignItems: 'center',
          gap: 12,
          paddingHorizontal: 8,
          paddingVertical: 6,
          borderRadius: 10,
        },
        lit,
      ]}
    >
      <Icon icon={icon} size={19} color={t.colors.text} />
      <View style={{ flex: 1 }}>
        <Label size={14}>{title}</Label>
        <Label muted size={12}>
          {caption}
        </Label>
      </View>
    </Animated.View>
  );
}

// ---------- 4 · Plan the week ----------

const WEEK = [
  {
    day: 'Mon',
    date: '24',
    title: 'Greek lemon chicken and potatoes',
    meta: '55 min · For 4',
    photo: PHOTOS.greekChicken,
  },
  {
    day: 'Tue',
    date: '25',
    title: 'Sri Lankan dhal curry',
    meta: '35 min · For 4',
    photo: PHOTOS.dhalCurry,
  },
  {
    day: 'Thu',
    date: '27',
    title: 'Lemon chicken orzo',
    meta: '25 min · For 4',
    photo: PHOTOS.lemonOrzo,
  },
];

function PlanMock({ p }: { p: Loop }) {
  const t = useTheme();
  // The first night's swap button turns, as if someone swapped the dinner.
  const swap = useAnimatedStyle(() => {
    const v = Math.min(1, Math.max(0, (p.get() - 0.5) / 0.12));
    return { transform: [{ rotate: `${v * 180}deg` }] };
  });
  return (
    <View style={{ gap: 10 }}>
      <Card style={{ padding: 14, gap: 6 }}>
        <SuggestedPill />
        <Label size={17}>4 dinners · 4 things to buy</Label>
        <Label muted size={13}>
          Built around what you have.
        </Label>
      </Card>
      <Eyebrow>MON 24 – FRI 28 NOV</Eyebrow>
      {WEEK.map((night, i) => (
        <Show key={night.day} p={p} start={0.06 + i * 0.1}>
          <Card
            style={{
              paddingHorizontal: 12,
              paddingVertical: 8,
              flexDirection: 'row',
              alignItems: 'center',
              gap: 12,
            }}
          >
            <View style={{ width: 32, alignItems: 'center' }}>
              <Label muted size={11}>
                {night.day}
              </Label>
              <Label size={17}>{night.date}</Label>
            </View>
            <Photo uri={night.photo} height={42} width={42} />
            <View style={{ flex: 1 }}>
              <Label size={14} lines={2}>
                {night.title}
              </Label>
              <Label muted size={12}>
                {night.meta}
              </Label>
            </View>
            <Animated.View style={i === 0 ? swap : undefined}>
              <Icon icon={ArrowLeftRight} size={18} color={t.colors.textMuted} />
            </Animated.View>
          </Card>
        </Show>
      ))}
    </View>
  );
}

// ---------- 5 · Shopping list ----------

function ListMock({ p }: { p: Loop }) {
  const t = useTheme();
  const done = useAnimatedStyle(() => {
    const on = shownAt(p.get(), 0.3, 0.92, 0.04);
    return {
      backgroundColor: interpolateColor(on, [0, 1], [t.colors.surface, t.colors.action]),
      borderColor: interpolateColor(on, [0, 1], [t.colors.textMuted, t.colors.action]),
    };
  });
  const checkShown = useAnimatedStyle(() => ({ opacity: shownAt(p.get(), 0.3, 0.92, 0.04) }));
  const strike = useAnimatedStyle(() => ({ width: shownAt(p.get(), 0.32, 0.92, 0.08) * 54 }));
  return (
    <View style={{ gap: 10 }}>
      <View style={{ flexDirection: 'row', gap: 8 }}>
        <Chip title="All" selected />
        <Chip title="Aisle" />
        <Chip title="Coles" />
        <Chip title="Woolies" />
      </View>
      <Eyebrow>FRUIT &amp; VEG</Eyebrow>
      <Card style={{ paddingHorizontal: 14 }}>
        {['Lemons', 'Coriander', 'Red onions'].map((name, i) => (
          <View
            key={name}
            style={{
              height: 46,
              flexDirection: 'row',
              alignItems: 'center',
              gap: 12,
              borderBottomWidth: i < 2 ? 1 : 0,
              borderBottomColor: ROW_LINE,
            }}
          >
            <View
              style={{
                width: 22,
                height: 22,
                borderRadius: 11,
                borderWidth: 2,
                borderColor: t.colors.textMuted,
              }}
            />
            <View style={{ flex: 1 }}>
              <Label>{name}</Label>
            </View>
            <Icon icon={MoreHorizontal} size={18} color={t.colors.textMuted} />
          </View>
        ))}
      </Card>
      <Eyebrow>DAIRY &amp; EGGS</Eyebrow>
      <Card style={{ paddingHorizontal: 14 }}>
        <View style={{ height: 46, flexDirection: 'row', alignItems: 'center', gap: 12 }}>
          <Animated.View
            style={[
              {
                width: 22,
                height: 22,
                borderRadius: 11,
                borderWidth: 2,
                alignItems: 'center',
                justifyContent: 'center',
              },
              done,
            ]}
          >
            <Animated.View style={checkShown}>
              <Icon icon={Check} size={13} color={t.colors.onAction} strong />
            </Animated.View>
          </Animated.View>
          <View style={{ flex: 1, justifyContent: 'center' }}>
            <Label>Ricotta</Label>
            <Animated.View
              style={[
                { position: 'absolute', left: 0, height: 2, backgroundColor: t.colors.text },
                strike,
              ]}
            />
          </View>
          <Icon icon={MoreHorizontal} size={18} color={t.colors.textMuted} />
        </View>
      </Card>
      <Show p={p} start={0.4} end={0.9}>
        <View
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            gap: t.space.md,
            backgroundColor: t.colors.inverse,
            borderRadius: t.radius.lg,
            padding: t.space.md,
          }}
        >
          <Tick size={30} />
          <View style={{ flex: 1 }}>
            <Text
              style={{ fontFamily: t.fonts.displayBold, fontSize: 14, color: t.colors.onInverse }}
            >
              Ticked off Ricotta
            </Text>
            <Text
              style={{ fontFamily: t.fonts.body, fontSize: 12, color: t.colors.onSelectedMuted }}
            >
              Added Ricotta to your Kitchen
            </Text>
          </View>
          <Text style={{ fontFamily: t.fonts.displayBold, fontSize: 14, color: t.colors.action }}>
            Undo
          </Text>
        </View>
      </Show>
    </View>
  );
}

// ---------- 6 · All in one ----------

const PARTS: { icon: LucideIcon; title: string; caption: string }[] = [
  { icon: Refrigerator, title: 'Kitchen', caption: 'Knows what you have' },
  { icon: Sparkles, title: 'Dinner ideas', caption: 'From what you have' },
  { icon: ShoppingBasket, title: 'Shopping list', caption: "Only what's missing" },
  { icon: Calendar, title: 'Meal plan', caption: 'Your week, sorted' },
];
// Kitchen → ideas → plan → list: the loop goes round the grid clockwise.
const TURN = [0, 1, 3, 2];

function SyncMock({ p }: { p: Loop }) {
  const float = useAnimatedStyle(() => ({
    transform: [{ translateY: Math.sin(p.get() * Math.PI * 4) * 6 }],
  }));
  return (
    <View style={{ height: 320, justifyContent: 'center' }}>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12 }}>
        {PARTS.map((part, i) => (
          <PartTile key={part.title} p={p} turn={TURN[i]} {...part} />
        ))}
      </View>
      <Animated.View
        pointerEvents="none"
        style={[{ position: 'absolute', alignSelf: 'center', top: 110 }, float]}
      >
        <Image
          source={require('../../../assets/images/welcome-chef.webp')}
          style={{ width: 104, height: 101 }}
          contentFit="contain"
        />
      </Animated.View>
    </View>
  );
}

function PartTile({
  p,
  turn,
  icon,
  title,
  caption,
}: {
  p: Loop;
  turn: number;
  icon: LucideIcon;
  title: string;
  caption: string;
}) {
  const t = useTheme();
  const lit = useAnimatedStyle(() => ({
    borderColor: interpolateColor(
      shownAt(p.get(), turn * 0.25, turn * 0.25 + 0.22, 0.04),
      [0, 1],
      [t.colors.border, t.colors.action],
    ),
  }));
  return (
    <Animated.View
      style={[
        {
          width: '47%',
          flexGrow: 1,
          height: 148,
          padding: 14,
          borderRadius: 20,
          borderWidth: 2,
          backgroundColor: t.colors.surface,
          justifyContent: turn > 1 ? 'flex-end' : 'flex-start',
          gap: 2,
        },
        lit,
      ]}
    >
      <Icon icon={icon} size={20} color={t.colors.text} />
      <Label>{title}</Label>
      <Label muted size={12} lines={2}>
        {caption}
      </Label>
    </Animated.View>
  );
}

// ---------- Welcome ----------

/** The welcome picture is drawn at this width; the panel scales it to the phone. */
export const WELCOME_SCENE_WIDTH = 330;

/** The welcome picture: tonight's idea on a tilted card, with Sweep's chef beside it. */
export function WelcomeScene({ active }: { active: boolean }) {
  const p = useLoop(active);
  const cardFloat = useAnimatedStyle(() => ({
    transform: [{ translateY: Math.sin(p.get() * Math.PI * 2) * 6 }, { rotate: '4deg' }],
  }));
  const chefFloat = useAnimatedStyle(() => ({
    transform: [{ translateY: Math.sin(p.get() * Math.PI * 2 + Math.PI) * 6 }],
  }));
  return (
    <View aria-hidden style={{ width: WELCOME_SCENE_WIDTH, height: 330 }}>
      <Animated.View style={[{ position: 'absolute', right: 6, top: 14, width: 220 }, cardFloat]}>
        <Card style={{ padding: 10, gap: 8 }}>
          <Photo uri={PHOTOS.dhalCurry} height={132} />
          <View style={{ paddingHorizontal: 4, gap: 7 }}>
            <SuggestedPill />
            <Label>Sri Lankan dhal curry</Label>
            <Show p={p} start={0.12}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                <Tick size={20} />
                <Label muted size={13}>
                  Uses 7 kitchen items
                </Label>
              </View>
            </Show>
            <Show p={p} start={0.22}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                <Tick size={20} />
                <Label muted size={13}>
                  Nothing to buy
                </Label>
              </View>
            </Show>
          </View>
        </Card>
      </Animated.View>
      <Animated.View style={[{ position: 'absolute', left: 0, bottom: 0 }, chefFloat]}>
        <Image
          source={require('../../../assets/images/welcome-chef.webp')}
          style={{ width: 150, height: 146 }}
          contentFit="contain"
        />
      </Animated.View>
    </View>
  );
}
