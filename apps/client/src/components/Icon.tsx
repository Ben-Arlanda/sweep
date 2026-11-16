import type { LucideIcon } from 'lucide-react-native';
import { View } from 'react-native';

import { iconStroke } from '@/theme/tokens';

/**
 * Every icon in the app goes through here, so they all share one line weight. Icons are
 * decorative: the words next to them say what they mean, so screen readers skip them.
 */
export function Icon({
  icon: Glyph,
  size = 22,
  color,
  strong = false,
}: {
  icon: LucideIcon;
  size?: number;
  color: string;
  /** The heavier line, for a selected state. */
  strong?: boolean;
}) {
  // Hidden on the wrapping View: React Native maps aria-hidden to each platform's own
  // setting, while the SVG underneath would pass unknown props straight to the web DOM.
  return (
    <View aria-hidden>
      <Glyph
        size={size}
        color={color}
        strokeWidth={strong ? iconStroke.strong : iconStroke.regular}
      />
    </View>
  );
}
