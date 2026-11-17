import { router, useLocalSearchParams } from 'expo-router';

import { Button, Screen, Text } from '@/components/ui';
import { KitchenPhotoReview } from '@/features/kitchen/KitchenPhotoReview';
import { findPhotoRead } from '@/features/kitchen/photoDrafts';

/** The Kitchen Photo review (ADR 0023), opened from "Add from photo" on the Kitchen. */
export default function KitchenPhotosRoute() {
  const { read: id } = useLocalSearchParams<{ read?: string }>();
  const read = findPhotoRead(id);
  if (!read) {
    // Kept in memory only, so a reload loses it: say so and offer the way back.
    return (
      <Screen>
        <Text>Those photos aren&apos;t here any more. Take them again from your Kitchen.</Text>
        <Button title="Back to Kitchen" onPress={() => router.replace('/kitchen')} />
      </Screen>
    );
  }
  return <KitchenPhotoReview read={read} />;
}
