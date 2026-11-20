import { Camera, Images, Trash2, type LucideIcon } from 'lucide-react-native';
import { useState } from 'react';
import { Platform, Pressable, View } from 'react-native';

import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { Sheet } from '@/components/Sheet';
import { ErrorText, Text } from '@/components/ui';
import { pickPhotos } from '@/features/imports/pick';
import type { PickedFile } from '@/lib/api/upload';
import { useTheme } from '@/theme/useTheme';

/**
 * "Add photo" / "Change photo" on a Member's own recipe (ADR 0031), floating on its
 * picture: on the review screen and the recipe page. Opens a sheet to take or choose one.
 */
export function PhotoButton({
  hasPhoto,
  busy = false,
  onPicked,
  onRemove,
  style,
}: {
  hasPhoto: boolean;
  busy?: boolean;
  onPicked: (file: PickedFile) => void;
  onRemove: () => void;
  style?: object;
}) {
  const t = useTheme();
  const [open, setOpen] = useState(false);
  const label = busy ? 'Saving photo…' : hasPhoto ? 'Change photo' : 'Add photo';
  return (
    <>
      <PressableScale
        accessibilityRole="button"
        accessibilityLabel={label}
        accessibilityState={{ disabled: busy }}
        disabled={busy}
        onPress={() => setOpen(true)}
        style={[
          {
            flexDirection: 'row',
            alignItems: 'center',
            gap: 6,
            minHeight: t.touchTarget,
            paddingHorizontal: t.space.md,
            borderRadius: t.touchTarget / 2,
            backgroundColor: t.colors.surface,
            boxShadow: t.shadow.raised,
          },
          style,
        ]}
      >
        <Icon icon={Camera} size={18} color={t.colors.text} />
        <Text variant="label">{label}</Text>
      </PressableScale>
      {open ? (
        <PhotoSheet
          hasPhoto={hasPhoto}
          onClose={() => setOpen(false)}
          onPicked={(file) => {
            setOpen(false);
            onPicked(file);
          }}
          onRemove={() => {
            setOpen(false);
            onRemove();
          }}
        />
      ) : null}
    </>
  );
}

function PhotoSheet({
  hasPhoto,
  onPicked,
  onRemove,
  onClose,
}: {
  hasPhoto: boolean;
  onPicked: (file: PickedFile) => void;
  onRemove: () => void;
  onClose: () => void;
}) {
  const t = useTheme();
  const [error, setError] = useState<string | null>(null);

  async function take(camera: boolean) {
    setError(null);
    const picked = await pickPhotos({ camera, max: 1, tooMany: 'Pick one photo of the dish.' });
    if (picked.ok) onPicked(picked.value[0]);
    else setError(picked.error);
  }

  const choices: { key: string; icon: LucideIcon; title: string; onPress: () => void }[] = [
    // A browser has no camera picker worth offering: the library covers it.
    ...(Platform.OS === 'web'
      ? []
      : [{ key: 'camera', icon: Camera, title: 'Take a photo', onPress: () => take(true) }]),
    { key: 'library', icon: Images, title: 'Choose from library', onPress: () => take(false) },
    ...(hasPhoto
      ? [{ key: 'remove', icon: Trash2, title: 'Remove photo', onPress: onRemove }]
      : []),
  ];

  return (
    <Sheet label="Recipe photo" title="Recipe photo" onClose={onClose}>
      <View style={{ gap: t.space.xs }}>
        {choices.map((c) => (
          <Pressable
            key={c.key}
            accessibilityRole="button"
            onPress={c.onPress}
            style={({ pressed }) => ({
              minHeight: t.touchTarget + 8,
              flexDirection: 'row',
              alignItems: 'center',
              gap: t.space.md,
              opacity: pressed ? 0.6 : 1,
            })}
          >
            <Icon icon={c.icon} color={t.colors.text} />
            <Text variant="label">{c.title}</Text>
          </Pressable>
        ))}
        <Text variant="caption" muted>
          Only your Household sees it. Location and camera details are removed.
        </Text>
        <ErrorText message={error ?? undefined} />
      </View>
    </Sheet>
  );
}
