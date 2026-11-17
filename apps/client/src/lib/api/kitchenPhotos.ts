/**
 * Kitchen Photos (slice 3e, ADR 0023): read photos into rows, then apply the ticked ones.
 *
 * Reading is one model call that counts toward the Member's 20 an hour, so it never
 * retries by itself. Applying is a normal Kitchen change: an Idempotency-Key made at tap
 * time, so a retry on a flaky connection can't add anything twice.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { api, ApiError, unwrap } from './client';
import { kitchenKeys } from './kitchen';
import type { components } from './schema';
import { appendFile, type PickedFile } from './upload';

type Place = components['schemas']['Place'];
export type KitchenPhotoRead = components['schemas']['KitchenPhotoOut'];
type ApplyIn = components['schemas']['KitchenPhotoApplyIn'];

// openapi-fetch would turn the body into JSON; FormData must go as it is.
const asIs = (body: unknown) => body as BodyInit;

export function useReadKitchenPhotos() {
  return useMutation({
    retry: false,
    mutationFn: async ({ place, photos }: { place: Place; photos: PickedFile[] }) => {
      const form = new FormData();
      form.append('place', place);
      for (const photo of photos) await appendFile(form, 'photos', photo);
      return unwrap(
        await api.POST('/kitchen/photos', { body: form as never, bodySerializer: asIs }),
      );
    },
  });
}

export function useApplyKitchenPhotos() {
  const queryClient = useQueryClient();
  return useMutation({
    retry: (failures, error) => !(error instanceof ApiError && error.status < 500) && failures < 3,
    onSettled: () => queryClient.invalidateQueries({ queryKey: kitchenKeys.all }),
    mutationFn: async ({ body, idempotencyKey }: { body: ApplyIn; idempotencyKey: string }) =>
      unwrap(
        await api.POST('/kitchen/photos/apply', {
          params: { header: { 'Idempotency-Key': idempotencyKey } },
          body,
        }),
      ),
  });
}
