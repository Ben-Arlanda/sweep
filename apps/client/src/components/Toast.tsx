import { Check, ShoppingCart, X } from 'lucide-react-native';
import {
  createContext,
  use,
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { Pressable, Text, View } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withSpring,
  withTiming,
} from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { FoodThumb } from '@/components/FoodThumb';
import { Icon } from '@/components/Icon';
import { tabBarHeight, type TintName } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

/** A quick confirmation: shown ~2 s, nothing to press. */
type PlainToast = { kind?: 'plain'; tag?: string; text: string };
/** Something happened, with Undo: stays ~8 s, and pauses while touched or focused. */
type UndoToast = { kind: 'undo'; text: string; detail?: string; onUndo: () => void };
/** A question ("Add avocado to your shopping list?"): stays until answered or replaced. */
type AskToast = {
  kind: 'ask';
  text: string;
  emoji: string;
  tint: TintName;
  actionLabel: string;
  onAction: () => void;
};
export type ToastMessage = PlainToast | UndoToast | AskToast;
type ShowToast = (message: ToastMessage) => void;

const PLAIN_MS = 2200;
const UNDO_MS = 8000; // long enough to read and reach (WCAG 2.2.1), and it pauses

const ToastContext = createContext<ShowToast>(() => {});

/**
 * Show a toast from anywhere: `const toast = useToast(); toast({ text: 'Moved to the fridge' })`.
 *
 * Why a context: the toast must sit above every screen, but the thing that triggers it
 * (a list row) is deep inside one. The provider owns the single toast; the hook hands
 * any component a way to show it. A new toast replaces the one on screen.
 */
export function useToast() {
  return use(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const reduceMotion = useReducedMotion();
  const [message, setMessage] = useState<ToastMessage | null>(null);
  const y = useSharedValue(40);
  const opacity = useSharedValue(0);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const show = useCallback<ShowToast>((m) => setMessage({ ...m }), []);

  const hide = useCallback(() => {
    clearTimeout(timer.current);
    y.set(reduceMotion ? 40 : withTiming(40, { duration: t.motion.duration.base }));
    opacity.set(withTiming(0, { duration: t.motion.duration.base }));
    // Unmount after the fade, so its buttons can't be reached while invisible.
    timer.current = setTimeout(() => setMessage(null), t.motion.duration.base);
  }, [opacity, reduceMotion, t.motion, y]);

  const startTimer = useCallback(
    (m: ToastMessage) => {
      clearTimeout(timer.current);
      if (m.kind === 'ask') return; // waits for an answer
      timer.current = setTimeout(hide, m.kind === 'undo' ? UNDO_MS : PLAIN_MS);
    },
    [hide],
  );

  useEffect(() => {
    if (!message) return;
    y.set(reduceMotion ? 0 : withSpring(0, t.motion.spring.gentle));
    opacity.set(withTiming(1, { duration: t.motion.duration.fast }));
    startTimer(message);
    return () => clearTimeout(timer.current);
  }, [message, opacity, reduceMotion, startTimer, t.motion, y]);

  const hold = () => clearTimeout(timer.current);
  const release = () => {
    if (message) startTimer(message);
  };

  const animated = useAnimatedStyle(() => ({
    opacity: opacity.get(),
    transform: [{ translateY: y.get() }],
  }));

  const interactive = message?.kind === 'undo' || message?.kind === 'ask';

  return (
    <ToastContext value={show}>
      {children}
      <Animated.View
        pointerEvents={interactive ? 'box-none' : 'none'}
        accessibilityLiveRegion="polite"
        style={[
          {
            position: 'absolute',
            left: t.space.md,
            right: t.space.md,
            // Above the tab bar, which every screen with a toast now has.
            bottom: insets.bottom + tabBarHeight + t.space.md,
            alignItems: 'center',
          },
          animated,
        ]}
      >
        {message ? (
          <View
            onPointerEnter={hold}
            onPointerLeave={release}
            onTouchStart={hold}
            onTouchEnd={release}
            style={{ maxWidth: 480, width: '100%' }}
          >
            {message.kind === 'undo' ? (
              <UndoCard
                message={message}
                onUndo={() => (message.onUndo(), hide())}
                hold={hold}
                release={release}
              />
            ) : message.kind === 'ask' ? (
              <AskCard
                message={message}
                onAction={() => (message.onAction(), hide())}
                onClose={hide}
              />
            ) : (
              <PlainCard message={message} />
            )}
          </View>
        ) : null}
      </Animated.View>
    </ToastContext>
  );
}

function PlainCard({ message }: { message: PlainToast }) {
  const t = useTheme();
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.sm,
        backgroundColor: t.colors.inverse,
        borderRadius: t.radius.md,
        paddingVertical: t.space.md,
        paddingHorizontal: t.space.lg,
        boxShadow: t.shadow.raised,
      }}
    >
      {message.tag ? (
        <View
          style={{
            backgroundColor: t.tints.mint.bg,
            borderRadius: t.radius.sm,
            paddingHorizontal: 7,
            paddingVertical: 2,
          }}
        >
          <Text style={[t.type.pill, { color: t.tints.mint.text }]}>{message.tag}</Text>
        </View>
      ) : null}
      <Text style={[t.type.body, { color: t.colors.onInverse, flexShrink: 1 }]}>
        {message.text}
      </Text>
    </View>
  );
}

/** Dark card: lime tick, what happened, and an outlined Undo. */
function UndoCard({
  message,
  onUndo,
  hold,
  release,
}: {
  message: UndoToast;
  onUndo: () => void;
  hold: () => void;
  release: () => void;
}) {
  const t = useTheme();
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.md,
        backgroundColor: t.colors.inverse,
        borderRadius: t.radius.lg,
        paddingVertical: t.space.md,
        paddingLeft: t.space.md,
        paddingRight: t.space.md,
        boxShadow: t.shadow.raised,
      }}
    >
      <View
        style={{
          width: 36,
          height: 36,
          borderRadius: 18,
          backgroundColor: t.colors.action,
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Icon icon={Check} size={20} color={t.colors.onAction} strong />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={[t.type.label, { color: t.colors.onInverse }]}>{message.text}</Text>
        {message.detail ? (
          <Text style={[t.type.caption, { color: t.colors.onInverse }]}>{message.detail}</Text>
        ) : null}
      </View>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`Undo: ${message.text}${message.detail ? `, ${message.detail}` : ''}`}
        onPress={onUndo}
        onFocus={hold}
        onBlur={release}
        style={({ pressed }) => ({
          minHeight: t.touchTarget,
          paddingHorizontal: t.space.lg,
          borderRadius: t.radius.pill,
          borderWidth: 1.5,
          borderColor: t.colors.onInverse,
          justifyContent: 'center',
          opacity: pressed ? 0.7 : 1,
        })}
      >
        <Text style={[t.type.label, { color: t.colors.onInverse }]}>Undo</Text>
      </Pressable>
    </View>
  );
}

/** Light card: the food, the question, Add to list (lime) and Not now. */
function AskCard({
  message,
  onAction,
  onClose,
}: {
  message: AskToast;
  onAction: () => void;
  onClose: () => void;
}) {
  const t = useTheme();
  return (
    <View
      style={{
        gap: t.space.md,
        backgroundColor: t.colors.surface,
        borderRadius: t.radius.lg,
        padding: t.space.md,
        boxShadow: t.shadow.raised,
        borderWidth: 1,
        borderColor: t.colors.border,
      }}
    >
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.md }}>
        <FoodThumb emoji={message.emoji} tint={message.tint} size={52} />
        <Text
          style={[t.type.label, { flex: 1, fontSize: 17, lineHeight: 22, color: t.colors.text }]}
        >
          {message.text}
        </Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Close"
          onPress={onClose}
          style={({ pressed }) => ({
            width: t.touchTarget,
            height: t.touchTarget,
            alignItems: 'center',
            justifyContent: 'center',
            alignSelf: 'flex-start',
            opacity: pressed ? 0.6 : 1,
          })}
        >
          <Icon icon={X} size={20} color={t.colors.textMuted} />
        </Pressable>
      </View>
      <View style={{ flexDirection: 'row', gap: t.space.sm }}>
        <Pressable
          accessibilityRole="button"
          onPress={onAction}
          style={({ pressed }) => ({
            flex: 1,
            minHeight: 48,
            borderRadius: t.radius.pill,
            backgroundColor: pressed ? t.colors.actionPressed : t.colors.action,
            flexDirection: 'row',
            alignItems: 'center',
            justifyContent: 'center',
            gap: t.space.sm,
          })}
        >
          <Icon icon={ShoppingCart} size={18} color={t.colors.onAction} />
          <Text style={[t.type.label, { color: t.colors.onAction }]}>{message.actionLabel}</Text>
        </Pressable>
        <Pressable
          accessibilityRole="button"
          onPress={onClose}
          style={({ pressed }) => ({
            flex: 1,
            minHeight: 48,
            borderRadius: t.radius.pill,
            borderWidth: 1.5,
            borderColor: t.colors.border,
            alignItems: 'center',
            justifyContent: 'center',
            opacity: pressed ? 0.7 : 1,
          })}
        >
          <Text style={[t.type.label, { color: t.colors.text }]}>Not now</Text>
        </Pressable>
      </View>
    </View>
  );
}
