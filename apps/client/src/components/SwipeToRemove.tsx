import { Trash2 } from 'lucide-react-native';
import { useState, type ReactNode } from 'react';
import { View } from 'react-native';
import ReanimatedSwipeable from 'react-native-gesture-handler/ReanimatedSwipeable';
import Animated, { FadeOut, LinearTransition, ReduceMotion } from 'react-native-reanimated';

import { Icon } from '@/components/Icon';
import { Text } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

/**
 * Swipe a row left past ~40% of its width to remove it: a red Delete panel follows the
 * finger, then the row fades and the rows below glide up. Gestures can't be the only way
 * (WCAG 2.5.1), so the screen must offer the same Remove in a menu; the panel is hidden
 * from screen readers for that reason. Undo is the screen's job (a toast).
 */
export function SwipeToRemove({
  onRemove,
  background,
  children,
}: {
  onRemove: () => void;
  /** The row's own background, so the red panel doesn't show through it. */
  background: string;
  children: ReactNode;
}) {
  const t = useTheme();
  const [width, setWidth] = useState(0);

  return (
    <Animated.View
      onLayout={(e) => setWidth(e.nativeEvent.layout.width)}
      exiting={FadeOut.duration(t.motion.duration.base).reduceMotion(ReduceMotion.System)}
      layout={LinearTransition.duration(t.motion.duration.base).reduceMotion(ReduceMotion.System)}
    >
      <ReanimatedSwipeable
        friction={1.2}
        overshootRight={false}
        rightThreshold={width > 0 ? width * 0.4 : 120}
        childrenContainerStyle={{ backgroundColor: background }}
        onSwipeableOpen={onRemove}
        renderRightActions={() => (
          <View
            aria-hidden
            importantForAccessibility="no-hide-descendants"
            style={{
              width: width || 320,
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'flex-end',
              gap: t.space.sm,
              paddingRight: t.space.lg,
              backgroundColor: t.colors.dangerSoft, // with danger text: contrast-tested
            }}
          >
            <Icon icon={Trash2} size={20} color={t.colors.danger} />
            <Text variant="label" style={{ color: t.colors.danger }}>
              Delete
            </Text>
          </View>
        )}
      >
        {children}
      </ReanimatedSwipeable>
    </Animated.View>
  );
}
