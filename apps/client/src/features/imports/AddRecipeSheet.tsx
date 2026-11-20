import { router } from 'expo-router';
import {
  Camera,
  ChevronLeft,
  ClipboardPaste,
  FileText,
  Link2,
  PenLine,
  type LucideIcon,
} from 'lucide-react-native';
import { useEffect, useRef, useState } from 'react';
import { Pressable, View } from 'react-native';

import { Icon } from '@/components/Icon';
import { Sheet } from '@/components/Sheet';
import { PressableScale } from '@/components/PressableScale';
import { Button, ErrorText, Field, Text } from '@/components/ui';
import { useReadRecipe, type Door } from '@/lib/api/imports';
import { useTheme } from '@/theme/useTheme';

import { keepDraft } from './drafts';
import { pickPdf, pickPhotos } from './pick';

type View_ = 'doors' | 'paste' | 'link';

const DOORS: {
  key: 'paste' | 'photo' | 'link' | 'file' | 'type';
  icon: LucideIcon;
  title: string;
  hint: string;
}[] = [
  {
    key: 'paste',
    icon: ClipboardPaste,
    title: 'Paste text',
    hint: 'From a website, a message or notes',
  },
  { key: 'photo', icon: Camera, title: 'Photos', hint: 'Up to 3 pages of a cookbook or a card' },
  { key: 'link', icon: Link2, title: 'Link', hint: 'A recipe page on the web' },
  { key: 'file', icon: FileText, title: 'PDF', hint: 'A saved or printed recipe' },
  { key: 'type', icon: PenLine, title: 'Type it in', hint: 'Start from a blank recipe' },
];

/**
 * "+ Add" on the Recipes tab: the ways a recipe comes in. Every one ends on the same
 * review screen, and nothing is saved until the Member taps Save there.
 */
export function AddRecipeSheet({ onClose }: { onClose: () => void }) {
  const t = useTheme();
  const [view, setView] = useState<View_>('doors');
  const [text, setText] = useState('');
  const [url, setUrl] = useState('');
  const [pickError, setPickError] = useState<string | null>(null);
  const read = useReadRecipe();

  // Closing the sheet while a read is running means "never mind": don't jump to review.
  const open = useRef(true);
  useEffect(
    () => () => {
      open.current = false;
    },
    [],
  );

  async function readAndReview(input: Door) {
    setPickError(null);
    try {
      const draft = await read.mutateAsync(input);
      if (!open.current) return;
      const id = keepDraft(draft);
      onClose();
      router.push({ pathname: '/recipes/review', params: { draft: id } });
    } catch {
      // read.error has the server's message, shown below
    }
  }

  async function openDoor(key: (typeof DOORS)[number]['key']) {
    read.reset();
    setPickError(null);
    if (key === 'paste' || key === 'link') return setView(key);
    if (key === 'type') {
      onClose();
      router.push('/recipes/review');
      return;
    }
    if (key === 'photo') {
      const photos = await pickPhotos();
      if (!photos.ok) return setPickError(photos.error); // null: they cancelled
      return readAndReview({ door: 'photo', photos: photos.value });
    }
    const file = await pickPdf();
    if (!file.ok) return setPickError(file.error);
    return readAndReview({ door: 'file', file: file.value });
  }

  const error = pickError ?? read.error?.message ?? null;
  const reading = read.isPending;

  return (
    <Sheet
      label="Add a recipe"
      title={
        view === 'paste' ? 'Paste a recipe' : view === 'link' ? 'Add from a link' : 'Add a recipe'
      }
      onClose={onClose}
    >
      {view === 'doors' ? (
        <View style={{ gap: t.space.xs }}>
          {DOORS.map((d) => (
            <Pressable
              key={d.key}
              accessibilityRole="button"
              accessibilityLabel={`${d.title}. ${d.hint}`}
              accessibilityState={{ disabled: reading }}
              disabled={reading}
              onPress={() => openDoor(d.key)}
              style={({ pressed }) => ({
                minHeight: t.touchTarget + 8,
                flexDirection: 'row',
                alignItems: 'center',
                gap: t.space.md,
                opacity: pressed || reading ? 0.6 : 1,
              })}
            >
              <Icon icon={d.icon} color={t.colors.text} />
              <View style={{ flex: 1 }}>
                <Text variant="label">{d.title}</Text>
                <Text variant="caption" muted>
                  {d.hint}
                </Text>
              </View>
            </Pressable>
          ))}
          {reading ? (
            <Text accessibilityLiveRegion="polite" aria-live="polite">
              Reading your recipe…
            </Text>
          ) : null}
        </View>
      ) : (
        <View style={{ gap: t.space.md }}>
          {view === 'paste' ? (
            <>
              <Text variant="caption" muted>
                Paste the whole recipe: ingredients and method. Sweep reads it and you check it
                before anything is saved.
              </Text>
              <Field
                label="Recipe text"
                value={text}
                onChangeText={setText}
                multiline
                maxLength={20_000}
                textAlignVertical="top"
                style={{ minHeight: 180, paddingTop: t.space.md }}
              />
            </>
          ) : (
            <>
              <Text variant="caption" muted>
                Sweep keeps the ingredients and a link to the page, so the method stays on the site
                that wrote it.
              </Text>
              <Field
                label="Recipe link"
                placeholder="https://"
                value={url}
                onChangeText={setUrl}
                keyboardType="url"
                autoCapitalize="none"
                autoCorrect={false}
                maxLength={2048}
              />
            </>
          )}
          <Button
            title={view === 'paste' ? 'Read recipe' : 'Get recipe'}
            loading={reading}
            disabled={view === 'paste' ? !text.trim() : !url.trim()}
            onPress={() =>
              readAndReview(
                view === 'paste' ? { door: 'paste', text } : { door: 'link', url: url.trim() },
              )
            }
          />
          <PressableScale
            accessibilityRole="button"
            onPress={() => {
              read.reset();
              setView('doors');
            }}
            style={{
              minHeight: t.touchTarget,
              flexDirection: 'row',
              alignItems: 'center',
              gap: t.space.xs,
            }}
          >
            <Icon icon={ChevronLeft} color={t.colors.text} size={18} />
            <Text variant="label">Other ways to add</Text>
          </PressableScale>
        </View>
      )}
      <ErrorText message={error} />
    </Sheet>
  );
}
