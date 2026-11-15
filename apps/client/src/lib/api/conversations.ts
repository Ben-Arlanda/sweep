/**
 * Conversations with the agent. The server keeps them (messages, Draft Plan, Proposal),
 * so a chat started on the phone carries on in the browser.
 *
 * Sending a message isn't here: it streams, so it goes through features/chat/sse.ts.
 */
import { useMutation, useQuery } from '@tanstack/react-query';

import { api, unwrap } from './client';

export const conversationKeys = {
  all: ['conversations'] as const,
  list: ['conversations', 'list'] as const,
  one: (id: string) => ['conversations', 'one', id] as const,
};

/** The Member's own Conversations, newest first. The chat reopens the first one. */
export function useConversations() {
  return useQuery({
    queryKey: conversationKeys.list,
    queryFn: async () => unwrap(await api.GET('/conversations')),
  });
}

/** The transcript, the Draft Plan and the latest Proposal. */
export function useConversation(id: string | null) {
  return useQuery({
    queryKey: conversationKeys.one(id ?? ''),
    queryFn: async () =>
      unwrap(
        await api.GET('/conversations/{conversation_id}', {
          params: { path: { conversation_id: id ?? '' } },
        }),
      ),
    enabled: id !== null,
  });
}

/**
 * Made when the Member sends their first message, not when the screen opens, so just
 * looking doesn't leave empty Conversations behind.
 */
export function useCreateConversation() {
  return useMutation({
    mutationFn: async () => unwrap(await api.POST('/conversations')),
  });
}
