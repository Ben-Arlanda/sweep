/**
 * Adding a picked photo or PDF to a FormData body, on web and on a phone.
 *
 * On a phone, Expo 58 makes `expo/fetch` the global fetch. It sends a file part only if
 * it has `.bytes()`, so the file goes in as expo-file-system's `File`. React Native's old
 * `{ uri, name, type }` trick throws "Unsupported FormDataPart implementation" there.
 * A browser's FormData needs the real bytes, fetched from the `blob:` or `data:` URL.
 */
import { File as DeviceFile } from 'expo-file-system';
import { Platform } from 'react-native';

/** A picked photo or PDF: where it is on the device, and what it is. */
export type PickedFile = { uri: string; name: string; type: string };

export async function appendFile(form: FormData, field: string, file: PickedFile) {
  if (Platform.OS === 'web') {
    const blob = await (await fetch(file.uri)).blob();
    form.append(field, new File([blob], file.name, { type: file.type }));
  } else {
    form.append(field, new DeviceFile(file.uri) as unknown as Blob);
  }
}
