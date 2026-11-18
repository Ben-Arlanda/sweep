import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';

import { streamTurn } from '@/features/chat/sse';
import type { Plan } from '@/features/chat/starters';
import { startTurn, turnReducer, type Proposal, type Turn } from '@/features/chat/turn';
import { ApiError } from '@/lib/api/client';
import { conversationKeys, useConversation, useCreateConversation } from '@/lib/api/conversations';

/**
 * One planning Conversation on the plan screens (slice 6e, ADR 0025): the same
 * Conversation and Proposals as the chat, shown as screens instead of messages.
 *
 * While a turn streams we keep it locally (the reply, the tools called for the
 * checklist, the Proposal when it comes). When it ends we refetch the saved
 * Conversation, which is then the source: a swap or approval elsewhere shows up too.
 */
export function usePlanRun() {
  const queryClient = useQueryClient();
  const create = useCreateConversation();
  const [conversationId, setConversationId] = useState<string | null>(null);
  const saved = useConversation(conversationId);
  const [turn, setTurn] = useState<Turn | null>(null);
  const [tools, setTools] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  // Sweep's words from the last turn, shown as a note above the plan it came with (a
  // swap afterwards makes a new plan, whose own summary is the note then).
  const [reply, setReply] = useState<{ text: string; proposalId: string | null } | null>(null);
  const abort = useRef<AbortController | null>(null);
  const busy = turn?.status === 'streaming';

  // Leaving the screen mid-reply stops reading. The server saves what it had so far.
  useEffect(() => () => abort.current?.abort(), []);

  /** `plan` starts a new Conversation with it; without, the turn continues this one. */
  async function send(text: string, plan?: Plan | null) {
    const words = text.trim();
    if (!words || busy) return;
    setError(null);
    setTools([]);
    setTurn(startTurn(words));
    abort.current = new AbortController();
    let id = plan !== undefined ? null : conversationId;
    let failure: string | null = null;
    let replyText = '';
    try {
      if (id === null) {
        const made = await create.mutateAsync(plan ?? null);
        id = made.id;
        setConversationId(made.id);
      }
      await streamTurn(
        id,
        words,
        (event) => {
          if (event.type === 'error') failure = event.message;
          if (event.type === 'tool') {
            const name = event.name;
            setTools((seen) => [...seen, name]);
            replyText = ''; // text before a tool call was narration, not the reply
          }
          if (event.type === 'text') replyText += event.text;
          setTurn((current) => current && turnReducer(current, event));
        },
        abort.current.signal,
      );
    } catch (e) {
      if ((e as Error).name === 'AbortError') return;
      failure = e instanceof ApiError ? e.message : "Couldn't reach Sweep. Check your connection.";
    }
    if (id) await queryClient.refetchQueries({ queryKey: conversationKeys.one(id) });
    const now = id
      ? queryClient.getQueryData<{ proposal: Proposal | null }>(conversationKeys.one(id))
      : undefined;
    setReply(
      replyText.trim() ? { text: replyText.trim(), proposalId: now?.proposal?.id ?? null } : null,
    );
    setTurn((current) => current && { ...current, status: 'done', activity: null });
    setError(failure);
  }

  // The pending Proposal: the streaming one first, then the saved one.
  const proposal: Proposal | null =
    (busy ? turn?.proposal : null) ?? saved.data?.proposal ?? turn?.proposal ?? null;

  return {
    conversationId,
    send,
    busy,
    tools,
    turn,
    proposal,
    /** What Sweep said with this plan, if anything beyond its summary. */
    replyFor: (proposalId: string | null | undefined) =>
      reply && reply.proposalId === (proposalId ?? null) ? reply.text : null,
    error,
    loading: saved.isPending && conversationId !== null,
  };
}
