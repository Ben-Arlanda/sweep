import { Minus, Plus } from 'lucide-react-native';
import { View } from 'react-native';

import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { Text } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

/** The database allows 1 to 20 servings on a Planned Meal. */
export const MAX_SERVES = 20;

/** "Serves  − 4 +": a pill with the number between two 44pt buttons. */
export function ServesStepper({
  value,
  onChange,
  disabled = false,
}: {
  value: number;
  onChange: (serves: number) => void;
  disabled?: boolean;
}) {
  const t = useTheme();
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        borderRadius: t.radius.pill,
        borderWidth: 1,
        borderColor: t.colors.border,
        backgroundColor: t.colors.surface,
      }}
    >
      <Step
        icon={Minus}
        label="Fewer people"
        disabled={disabled || value <= 1}
        onPress={() => onChange(value - 1)}
      />
      <Text
        variant="label"
        accessibilityLiveRegion="polite"
        accessibilityLabel={`Serves ${value}`}
        style={{ minWidth: 28, textAlign: 'center', fontVariant: ['tabular-nums'] }}
      >
        {value}
      </Text>
      <Step
        icon={Plus}
        label="More people"
        disabled={disabled || value >= MAX_SERVES}
        onPress={() => onChange(value + 1)}
      />
    </View>
  );
}

function Step({
  icon,
  label,
  disabled,
  onPress,
}: {
  icon: typeof Plus;
  label: string;
  disabled: boolean;
  onPress: () => void;
}) {
  const t = useTheme();
  return (
    <PressableScale
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={onPress}
      style={{
        width: t.touchTarget,
        height: t.touchTarget,
        alignItems: 'center',
        justifyContent: 'center',
        opacity: disabled ? 0.4 : 1,
      }}
    >
      <Icon icon={icon} size={20} color={t.colors.text} />
    </PressableScale>
  );
}
