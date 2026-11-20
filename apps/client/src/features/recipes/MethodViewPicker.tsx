import { Check, ChevronDown, Layers, Zap, type LucideIcon } from 'lucide-react-native';
import { useRef, useState } from 'react';
import { Pressable, View, type HostInstance } from 'react-native';

import { Icon } from '@/components/Icon';
import { measureAnchor, Popover, type Anchor } from '@/components/Popover';
import { Text } from '@/components/ui';
import { haptic } from '@/lib/haptics';
import { useTheme } from '@/theme/useTheme';

import type { MethodView } from './method';

const VIEWS: { value: MethodView; label: string; hint: string; icon: LucideIcon }[] = [
  { value: 'detailed', label: 'Detailed', hint: 'Stages, times and why', icon: Layers },
  { value: 'quick', label: 'Quick', hint: 'Just the steps', icon: Zap },
];

/**
 * "Detailed view ⌄" under the Method heading: tapped, it pops out the two ways to read the
 * method, each with a line saying what you get. The choice is remembered on the device.
 */
export function MethodViewPicker({
  value,
  onChange,
}: {
  value: MethodView;
  onChange: (view: MethodView) => void;
}) {
  const t = useTheme();
  const button = useRef<HostInstance>(null);
  const [anchor, setAnchor] = useState<Anchor | null>(null);
  const current = VIEWS.find((v) => v.value === value) ?? VIEWS[0];

  return (
    <>
      <Pressable
        ref={button}
        accessibilityRole="button"
        accessibilityLabel={`${current.label} view. Change`}
        onPress={async () => setAnchor(await measureAnchor(button))}
        hitSlop={8}
        style={({ pressed }) => ({
          flexDirection: 'row',
          alignItems: 'center',
          gap: 2,
          minHeight: 24,
          opacity: pressed ? 0.7 : 1,
        })}
      >
        <Text style={{ color: t.colors.onBackgroundMuted }}>{current.label} view</Text>
        <Icon icon={ChevronDown} size={16} color={t.colors.onBackgroundMuted} />
      </Pressable>
      {anchor ? (
        <Popover anchor={anchor} label="Method view" width={240} onClose={() => setAnchor(null)}>
          <View accessibilityRole="menu">
            {VIEWS.map((v, i) => {
              const on = v.value === value;
              return (
                <Pressable
                  key={v.value}
                  accessibilityRole="menuitem"
                  accessibilityState={{ checked: on }}
                  aria-checked={on}
                  onPress={() => {
                    setAnchor(null);
                    if (!on) {
                      haptic.select();
                      onChange(v.value);
                    }
                  }}
                  style={({ pressed }) => ({
                    flexDirection: 'row',
                    alignItems: 'center',
                    gap: t.space.md,
                    minHeight: 56,
                    paddingHorizontal: t.space.lg,
                    borderTopWidth: i === 0 ? 0 : 1,
                    borderTopColor: t.colors.border,
                    backgroundColor: pressed ? t.colors.background : 'transparent',
                  })}
                >
                  <Icon icon={v.icon} size={20} color={t.colors.text} />
                  <View style={{ flex: 1 }}>
                    <Text variant="label">{v.label}</Text>
                    <Text variant="caption" muted>
                      {v.hint}
                    </Text>
                  </View>
                  {on ? <Icon icon={Check} size={18} color={t.colors.text} strong /> : null}
                </Pressable>
              );
            })}
          </View>
        </Popover>
      ) : null}
    </>
  );
}
