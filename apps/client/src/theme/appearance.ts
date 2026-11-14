/**
 * Which theme the app uses: Sweep is dark by default, and anyone can switch to light
 * or to "match my phone".
 *
 * The choice lives in a tiny store outside React, so every `useTheme()` in the app
 * reads the same value and re-renders together when it changes. `useSyncExternalStore`
 * is React's built-in way to subscribe a component to a store like this.
 *
 * It's saved to device storage. Reading storage is async, so the very first frame uses
 * the default (dark); someone who picked light sees it a moment later.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useSyncExternalStore } from 'react';

export type Appearance = 'dark' | 'light' | 'system';

export const DEFAULT_APPEARANCE: Appearance = 'dark';
const KEY = 'sweep.appearance';

let current: Appearance = DEFAULT_APPEARANCE;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function isAppearance(value: unknown): value is Appearance {
  return value === 'dark' || value === 'light' || value === 'system';
}

/** Load the saved choice once, at startup. A missing or broken value keeps the default. */
export async function loadAppearance() {
  try {
    const saved = await AsyncStorage.getItem(KEY);
    if (isAppearance(saved) && saved !== current) {
      current = saved;
      emit();
    }
  } catch {
    // Storage unavailable (e.g. a private browser window): just use the default.
  }
}

export function setAppearance(next: Appearance) {
  current = next;
  emit();
  AsyncStorage.setItem(KEY, next).catch(() => {}); // the change still applies this session
}

export function useAppearance(): Appearance {
  return useSyncExternalStore(subscribe, () => current);
}
