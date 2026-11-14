import { createContext, use, useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { Text, View } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withSpring,
  withTiming,
} from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { tabBarHeight } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

type ToastMessage = { tag?: string; text: string };
type ShowToast = (message: ToastMessage) => void;

const ToastContext = createContext<ShowToast>(() => {});

/**
 * Show a short confirmation from anywhere: `const toast = useToast(); toast({ tag: 'Cabinet', text: 'Added 1.5 kg chicken' })`.
 *
 * Why a context: the toast must sit above every screen, but the thing that triggers it
 * (a list row) is deep inside one. The provider owns the single toast; the hook hands
 * any component a way to show it.
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

  useEffect(() => {
    if (!message) return;
    y.set(reduceMotion ? 0 : withSpring(0, t.motion.spring.gentle));
    opacity.set(withTiming(1, { duration: t.motion.duration.fast }));
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      y.set(reduceMotion ? 40 : withTiming(40, { duration: t.motion.duration.base }));
      opacity.set(withTiming(0, { duration: t.motion.duration.base }));
    }, 2200);
    return () => clearTimeout(timer.current);
  }, [message, opacity, reduceMotion, t.motion, y]);

  const animated = useAnimatedStyle(() => ({
    opacity: opacity.get(),
    transform: [{ translateY: y.get() }],
  }));

  return (
    <ToastContext value={show}>
      {children}
      <Animated.View
        pointerEvents="none"
        accessibilityLiveRegion="polite"
        style={[
          {
            position: 'absolute',
            left: t.space.lg,
            right: t.space.lg,
            // Above the tab bar, which every screen with a toast now has.
            bottom: insets.bottom + tabBarHeight + t.space.lg,
            alignItems: 'center',
          },
          animated,
        ]}
      >
        {message ? (
          <View
            // Polite, not "alert": a tick confirmation shouldn't interrupt the screen reader.
            style={{
              maxWidth: 480,
              width: '100%',
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
        ) : null}
      </Animated.View>
    </ToastContext>
  );
}
