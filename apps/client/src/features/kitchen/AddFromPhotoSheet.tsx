import { router } from 'expo-router';
import { Camera, Images, type LucideIcon } from 'lucide-react-native';
import { useEffect, useRef, useState } from 'react';
import { Pressable, View } from 'react-native';

import { ChoiceChips } from '@/components/ChoiceChips';
import { Icon } from '@/components/Icon';
import { Sheet } from '@/components/Sheet';
import { ErrorText, Text } from '@/components/ui';
import { pickPhotos } from '@/features/imports/pick';
import { useReadKitchenPhotos } from '@/lib/api/kitchenPhotos';
import { useTheme } from '@/theme/useTheme';

import { keepPhotoRead } from './photoDrafts';
import { PLACES, type Place } from './places';

const TOO_MANY = 'Up to 3 photos at a time, all from one place. Pick again.';

/**
 * "Add from photo" on the Kitchen (ADR 0023): say where the things came from, then take
 * or choose photos of them laid out. Sweep reads them and the review screen shows what
 * it saw; nothing changes until the Member taps Add there.
 */
export function AddFromPhotoSheet({ start, onClose }: { start: Place; onClose: () => void }) {
  const t = useTheme();
  const [place, setPlace] = useState<Place>(start);
  const [pickError, setPickError] = useState<string | null>(null);
  const read = useReadKitchenPhotos();

  // Closing the sheet while Sweep is reading means "never mind": don't jump to review.
  const open = useRef(true);
  useEffect(
    () => () => {
      open.current = false;
    },
    [],
  );

  async function take(camera: boolean) {
    read.reset();
    setPickError(null);
    const photos = await pickPhotos({ camera, tooMany: TOO_MANY });
    if (!photos.ok) return setPickError(photos.error); // null: they cancelled
    try {
      const result = await read.mutateAsync({ place, photos: photos.value });
      if (!open.current) return;
      const id = keepPhotoRead(result);
      onClose();
      router.push({ pathname: '/kitchen-photos', params: { read: id } });
    } catch {
      // read.error has the server's message, shown below
    }
  }

  const reading = read.isPending;
  const choices: { camera: boolean; icon: LucideIcon; title: string; hint: string }[] = [
    { camera: true, icon: Camera, title: 'Take a photo', hint: 'Lay things out with labels up' },
    { camera: false, icon: Images, title: 'Choose photos', hint: 'Up to 3 from your library' },
  ];

  return (
    <Sheet label="Add from photo" title="Add from photo" onClose={onClose}>
      <View style={{ gap: t.space.md }}>
        <Text variant="label" aria-hidden>
          Where did these come from?
        </Text>
        <ChoiceChips<Place>
          label="Where did these come from?"
          value={place}
          onChange={setPlace}
          options={PLACES.map(({ place: value, label }) => ({ label, value }))}
        />
        <View style={{ gap: t.space.xs }}>
          {choices.map((c) => (
            <Pressable
              key={c.title}
              accessibilityRole="button"
              accessibilityLabel={`${c.title}. ${c.hint}`}
              accessibilityState={{ disabled: reading }}
              disabled={reading}
              onPress={() => take(c.camera)}
              style={({ pressed }) => ({
                minHeight: t.touchTarget + 8,
                flexDirection: 'row',
                alignItems: 'center',
                gap: t.space.md,
                opacity: pressed || reading ? 0.6 : 1,
              })}
            >
              <Icon icon={c.icon} color={t.colors.text} />
              <View style={{ flex: 1 }}>
                <Text variant="label">{c.title}</Text>
                <Text variant="caption" muted>
                  {c.hint}
                </Text>
              </View>
            </Pressable>
          ))}
        </View>
        {reading ? (
          <Text accessibilityLiveRegion="polite" aria-live="polite">
            Looking at your photos…
          </Text>
        ) : null}
        <ErrorText message={pickError ?? read.error?.message} />
      </View>
    </Sheet>
  );
}
