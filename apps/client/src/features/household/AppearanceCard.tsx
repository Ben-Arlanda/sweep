import { ChoiceChips } from '@/components/ChoiceChips';
import { Card, Text } from '@/components/ui';
import { setAppearance, useAppearance, type Appearance } from '@/theme/appearance';

const OPTIONS: { label: string; value: Appearance }[] = [
  { label: 'Dark', value: 'dark' },
  { label: 'Light', value: 'light' },
  { label: 'Match my phone', value: 'system' },
];

/** Dark (the default), light, or follow the phone's setting. Saved on this device. */
export function AppearanceCard() {
  const appearance = useAppearance();
  return (
    <Card>
      <Text variant="heading">Appearance</Text>
      <ChoiceChips
        label="Appearance"
        options={OPTIONS}
        value={appearance}
        onChange={setAppearance}
      />
    </Card>
  );
}
