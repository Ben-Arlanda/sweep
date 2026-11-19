import { ChevronRight, type LucideIcon } from 'lucide-react-native';
import { Pressable } from 'react-native';

import { Icon } from '@/components/Icon';
import { Text } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

/** One line in a ••• Popover menu (Kitchen, Shopping List): icon, label, optional chevron. */
export function MenuItem({
  icon,
  label,
  detail,
  chevron,
  danger,
  divider,
  onPress,
}: {
  icon: LucideIcon;
  label: string;
  detail?: string;
  chevron?: boolean;
  danger?: boolean;
  divider?: boolean;
  onPress: () => void;
}) {
  const t = useTheme();
  const color = danger ? t.colors.danger : t.colors.text;
  return (
    <Pressable
      accessibilityRole="menuitem"
      onPress={onPress}
      style={({ pressed }) => ({
        minHeight: 50,
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.md,
        paddingHorizontal: t.space.lg,
        borderTopWidth: divider ? 1 : 0,
        borderTopColor: t.colors.border,
        backgroundColor: pressed ? t.colors.background : 'transparent',
      })}
    >
      <Icon icon={icon} size={20} color={color} />
      <Text style={{ flex: 1, color }}>{label}</Text>
      {detail ? (
        <Text variant="caption" muted>
          {detail}
        </Text>
      ) : null}
      {chevron ? <Icon icon={ChevronRight} size={16} color={t.colors.text} /> : null}
    </Pressable>
  );
}
