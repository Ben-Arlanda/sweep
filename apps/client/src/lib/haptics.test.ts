import * as Haptics from 'expo-haptics';
import { Platform } from 'react-native';

import { haptic } from './haptics';

jest.mock('expo-haptics', () => ({
  impactAsync: jest.fn(() => Promise.resolve()),
  notificationAsync: jest.fn(() => Promise.resolve()),
  selectionAsync: jest.fn(() => Promise.resolve()),
  ImpactFeedbackStyle: { Light: 'light', Medium: 'medium' },
  NotificationFeedbackType: { Success: 'success', Error: 'error' },
}));

beforeEach(() => jest.clearAllMocks());

test('each moment has one restrained feel', () => {
  Platform.OS = 'ios';
  haptic.tap();
  haptic.threshold();
  haptic.success();
  haptic.error();
  haptic.select();
  expect(Haptics.impactAsync).toHaveBeenNthCalledWith(1, 'light');
  expect(Haptics.impactAsync).toHaveBeenNthCalledWith(2, 'medium');
  expect(Haptics.notificationAsync).toHaveBeenNthCalledWith(1, 'success');
  expect(Haptics.notificationAsync).toHaveBeenNthCalledWith(2, 'error');
  expect(Haptics.selectionAsync).toHaveBeenCalledTimes(1);
});

test('the web has no haptics, so nothing is called', () => {
  Platform.OS = 'web';
  haptic.tap();
  haptic.success();
  expect(Haptics.impactAsync).not.toHaveBeenCalled();
  expect(Haptics.notificationAsync).not.toHaveBeenCalled();
});

test('a phone that refuses never breaks the tap', async () => {
  Platform.OS = 'android';
  jest.mocked(Haptics.impactAsync).mockRejectedValueOnce(new Error('no motor'));
  expect(() => haptic.tap()).not.toThrow();
  await Promise.resolve();
});
