import { View } from 'react-native';

import { Card, Text } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

import { formatAddition, formatDay } from './format';
import type { Draft, Proposal } from './turn';

/**
 * The plan the agent is asking you to approve. Read-only for now: approving or
 * rejecting it (and so changing the Meal Plan and Shopping List) arrives in slice 6.
 */
export function ProposalCard({ proposal }: { proposal: Proposal }) {
  const t = useTheme();
  return (
    <Card>
      <Text variant="heading" role="heading" aria-level={2}>
        Sweep&apos;s plan
      </Text>
      <Text>{proposal.summary}</Text>

      {proposal.meals.length > 0 ? (
        <Section title="Meals">
          {proposal.meals.map((meal) => (
            <Row
              key={meal.date}
              left={formatDay(meal.date)}
              right={`${meal.title} · serves ${meal.servings}`}
            />
          ))}
        </Section>
      ) : null}

      {proposal.list_additions.length > 0 ? (
        <Section title="Add to the Shopping List">
          {proposal.list_additions.map((item) => (
            <Text key={item.name}>{formatAddition(item)}</Text>
          ))}
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

      <View style={{ gap: t.space.xs }}>
        <Text variant="caption" muted>
          Nothing in your Household has changed. Approving a plan is coming soon.
        </Text>
        <Text variant="caption" muted>
          Always check labels for allergens. Sweep can make mistakes.
        </Text>
      </View>
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
