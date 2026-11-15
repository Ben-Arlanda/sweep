/**
 * The Shop chosen under the add box, remembered on this device, so adding five Aldi
 * items in a row needs no extra taps. Per device, not per Household: it's a habit of
 * whoever's holding the phone, not shared data.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useEffect, useState } from 'react';

const KEY = 'sweep.lastShop';

export function useLastShop(): [string | null, (shopId: string | null) => void] {
  const [shopId, setShopId] = useState<string | null>(null);

  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then((saved) => {
        if (saved) setShopId(saved);
      })
      .catch(() => {}); // storage unavailable (private window): start with "any shop"
  }, []);

  function remember(next: string | null) {
    setShopId(next);
    const write = next ? AsyncStorage.setItem(KEY, next) : AsyncStorage.removeItem(KEY);
    write.catch(() => {});
  }

  return [shopId, remember];
}
