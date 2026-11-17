// The phone's FormData, as Expo 58 sets it up (React Native's, patched by Expo), and the
// code expo/fetch runs on it before sending. Jest's own FormData is Node's, not these.
import { convertFormDataAsync } from 'expo/src/winter/fetch/convertFormData';

import { appendFile } from './upload';

// A stand-in for expo-file-system's File: what expo/fetch needs is `.bytes()`.
jest.mock('expo-file-system', () => ({
  File: class {
    uri: string;
    name = 'photo.jpg';
    type = 'image/jpeg';
    constructor(uri: string) {
      this.uri = uri;
    }
    async bytes() {
      return new Uint8Array([0xff, 0xd8, 0xff]);
    }
  },
}));

const RNFormData = jest.requireActual('react-native/Libraries/Network/FormData');
const { installFormDataPatch } = jest.requireActual('expo/src/winter/FormData');
const PhoneFormData: typeof FormData = installFormDataPatch(RNFormData.default ?? RNFormData);

const PHOTO = { uri: 'file:///cache/photo.jpg', name: 'photo.jpg', type: 'image/jpeg' };

describe('appendFile on a phone', () => {
  it('builds a body expo/fetch can send (Expo 58 made it the global fetch)', async () => {
    const form = new PhoneFormData();
    await appendFile(form, 'photos', PHOTO);

    const { body } = await convertFormDataAsync(form, 'b');

    const text = new TextDecoder().decode(body);
    expect(text).toContain('name="photos"; filename="photo.jpg"');
    expect(text).toContain('content-type: image/jpeg');
  });

  it("the old React Native { uri, name, type } part is what expo/fetch can't send", async () => {
    const form = new PhoneFormData();
    form.append('photos', PHOTO as unknown as Blob);

    await expect(convertFormDataAsync(form, 'b')).rejects.toThrow(
      'Unsupported FormDataPart implementation',
    );
  });
});
