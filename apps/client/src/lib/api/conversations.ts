/**
 * Conversations with the agent. The server keeps them (messages, Draft Plan, Proposal),
 * so a chat started on the phone carries on in the browser.
 *
 * Sending a message isn't here: it streams, so it goes through features/chat/sse.ts.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api, unwrap } from './client';
import { listKeys } from './lists';
import { mealPlanKeys } from './mealPlan';
import type { components } from './schema';
import { haptic } from '@/lib/haptics';

type Decision = components['schemas']['DecisionIn'];

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
    // `plan` from the "Plan my week" sheet: the kind of plan and the days (ADR 0015).
    mutationFn: async (plan: components['schemas']['ConversationIn'] | null) =>
      unwrap(await api.POST('/conversations', { body: plan ?? {} })),
  });
}

/**
 * Approve or reject a Proposal. No Idempotency-Key: the Proposal id does that job on the
 * server (a repeated Approve returns the stored outcome, ADR 0014). And no automatic
 * retry: approving resumes the agent, so if it fails we show why and let them tap again.
 *
 * Afterwards everything approving can touch is refetched: the Conversation (the card's
 * new status and outcome), the Meal Plan and the Shopping List.
 */
export function useDecideProposal(conversationId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (v: { proposalId: string; decision: Decision }) =>
      unwrap(
        await api.POST('/proposals/{proposal_id}/decision', {
          params: { path: { proposal_id: v.proposalId } },
          body: v.decision,
        }),
      ),
    onSuccess: (_, v) => {
      if (v.decision.action === 'approve') haptic.success();
    },
    onSettled: async () => {
      await Promise.all([
        conversationId
          ? queryClient.invalidateQueries({ queryKey: conversationKeys.one(conversationId) })
          : null,
        queryClient.invalidateQueries({ queryKey: mealPlanKeys.all }),
        queryClient.invalidateQueries({ queryKey: listKeys.all }),
      ]);
    },
  });
}
