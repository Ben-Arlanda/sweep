import * as Haptics from 'expo-haptics';
import { Platform } from 'react-native';

/** Fire and forget: a phone without a motor (or the web) just stays still. */
function run(feel: () => Promise<void>) {
  if (Platform.OS === 'web') return;
  feel().catch(() => {});
}

/**
 * Sweep's few haptic feels, kept light so they mean something. The phone's own settings
 * (e.g. iOS "System Haptics" off) silence them.
 */
export const haptic = {
  /** Ticking an item, hearting, the next Cook Mode step. */
  tap: () => run(() => Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light)),
  /** A swipe passing the point where letting go removes the row. */
  threshold: () => run(() => Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium)),
  /** Cooked, planned, saved. */
  success: () => run(() => Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success)),
  /** Something didn't save. */
  error: () => run(() => Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error)),
  /** Changing a segmented control or chip. */
  select: () => run(() => Haptics.selectionAsync()),
};
