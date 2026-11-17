import { useQueryClient } from '@tanstack/react-query';
import { Stack } from 'expo-router';
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

import { placeProposals } from './history';
import { replyBlocks, type Span } from './reply';
import { DraftPeek, PastProposal, ProposalCard } from './ProposalCard';
import { streamTurn, type TurnEvent } from './sse';
import { PlanSheet } from '@/features/mealPlan/PlanSheet';

import { planMessage, SUGGESTIONS, takeStart, type Plan } from './starters';
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

  // Home's "Plan my week" sheet (ADR 0015) or "Just tonight" (ADR 0013): a new plan
  // with a first message, and from the sheet a mode and days. takeStart() hands it over
  // once, so a reload never re-sends (a paid call).
  const [planning, setPlanning] = useState(false);
  const ready = !list.isPending;
  useEffect(() => {
    if (!ready) return;
    const start = takeStart();
    if (start) void send(start.text, { fresh: true, plan: start.plan });
    // send is recreated every render; this should run once, when the list is ready.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);

  /**
   * `fresh`: start a new plan, even though the screen still shows the last one.
   * `plan`: the sheet's mode and days, saved on the new Conversation.
   */
  async function send(text: string, opts: { fresh?: boolean; plan?: Plan | null } = {}) {
    const words = text.trim();
    if (!words || busy) return;
    if (opts.fresh) setChosen(null); // show the new plan, not the last one
    setInput('');
    setError(null);
    setTurn(startTurn(words));
    abort.current = new AbortController();

    const result = await runTurn({
      conversationId: opts.fresh ? null : conversationId,
      words,
      signal: abort.current.signal,
      createConversation: async () => {
        const made = await create.mutateAsync(opts.plan ?? null);
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
  // Every Proposal back where it happened in the chat (6a); only a pending one can be
  // decided, earlier ones shrink to a line saying what became of them.
  const proposals = conversationId ? (saved.data?.proposals ?? []) : [];
  const history = placeProposals(messages, proposals);
  // The newest plan stays a full card after it's decided, so its outcome shows there
  // (and is announced); older ones shrink to a line.
  const newest = turn?.proposal ? null : proposals.at(-1);
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
          {empty ? <Welcome onPick={send} onPlanWeek={() => setPlanning(true)} /> : null}

          {history.map((item) =>
            item.kind === 'line' ? (
              <Bubble key={`line-${item.index}`} role={item.line.role} text={item.line.text} />
            ) : item.proposal.status === 'pending' || item.proposal === newest ? (
              <ProposalCard
                key={item.proposal.id ?? 'pending'}
                proposal={item.proposal}
                conversationId={conversationId}
                disabled={busy}
              />
            ) : (
              <PastProposal key={item.proposal.id ?? 'past'} proposal={item.proposal} />
            ),
          )}

          {turn ? (
            <>
              <Bubble role="user" text={turn.userText} />
              {turn.reply ? <Bubble role="assistant" text={turn.reply} /> : null}
              {busy && !turn.proposal && turn.draft ? <DraftPeek draft={turn.draft} /> : null}
              {turn.proposal ? (
                <ProposalCard
                  proposal={turn.proposal}
                  conversationId={conversationId}
                  disabled={busy}
                />
              ) : null}
            </>
          ) : null}

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
      {planning ? (
        <PlanSheet
          onClose={() => setPlanning(false)}
          onPick={(mode, days) =>
            void send(planMessage(mode, days), { fresh: true, plan: { mode, days } })
          }
        />
      ) : null}
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

function Welcome({
  onPick,
  onPlanWeek,
}: {
  onPick: (text: string) => void;
  onPlanWeek: () => void;
}) {
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
      <Button title="Plan my week" onPress={onPlanWeek} />
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
      accessibilityLabel={`${mine ? 'You' : 'Sweep'}: ${mine ? text : text.replaceAll('**', '')}`}
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
      {mine ? <Text style={{ color: t.colors.onInverse }}>{text}</Text> : <Reply text={text} />}
    </View>
  );
}

function Reply({ text }: { text: string }) {
  const t = useTheme();
  const line = (spans: Span[]) =>
    spans.map((s, i) => (
      <Text key={i} style={s.bold ? { fontFamily: t.fonts.bold } : undefined}>
        {s.text}
      </Text>
    ));
  return (
    <View style={{ gap: t.space.sm }}>
      {replyBlocks(text).map((block, i) =>
        block.kind === 'text' ? (
          <Text key={i}>{line(block.spans)}</Text>
        ) : (
          <View key={i} style={{ flexDirection: 'row', gap: t.space.sm }}>
            <Text style={{ fontFamily: t.fonts.bold, minWidth: 18 }}>
              {block.marker === '•' ? '•' : `${block.marker}.`}
            </Text>
            <Text style={{ flex: 1 }}>{line(block.spans)}</Text>
          </View>
        ),
      )}
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
