/**
 * The Kitchen's last filter chip (All / Fridge / Freezer / Cupboard), remembered on this
 * device. Per device, not per Household: it's a habit of whoever holds the phone.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useEffect, useState } from 'react';

import { isPlaceFilter, type PlaceFilter } from './places';

const KEY = 'sweep.kitchenFilter';

export function usePlaceFilter(): [PlaceFilter, (next: PlaceFilter) => void] {
  const [filter, setFilter] = useState<PlaceFilter>('all');

  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then((saved) => {
        if (isPlaceFilter(saved)) setFilter(saved);
      })
      .catch(() => {}); // storage unavailable (private window): start on "All"
  }, []);

  function remember(next: PlaceFilter) {
    setFilter(next);
    AsyncStorage.setItem(KEY, next).catch(() => {});
  }

  return [filter, remember];
}
