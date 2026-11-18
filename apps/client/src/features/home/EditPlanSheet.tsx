import { ChevronRight, Pencil, Trash2, type LucideIcon } from 'lucide-react-native';
import { View } from 'react-native';

import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { Sheet } from '@/components/Sheet';
import { Text } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

/**
 * "Edit plan" on Home, once the week is planned: change it on the Plan tab, or clear
 * it and plan again. The screen that opens this does both (Start fresh asks first).
 */
export function EditPlanSheet({
  onEdit,
  onStartFresh,
  onClose,
}: {
  onEdit: () => void;
  onStartFresh: () => void;
  onClose: () => void;
}) {
  const t = useTheme();
  return (
    <Sheet label="Edit your meal plan" title="Edit your meal plan" onClose={onClose}>
      <View style={{ gap: t.space.sm }}>
        <Option
          icon={Pencil}
          title="Edit this week"
          hint="Swap, change or add meals"
          highlight
          onPress={onEdit}
        />
        <Option
          icon={Trash2}
          title="Start fresh"
          hint="Clear this week and plan again"
          onPress={onStartFresh}
        />
      </View>
    </Sheet>
  );
}

function Option({
  icon,
  title,
  hint,
  highlight,
  onPress,
}: {
  icon: LucideIcon;
  title: string;
  hint: string;
  highlight?: boolean;
  onPress: () => void;
}) {
  const t = useTheme();
  return (
    <PressableScale
      accessibilityRole="button"
      accessibilityLabel={`${title}: ${hint}`}
      onPress={onPress}
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.md,
        minHeight: 68,
        paddingHorizontal: t.space.md,
        borderRadius: t.radius.lg,
        backgroundColor: highlight ? t.colors.actionSoft : t.colors.surface,
        boxShadow: highlight ? undefined : t.shadow.card,
      }}
    >
      <Icon icon={icon} size={24} color={t.colors.text} />
      <View style={{ flex: 1 }}>
        <Text variant="label">{title}</Text>
        <Text
          variant="caption"
          style={{ color: highlight ? t.colors.onActionSoft : t.colors.textMuted }}
        >
          {hint}
        </Text>
      </View>
      <Icon icon={ChevronRight} size={20} color={t.colors.text} strong />
    </PressableScale>
  );
}
