import { useQueryClient } from '@tanstack/react-query';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import {
  AccessibilityInfo,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  View,
  type ScrollViewInstance,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { PressableScale } from '@/components/PressableScale';
import { Button, ErrorText, Field, Loading, Text } from '@/components/ui';
import { ApiError } from '@/lib/api/client';
import {
  conversationKeys,
  useConversation,
  useConversations,
  useCreateConversation,
} from '@/lib/api/conversations';
import { useTheme } from '@/theme/useTheme';

import { DraftPeek, ProposalCard } from './ProposalCard';
import { streamTurn, type TurnEvent } from './sse';
import { starterMessage, SUGGESTIONS } from './starters';
import { startTurn, turnReducer, type Turn } from './turn';

/**
 * Chatting with the agent. Two kinds of state live here:
 * - the saved Conversation (transcript + latest Proposal), from the server via TanStack
 *   Query, so it's the same on every device;
 * - the turn that's streaming right now, local to this screen. When it ends we refetch
 *   the saved Conversation and drop the local copy, so the server stays the source.
 */
export function ChatScreen() {
  const t = useTheme();
  const queryClient = useQueryClient();
  const list = useConversations();
  const create = useCreateConversation();

  // undefined: follow the newest Conversation. null: "New plan" (made on first send).
  const [chosen, setChosen] = useState<string | null | undefined>(undefined);
  const conversationId = chosen === undefined ? (list.data?.[0]?.id ?? null) : chosen;
  const saved = useConversation(conversationId);

  const [turn, setTurn] = useState<Turn | null>(null);
  const [input, setInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null);
  const scroll = useRef<ScrollViewInstance>(null);
  const busy = turn?.status === 'streaming';

  // Leaving the screen mid-reply stops reading. The server saves what it had so far.
  useEffect(() => () => abort.current?.abort(), []);

  // Home's "Plan my week" / "Just tonight" (ADR 0013): a new plan with a fixed first
  // message. The ref makes it once per visit, even if React runs effects twice; clearing
  // the param means going back or reloading doesn't send it again.
  const { start } = useLocalSearchParams<{ start?: string }>();
  const started = useRef(false);
  const ready = !list.isPending;
  useEffect(() => {
    const words = starterMessage(start);
    if (!ready || !words || started.current) return;
    started.current = true;
    router.setParams({ start: undefined });
    setChosen(null);
    void send(words, { fresh: true });
    // send is recreated every render; this should run only when `start` arrives.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, start]);

  /** `fresh`: start a new plan, even though the screen still shows the last one. */
  async function send(text: string, opts: { fresh?: boolean } = {}) {
    const words = text.trim();
    if (!words || busy) return;
    setInput('');
    setError(null);
    setTurn(startTurn(words));
    abort.current = new AbortController();

    const result = await runTurn({
      conversationId: opts.fresh ? null : conversationId,
      words,
      signal: abort.current.signal,
      createConversation: async () => {
        const made = await create.mutateAsync();
        setChosen(made.id);
        queryClient.setQueryData(conversationKeys.list, (old: (typeof made)[] | undefined) => [
          made,
          ...(old ?? []),
        ]);
        return made.id;
      },
      onEvent: (event) => setTurn((current) => current && turnReducer(current, event)),
    });
    if (result.aborted) return;

    const { id, failure } = result;
    if (id) await queryClient.refetchQueries({ queryKey: conversationKeys.one(id) });
    const refreshed = id ? queryClient.getQueryState(conversationKeys.one(id)) : undefined;
    // Keep the live copy if we couldn't load the saved one, so the reply doesn't vanish.
    if (refreshed?.status === 'success') setTurn(null);
    else setTurn((current) => current && { ...current, status: 'done', activity: null });

    if (failure) {
      setError(failure);
      setInput((now) => now || words); // give them their words back to try again
    } else {
      announce('Sweep replied.');
    }
  }

  function newPlan() {
    if (busy) return;
    setChosen(null);
    setTurn(null);
    setError(null);
  }

  if (list.isPending) return <Loading />;

  const messages = conversationId ? (saved.data?.messages ?? []) : [];
  const proposal = turn ? turn.proposal : (saved.data?.proposal ?? null);
  const empty = messages.length === 0 && !turn;

  return (
    <SafeAreaView
      edges={['left', 'right', 'bottom']}
      style={{ flex: 1, backgroundColor: t.colors.background }}
    >
      <Stack.Screen
        options={{
          title: 'Plan my week',
          headerRight: () =>
            empty ? null : (
              <Button title="New plan" variant="ghost" compact onPress={newPlan} disabled={busy} />
            ),
        }}
      />
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 100 : 0}
      >
        <ScrollView
          ref={scroll}
          keyboardShouldPersistTaps="handled"
          onContentSizeChange={() => scroll.current?.scrollToEnd({ animated: true })}
          contentContainerStyle={{
            padding: t.space.lg,
            gap: t.space.md,
            width: '100%',
            maxWidth: 560,
            alignSelf: 'center',
          }}
        >
          {saved.isError ? <ErrorText message={saved.error.message} /> : null}
          {empty ? <Welcome onPick={send} /> : null}

          {messages.map((m, i) => (
            <Bubble key={i} role={m.role} text={m.text} />
          ))}

          {turn ? (
            <>
              <Bubble role="user" text={turn.userText} />
              {turn.reply ? <Bubble role="assistant" text={turn.reply} /> : null}
              {busy && !turn.proposal && turn.draft ? <DraftPeek draft={turn.draft} /> : null}
            </>
          ) : null}

          {proposal ? <ProposalCard proposal={proposal} /> : null}

          {/* Only the status is a live region: reading out every streamed word would
              swamp a screen reader. The finished reply is announced once instead. */}
          <View accessibilityLiveRegion="polite">
            {busy && turn?.activity ? (
              <Status activity={turn.activity} narration={turn.narration} />
            ) : null}
          </View>
        </ScrollView>

        <View
          style={{
            padding: t.space.md,
            gap: t.space.sm,
            borderTopWidth: 1,
            borderTopColor: t.colors.border,
            backgroundColor: t.colors.surface,
          }}
        >
          <View style={{ width: '100%', maxWidth: 560, alignSelf: 'center', gap: t.space.sm }}>
            <View accessibilityLiveRegion="assertive">
              {error ? <ErrorText message={error} /> : null}
            </View>
            <Field
              label="Message Sweep"
              hideLabel
              placeholder="Ask for a plan, or change one"
              value={input}
              onChangeText={setInput}
              maxLength={2000}
              multiline
              editable={!busy}
              onSubmitEditing={() => send(input)}
              submitBehavior="submit"
              returnKeyType="send"
            />
            <Button
              title={busy ? 'Sweep is working…' : 'Send'}
              onPress={() => send(input)}
              disabled={!input.trim()}
              loading={busy}
            />
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

/**
 * The network side of one turn, outside the component: make the Conversation if this
 * is the first message, then stream the reply. Returns what happened instead of
 * changing anything, so the screen decides what to show.
 */
async function runTurn(opts: {
  conversationId: string | null;
  words: string;
  signal: AbortSignal;
  createConversation: () => Promise<string>;
  onEvent: (event: TurnEvent) => void;
}): Promise<{ aborted: true } | { aborted: false; id: string | null; failure: string | null }> {
  let id = opts.conversationId;
  let failure: string | null = null;
  try {
    id ??= await opts.createConversation();
    await streamTurn(
      id,
      opts.words,
      (event) => {
        if (event.type === 'error') failure = event.message;
        opts.onEvent(event);
      },
      opts.signal,
    );
  } catch (e) {
    if ((e as Error).name === 'AbortError') return { aborted: true };
    failure = e instanceof ApiError ? e.message : "Couldn't reach Sweep. Check your connection.";
  }
  return { aborted: false, id, failure };
}

function announce(message: string) {
  // iOS has no live regions, so say it directly. Android and web use the regions above.
  if (Platform.OS === 'ios') AccessibilityInfo.announceForAccessibility(message);
}

function Welcome({ onPick }: { onPick: (text: string) => void }) {
  const t = useTheme();
  return (
    <View style={{ gap: t.space.md }}>
      <Text variant="title" role="heading" aria-level={2}>
        What should we cook?
      </Text>
      <Text muted>
        Sweep plans meals from its recipes, follows your Dietary Rules and checks your Kitchen.
        Nothing changes until you approve it.
      </Text>
      <View style={{ gap: t.space.sm }}>
        {SUGGESTIONS.map((s) => (
          <PressableScale
            key={s}
            accessibilityRole="button"
            onPress={() => onPick(s)}
            style={{
              minHeight: t.touchTarget,
              justifyContent: 'center',
              paddingHorizontal: t.space.lg,
              paddingVertical: t.space.sm,
              borderRadius: t.radius.md,
              borderWidth: 1.5,
              borderColor: t.colors.border,
              backgroundColor: t.colors.surface,
            }}
          >
            <Text>{s}</Text>
          </PressableScale>
        ))}
      </View>
    </View>
  );
}

function Bubble({ role, text }: { role: 'user' | 'assistant'; text: string }) {
  const t = useTheme();
  const mine = role === 'user';
  return (
    <View
      accessible
      accessibilityLabel={`${mine ? 'You' : 'Sweep'}: ${text}`}
      style={{
        alignSelf: mine ? 'flex-end' : 'flex-start',
        maxWidth: '88%',
        paddingHorizontal: t.space.lg,
        paddingVertical: t.space.md,
        borderRadius: t.radius.lg,
        backgroundColor: mine ? t.colors.inverse : t.colors.surface,
        boxShadow: mine ? undefined : t.shadow.card,
      }}
    >
      <Text style={mine ? { color: t.colors.onInverse } : undefined}>{text}</Text>
    </View>
  );
}

function Status({ activity, narration }: { activity: string; narration: string | null }) {
  const t = useTheme();
  return (
    <View style={{ flexDirection: 'row', gap: t.space.sm, alignItems: 'flex-start' }}>
      <ActivityIndicator color={t.colors.textMuted} aria-hidden />
      <View style={{ flexShrink: 1, gap: 2 }}>
        <Text muted>{activity}…</Text>
        {narration ? (
          <Text variant="caption" muted>
            {narration}
          </Text>
        ) : null}
      </View>
    </View>
  );
}
