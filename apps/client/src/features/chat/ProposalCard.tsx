import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { Checkbox } from '@/components/Checkbox';
import { Button, Card, ErrorText, Text } from '@/components/ui';
import { adaptedTitle, swapLine } from '@/features/recipes/adaptations';
import { useDecideProposal } from '@/lib/api/conversations';
import { useTheme } from '@/theme/useTheme';

import {
  allKept,
  decisionFor,
  isAdditionKept,
  isMealKept,
  keptCount,
  toggleAddition,
  toggleMeal,
  type Ticks,
} from './decision';
import { additionLine, formatDay } from './format';
import { keptOf, statusLine } from './history';
import type { Draft, Proposal } from './turn';

/**
 * The plan the agent is asking you to approve. While it's pending, every meal and list
 * addition has a tick: untick what you don't want, then Approve (ADR 0014). Approving
 * is plain code on the server, no LLM call, and its outcome message replaces the buttons.
 *
 * `disabled` while a turn is still streaming: the graph only pauses for a decision once
 * the turn has finished.
 */
export function ProposalCard({
  proposal,
  conversationId,
  disabled,
}: {
  proposal: Proposal;
  conversationId: string | null;
  disabled?: boolean;
}) {
  const t = useTheme();
  const [ticks, setTicks] = useState<Ticks>(allKept);
  const decide = useDecideProposal(conversationId);
  const pending = proposal.status === 'pending';
  const decision = decisionFor(proposal, ticks);
  const kept = keptCount(proposal, ticks);
  // Once decided, the rows show what was kept (no ticks); while pending, everything.
  const shown = keptOf(proposal);
  const canAct = pending && Boolean(proposal.id) && !disabled && !decide.isPending;

  function send(action: 'approve' | 'reject') {
    if (!proposal.id) return;
    const body = action === 'reject' ? { action } : decision;
    if (!body) return;
    decide.mutate({ proposalId: proposal.id, decision: body });
  }

  return (
    <Card>
      <Text variant="heading" role="heading" aria-level={2}>
        Sweep&apos;s plan
      </Text>
      <Text>{proposal.summary}</Text>

      {shown.meals.length > 0 ? (
        <Section title="Meals">
          {shown.meals.map((meal) => {
            const day = formatDay(meal.date);
            const what = `${adaptedTitle(meal)} · serves ${meal.servings}`;
            const replaces = meal.replaces ? `Replaces ${meal.replaces}` : null;
            // One tick approves the Adaptation as a whole, so its Swaps sit in the row.
            const swaps = meal.adaptation?.swaps.map(swapLine) ?? [];
            return (
              <TickRow
                key={meal.date}
                ticked={pending ? isMealKept(ticks, meal.date) : null}
                disabled={!canAct}
                onToggle={() => setTicks((now) => toggleMeal(now, meal.date))}
                label={[day, what, ...swaps, replaces].filter(Boolean).join(', ')}
              >
                <Text variant="label" style={{ minWidth: 92 }}>
                  {day}
                </Text>
                <View style={{ flexShrink: 1 }}>
                  <Text>{what}</Text>
                  {swaps.map((line) => (
                    <Text key={line} variant="caption">
                      {line}
                    </Text>
                  ))}
                  {replaces ? (
                    <Text variant="caption" muted>
                      {replaces}
                    </Text>
                  ) : null}
                </View>
              </TickRow>
            );
          })}
        </Section>
      ) : null}

      {shown.additions.length > 0 ? (
        <Section title={pending ? 'Add to the Shopping List' : 'For the Shopping List'}>
          {shown.additions.map(({ item, index: i }) => {
            // Flagged while pending: no meal needs it and the Member didn't ask (slice 10).
            const flag = pending && item.reason === 'unexplained' ? 'Not for any meal' : null;
            return (
              <TickRow
                // Positions are what the server keeps, and names can repeat.
                key={i}
                ticked={pending ? isAdditionKept(proposal, ticks, i) : null}
                disabled={!canAct}
                onToggle={() => setTicks((now) => toggleAddition(now, i))}
                label={[additionLine(item), flag].filter(Boolean).join(', ')}
              >
                <View style={{ flexShrink: 1 }}>
                  <Text>{additionLine(item)}</Text>
                  {flag ? (
                    <Text variant="caption" muted>
                      {flag}
                    </Text>
                  ) : null}
                </View>
              </TickRow>
            );
          })}
        </Section>
      ) : null}

      {proposal.dropped.length > 0 ? (
        <Section title="Left out">
          {proposal.dropped.map((reason) => (
            <Text key={reason} muted>
              {reason}
            </Text>
          ))}
        </Section>
      ) : null}

      {proposal.check_label.length > 0 ? (
        <Section title="Check the label">
          {proposal.check_label.map((line) => (
            <Text key={line}>{line}</Text>
          ))}
        </Section>
      ) : null}

      {/* The result is announced: after tapping Approve, focus stays on a button that
          has just gone, so a screen reader user needs telling what happened. */}
      <View accessibilityLiveRegion="polite" style={{ gap: t.space.xs }}>
        {pending ? null : <Text variant="label">{statusLine(proposal)}</Text>}
        {proposal.outcome ? <Text>{proposal.outcome.message}</Text> : null}
        {proposal.outcome?.topped_up?.map((line) => (
          <Text key={line} variant="caption" muted>
            Topped up {line}
          </Text>
        ))}
        {/* The message says "Skipped N: see below", so each reason goes here. */}
        {proposal.outcome?.skipped.map((reason) => (
          <Text key={reason} variant="caption" muted>
            {reason}
          </Text>
        ))}
        <ErrorText message={decide.error?.message} />
      </View>

      {pending ? (
        <View style={{ gap: t.space.sm }}>
          <Text variant="caption" muted>
            {decision ? `Approving adds ${keptSummary(kept)}.` : 'Tick something to approve.'}{' '}
            Nothing changes until you approve.
          </Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}>
            <Button
              title="Approve"
              accessibilityLabel={decision ? `Approve ${keptSummary(kept)}` : 'Approve'}
              onPress={() => send('approve')}
              disabled={!canAct || !decision}
              loading={decide.isPending && decide.variables?.decision.action === 'approve'}
              compact
            />
            <Button
              title="Reject"
              variant="secondary"
              onPress={() => send('reject')}
              disabled={!canAct}
              loading={decide.isPending && decide.variables?.decision.action === 'reject'}
              compact
            />
          </View>
        </View>
      ) : null}

      <Text variant="caption" muted>
        Always check labels for allergens. Sweep can make mistakes.
      </Text>
    </Card>
  );
}

function keptSummary(kept: { meals: number; additions: number }) {
  const parts = [
    kept.meals > 0 ? `${kept.meals} ${kept.meals === 1 ? 'meal' : 'meals'}` : null,
    kept.additions > 0
      ? `${kept.additions} ${kept.additions === 1 ? 'item' : 'items'} to the list`
      : null,
  ].filter(Boolean);
  return parts.join(' and ');
}

/** An earlier plan in the chat history: one line saying what became of it. */
export function PastProposal({ proposal }: { proposal: Proposal }) {
  const meals = keptOf(proposal).meals.map(adaptedTitle).join(', ');
  return (
    <Card style={{ gap: 4 }}>
      <Text variant="label">Sweep&apos;s plan · {statusLine(proposal)}</Text>
      {meals ? (
        <Text muted numberOfLines={2}>
          {meals}
        </Text>
      ) : null}
      {proposal.outcome?.skipped.length ? (
        <Text variant="caption" muted>
          {proposal.outcome.message}
        </Text>
      ) : null}
    </Card>
  );
}

/** The plan as it grows during a turn, before it's a Proposal. */
export function DraftPeek({ draft }: { draft: Draft }) {
  const meals = Object.entries(draft.meals).sort(([a], [b]) => a.localeCompare(b));
  if (meals.length === 0) return null;
  return (
    <Card>
      <Text variant="label">Plan so far</Text>
      {meals.map(([day, meal]) => (
        <Row key={day} left={formatDay(day)} right={meal.title ?? 'A recipe'} />
      ))}
    </Card>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  const t = useTheme();
  return (
    <View style={{ gap: t.space.xs }}>
      <Text variant="label">{title}</Text>
      {children}
    </View>
  );
}

/**
 * A row with a tick while the plan is pending (`ticked` true/false), or a plain row once
 * it's decided (`ticked` null). The whole row is the checkbox, so the target is big.
 */
function TickRow({
  ticked,
  disabled,
  onToggle,
  label,
  children,
}: {
  ticked: boolean | null;
  disabled: boolean;
  onToggle: () => void;
  label: string;
  children: React.ReactNode;
}) {
  const t = useTheme();
  const rowStyle = {
    flexDirection: 'row' as const,
    flexWrap: 'wrap' as const, // wraps instead of squeezing at 320px wide (WCAG reflow)
    alignItems: 'center' as const,
    columnGap: t.space.md,
  };
  if (ticked === null) return <View style={rowStyle}>{children}</View>;
  return (
    <Pressable
      accessibilityRole="checkbox"
      accessibilityLabel={label}
      accessibilityState={{ checked: ticked, disabled }}
      aria-checked={ticked}
      disabled={disabled}
      onPress={onToggle}
      style={{ ...rowStyle, minHeight: t.touchTarget, flexWrap: 'nowrap' }}
    >
      <Checkbox checked={ticked} size={24} />
      <View style={[rowStyle, { flexShrink: 1 }]}>{children}</View>
    </Pressable>
  );
}

function Row({ left, right }: { left: string; right: string }) {
  const t = useTheme();
  // Wraps instead of squeezing at 320px wide (WCAG reflow).
  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', columnGap: t.space.md }}>
      <Text variant="label" style={{ minWidth: 92 }}>
        {left}
      </Text>
      <Text style={{ flexShrink: 1 }}>{right}</Text>
    </View>
  );
}
