/**
 * Picking photos and a PDF for the Photo and File doors.
 *
 * Photos are shrunk on the phone before upload: a phone photo is often 4,000 px and
 * 5+ MB, while the model reads a recipe page fine at 1,600 px. Smaller is faster on a
 * supermarket's patchy signal, costs fewer tokens, and stays under the server's 5 MB
 * limit. Saving as JPEG also turns an iPhone's HEIC into something the server accepts.
 * The decisions are pure functions (tested); the picking itself is the platform's.
 */
import * as DocumentPicker from 'expo-document-picker';
import { ImageManipulator, SaveFormat } from 'expo-image-manipulator';
import * as ImagePicker from 'expo-image-picker';

import type { PickedFile } from '@/lib/api/imports';

export const MAX_PHOTOS = 3;
const LONGEST_SIDE = 1600;
const MAX_PDF_BYTES = 10_000_000;

export function resizeFor(width: number, height: number) {
  if (Math.max(width, height) <= LONGEST_SIDE) return null;
  return width >= height ? { width: LONGEST_SIDE } : { height: LONGEST_SIDE };
}

const TOO_MANY = 'Up to 3 photos, one recipe. Pick the pages again.';

export function checkPhotoCount(n: number, tooMany = TOO_MANY): string | null {
  return n > MAX_PHOTOS ? tooMany : null;
}

export function checkPdf(file: { name: string; mimeType?: string; size?: number }): string | null {
  const isPdf = file.mimeType === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
  if (!isPdf) return 'Sweep reads PDFs only. For a Word or text file, paste the recipe text.';
  if ((file.size ?? 0) > MAX_PDF_BYTES) {
    return 'That PDF is over 10 MB. Try a smaller copy, or paste the recipe text.';
  }
  return null;
}

export type Picked<T> = { ok: true; value: T } | { ok: false; error: string | null }; // null: cancelled

type PickOptions = { camera?: boolean; tooMany?: string };

/**
 * Up to 3 photos from the library, in the order picked, or one from the camera; each
 * shrunk to JPEG. Recipes use the library (cookbook pages); the Kitchen offers both.
 */
export async function pickPhotos({ camera = false, tooMany = TOO_MANY }: PickOptions = {}): Promise<
  Picked<PickedFile[]>
> {
  if (camera) {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      return {
        ok: false,
        error: 'Sweep needs the camera for this. You can choose photos instead.',
      };
    }
  }
  const result = camera
    ? await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: 1 })
    : await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        allowsMultipleSelection: true,
        selectionLimit: MAX_PHOTOS, // the web picker can't enforce this, hence checkPhotoCount
        orderedSelection: true,
        quality: 1, // compressed once, below
      });
  if (result.canceled) return { ok: false, error: null };
  const problem = checkPhotoCount(result.assets.length, tooMany);
  if (problem) return { ok: false, error: problem };

  const photos: PickedFile[] = [];
  for (const [i, asset] of result.assets.entries()) {
    const context = ImageManipulator.manipulate(asset.uri);
    const size = resizeFor(asset.width, asset.height);
    if (size) context.resize(size);
    const image = await (
      await context.renderAsync()
    ).saveAsync({
      format: SaveFormat.JPEG,
      compress: 0.8,
    });
    photos.push({ uri: image.uri, name: `page-${i + 1}.jpg`, type: 'image/jpeg' });
  }
  return { ok: true, value: photos };
}

/** One PDF. */
export async function pickPdf(): Promise<Picked<PickedFile>> {
  const result = await DocumentPicker.getDocumentAsync({
    type: 'application/pdf',
    copyToCacheDirectory: true, // so the upload can read it
  });
  if (result.canceled) return { ok: false, error: null };
  const asset = result.assets[0];
  const problem = checkPdf(asset);
  if (problem) return { ok: false, error: problem };
  return { ok: true, value: { uri: asset.uri, name: asset.name, type: 'application/pdf' } };
}
