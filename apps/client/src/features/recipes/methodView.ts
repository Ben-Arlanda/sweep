/**
 * Detailed or Quick, remembered on this device (ADR 0028). Per device, like the Kitchen
 * filter: it's a habit of whoever is cooking. Detailed until someone picks Quick.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useEffect, useState } from 'react';

import { isMethodView, type MethodView } from './method';

const KEY = 'sweep.methodView';

export function useMethodView(): [MethodView, (next: MethodView) => void] {
  const [view, setView] = useState<MethodView>('detailed');

  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then((saved) => {
        if (isMethodView(saved)) setView(saved);
      })
      .catch(() => {}); // storage unavailable (private window): start on Detailed
  }, []);

  function remember(next: MethodView) {
    setView(next);
    AsyncStorage.setItem(KEY, next).catch(() => {});
  }

  return [view, remember];
}
