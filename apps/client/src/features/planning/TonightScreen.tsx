import { router, Stack } from 'expo-router';
import {
  ArrowUp,
  BookOpen,
  CalendarDays,
  Check,
  Clock,
  Ellipsis,
  Sparkles,
} from 'lucide-react-native';
import { useEffect, useState } from 'react';
import { ScrollView, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ChoiceChips } from '@/components/ChoiceChips';
import { HeartButton } from '@/components/HeartButton';
import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { RecipeArt } from '@/components/RecipeArt';
import { Sheet } from '@/components/Sheet';
import { Button, ErrorText, Text } from '@/components/ui';
import { allKept, decisionFor } from '@/features/chat/decision';
import { requestPlan } from '@/features/chat/starters';
import { PlanSheet } from '@/features/mealPlan/PlanSheet';
import { useDecideProposal } from '@/lib/api/conversations';
import { useMealPlan } from '@/lib/api/mealPlan';
import { useDinnerIdeas, type DinnerIdea, type IdeaFilter } from '@/lib/api/planning';
import { useTheme } from '@/theme/useTheme';

import { GeneratingView } from './GeneratingView';
import { stepsFor, TONIGHT_STEPS } from './steps';
import { usePlanRun } from './usePlanRun';

// The chef shows at least this long: the ideas come back in well under a second, and a
// flash of the Generating screen reads as a glitch (ADR 0025: a brief branded moment).
const MIN_CHEF_MS = 1200;
const STEP_MS = MIN_CHEF_MS / TONIGHT_STEPS.length;
const PAGE = 3;

const TWEAKS = ['Make it quicker', 'More vegetarian'];

/**
 * "Just tonight" (slice 6e, ADR 0025): Dinner Ideas chosen by code from the Kitchen and
 * Dietary Rules. Choosing one opens its recipe to plan it. Asking Sweep to tweak them
 * starts a Conversation, which answers here with one dinner to plan.
 */
export function TonightScreen() {
  const t = useTheme();
  const [filter, setFilter] = useState<IdeaFilter>('all');
  const [limit, setLimit] = useState(PAGE);
  const ideas = useDinnerIdeas(filter, limit);
  const today = useMealPlan(null).data?.today;
  const [elapsed, setElapsed] = useState(0);
  const run = usePlanRun();
  const decide = useDecideProposal(run.conversationId);
  const [showIdeas, setShowIdeas] = useState(true);
  const [menu, setMenu] = useState(false);
  const [planning, setPlanning] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => setElapsed((e) => e + STEP_MS), STEP_MS);
    return () => clearInterval(timer);
  }, []);
  const intro = elapsed < MIN_CHEF_MS || ideas.isPending;

  function tweak(text: string) {
    setShowIdeas(false);
    void run.send(`Dinner tonight: ${text}`, null);
  }

  function body() {
    if (intro) {
      const step = Math.min(Math.floor(elapsed / STEP_MS), TONIGHT_STEPS.length);
      const fake = ['get_kitchen', 'recipes_from_kitchen', 'propose_plan'].slice(0, step);
      return (
        <GeneratingView
          title="Finding your dinner ideas…"
          subtitle="Looking for meals that fit your Kitchen and your Dietary Rules."
          steps={stepsFor(TONIGHT_STEPS, fake, step >= TONIGHT_STEPS.length)}
        />
      );
    }
    if (run.busy) {
      return (
        <GeneratingView
          title="Asking Sweep…"
          subtitle="Sweep is finding a dinner for tonight."
          steps={stepsFor(TONIGHT_STEPS, run.tools, Boolean(run.turn?.proposal))}
        />
      );
    }
    const proposal = run.proposal?.status === 'pending' ? run.proposal : null;
    if (!showIdeas && (proposal || run.error || run.replyFor(null))) {
      return (
        <SweepsPick
          note={run.replyFor(proposal?.id) ?? proposal?.summary ?? null}
          error={run.error ?? decide.error?.message ?? null}
          title={proposal?.meals[0]?.title ?? null}
          recipeId={proposal?.meals[0]?.recipe_id ?? null}
          approving={decide.isPending}
          onPlan={() => {
            const decision = proposal && decisionFor(proposal, allKept());
            if (!proposal?.id || !decision) return;
            const title = proposal.meals[0]?.title ?? '';
            decide.mutate(
              { proposalId: proposal.id, decision },
              {
                onSuccess: () =>
                  router.replace({ pathname: '/planned', params: { kind: 'tonight', title } }),
              },
            );
          }}
          onBack={() => {
            // Leave Sweep's pick undecided: it expires by itself, and approving it later
            // from the conversation still works.
            setShowIdeas(true);
          }}
        />
      );
    }
    return (
      <Ideas
        ideas={ideas.data ?? []}
        error={ideas.error?.message ?? null}
        filter={filter}
        today={today ?? null}
        canMore={(ideas.data?.length ?? 0) >= limit && limit < 12}
        onFilter={(f) => {
          setFilter(f);
          setLimit(PAGE);
        }}
        onMore={() => setLimit((l) => l + PAGE)}
        onTweak={tweak}
      />
    );
  }

  return (
    <SafeAreaView
      edges={['left', 'right', 'bottom']}
      style={{ flex: 1, backgroundColor: t.colors.background }}
    >
      <Stack.Screen
        options={{
          title: 'Dinner tonight',
          headerRight: () => (
            <PressableScale
              accessibilityRole="button"
              accessibilityLabel="More options"
              onPress={() => setMenu(true)}
              style={{
                width: t.touchTarget,
                height: t.touchTarget,
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Icon icon={Ellipsis} color={t.colors.text} />
            </PressableScale>
          ),
        }}
      />
      {body()}
      {menu ? (
        <Sheet label="More options" title="More options" onClose={() => setMenu(false)}>
          <View style={{ gap: t.space.sm }}>
            <Button
              title="Plan my week instead"
              icon={CalendarDays}
              variant="secondary"
              onPress={() => {
                setMenu(false);
                setPlanning(true);
              }}
            />
            <Button
              title="Browse all recipes"
              icon={BookOpen}
              variant="secondary"
              onPress={() => {
                setMenu(false);
                router.push('/recipes');
              }}
            />
          </View>
        </Sheet>
      ) : null}
      {planning ? (
        <PlanSheet
          onClose={() => setPlanning(false)}
          onPick={(mode, days, tweaks) => {
            requestPlan(mode, days, tweaks);
            router.replace('/plan-week');
          }}
        />
      ) : null}
    </SafeAreaView>
  );
}

function IdeaMeta({ idea }: { idea: DinnerIdea }) {
  const t = useTheme();
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
      <Icon icon={Clock} size={15} color={t.colors.textMuted} />
      <Text variant="caption" muted style={{ flexShrink: 1 }}>
        {ideaMeta(idea)}
      </Text>
    </View>
  );
}

function ideaMeta(idea: DinnerIdea) {
  return [
    idea.total_minutes ? `${idea.total_minutes} min` : null,
    `Serves ${idea.servings}`,
    idea.missing.length ? `${idea.missing.length} to buy` : 'Nothing to buy',
  ]
    .filter(Boolean)
    .join(' · ');
}

function openRecipe(idea: DinnerIdea, today: string | null) {
  router.push({
    pathname: '/recipe/[id]',
    params: today ? { id: idea.id, plan: today } : { id: idea.id },
  });
}

function Ideas({
  ideas,
  error,
  filter,
  today,
  canMore,
  onFilter,
  onMore,
  onTweak,
}: {
  ideas: DinnerIdea[];
  error: string | null;
  filter: IdeaFilter;
  today: string | null;
  canMore: boolean;
  onFilter: (f: IdeaFilter) => void;
  onMore: () => void;
  onTweak: (text: string) => void;
}) {
  const t = useTheme();
  const [main, ...rest] = ideas;
  return (
    <ScrollView
      keyboardShouldPersistTaps="handled"
      contentContainerStyle={{
        padding: t.space.lg,
        gap: t.space.md,
        width: '100%',
        maxWidth: 560,
        alignSelf: 'center',
      }}
    >
      <View
        style={{
          flexDirection: 'row',
          gap: t.space.md,
          alignItems: 'center',
          backgroundColor: t.colors.actionSoft,
          borderRadius: t.radius.lg,
          padding: t.space.lg,
        }}
      >
        <Icon icon={Sparkles} color={t.colors.onActionSoft} />
        <View style={{ flex: 1 }}>
          <Text
            variant="heading"
            role="heading"
            aria-level={1}
            style={{ color: t.colors.onActionSoft }}
          >
            Here are some dinner ideas
          </Text>
          <Text variant="caption" style={{ color: t.colors.onActionSoft }}>
            Based on your Kitchen and Dietary Rules.
          </Text>
        </View>
      </View>

      <ChoiceChips
        label="Show"
        size="small"
        value={filter}
        options={[
          { label: 'All', value: 'all' as const },
          { label: 'Under 30 min', value: 'quick' as const },
          {
            label: 'Use my Kitchen',
            value: 'kitchen' as const,
            accessibilityLabel: 'Nothing to buy',
          },
        ]}
        onChange={onFilter}
      />
      <ErrorText message={error} />
      {!main && !error ? (
        <Text muted>No dinners fit that right now. Try another filter, or ask Sweep below.</Text>
      ) : null}

      {main ? (
        <View
          style={{
            backgroundColor: t.colors.surface,
            borderRadius: t.radius.lg,
            padding: t.space.sm,
            gap: t.space.sm,
            boxShadow: t.shadow.card,
          }}
        >
          <View>
            <RecipeArt
              title={main.title}
              width="100%"
              height={140}
              radius={t.radius.md}
              emojiSize={64}
            />
            {main.have.length > 0 ? (
              <View
                style={{
                  position: 'absolute',
                  left: t.space.sm,
                  bottom: t.space.sm,
                  flexDirection: 'row',
                  alignItems: 'center',
                  gap: 4,
                  backgroundColor: t.colors.surface,
                  borderRadius: t.radius.pill,
                  paddingHorizontal: t.space.md,
                  paddingVertical: 4,
                }}
              >
                <Icon icon={Check} size={14} color={t.colors.text} strong />
                <Text variant="caption">
                  Uses {main.have.length} Kitchen {main.have.length === 1 ? 'item' : 'items'}
                </Text>
              </View>
            ) : null}
            <View style={{ position: 'absolute', top: t.space.sm, right: t.space.sm }}>
              <HeartButton
                recipeId={main.id}
                title={main.title}
                favourite={main.favourite ?? false}
              />
            </View>
          </View>
          <View style={{ paddingHorizontal: t.space.sm, gap: 2 }}>
            <Text variant="heading">{main.title}</Text>
            <IdeaMeta idea={main} />
          </View>
          <Button
            title="Choose recipe →"
            accessibilityLabel={`Choose ${main.title}`}
            onPress={() => openRecipe(main, today)}
          />
        </View>
      ) : null}

      {rest.length > 0 ? (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}>
          {rest.map((idea) => (
            <View
              key={idea.id}
              style={{
                flexGrow: 1,
                flexBasis: 150,
                backgroundColor: t.colors.surface,
                borderRadius: t.radius.lg,
                padding: t.space.sm,
                gap: t.space.sm,
                boxShadow: t.shadow.card,
              }}
            >
              <RecipeArt title={idea.title} width="100%" height={76} radius={t.radius.md} />
              <View style={{ flex: 1, paddingHorizontal: 4 }}>
                <Text variant="label">{idea.title}</Text>
                <IdeaMeta idea={idea} />
              </View>
              <Button
                title="Choose"
                accessibilityLabel={`Choose ${idea.title}`}
                variant="secondary"
                onPress={() => openRecipe(idea, today)}
              />
            </View>
          ))}
        </View>
      ) : null}

      <TweakBox onSend={onTweak} />
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.sm }}>
        {TWEAKS.map((tw) => (
          <Button key={tw} title={tw} variant="secondary" compact onPress={() => onTweak(tw)} />
        ))}
        {canMore ? (
          <Button title="More ideas" variant="secondary" compact onPress={onMore} />
        ) : null}
      </View>
    </ScrollView>
  );
}

function TweakBox({ onSend }: { onSend: (text: string) => void }) {
  const t = useTheme();
  const [text, setText] = useState('');
  const canSend = text.trim().length > 0;
  const send = () => {
    if (!canSend) return;
    onSend(text);
    setText('');
  };
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.sm,
        minHeight: t.touchTarget + 8,
        paddingLeft: t.space.lg,
        paddingRight: t.space.xs,
        borderRadius: t.radius.pill,
        backgroundColor: t.colors.surface,
        borderWidth: 1,
        borderColor: t.colors.border,
      }}
    >
      <Icon icon={Sparkles} size={20} color={t.colors.text} />
      <TextInput
        accessibilityLabel="Ask Sweep to tweak these ideas"
        placeholder="Ask Sweep to tweak these ideas…"
        placeholderTextColor={t.colors.textMuted}
        value={text}
        onChangeText={setText}
        maxLength={2000}
        returnKeyType="send"
        onSubmitEditing={send}
        style={[t.type.body, { flex: 1, minHeight: t.touchTarget, color: t.colors.text }]}
      />
      <PressableScale
        accessibilityRole="button"
        accessibilityLabel="Send to Sweep"
        accessibilityState={{ disabled: !canSend }}
        disabled={!canSend}
        onPress={send}
        style={{
          width: t.touchTarget,
          height: t.touchTarget,
          borderRadius: t.radius.pill,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: canSend ? t.colors.inverse : t.colors.border,
        }}
      >
        <Icon
          icon={ArrowUp}
          size={20}
          color={canSend ? t.colors.onInverse : t.colors.text}
          strong
        />
      </PressableScale>
    </View>
  );
}

function SweepsPick({
  note,
  error,
  title,
  recipeId,
  approving,
  onPlan,
  onBack,
}: {
  note: string | null;
  error: string | null;
  title: string | null;
  recipeId: string | null;
  approving: boolean;
  onPlan: () => void;
  onBack: () => void;
}) {
  const t = useTheme();
  return (
    <ScrollView
      contentContainerStyle={{
        padding: t.space.lg,
        gap: t.space.md,
        width: '100%',
        maxWidth: 560,
        alignSelf: 'center',
      }}
    >
      {note ? (
        <View
          accessibilityLiveRegion="polite"
          style={{
            flexDirection: 'row',
            gap: t.space.md,
            backgroundColor: t.colors.actionSoft,
            borderRadius: t.radius.lg,
            padding: t.space.lg,
          }}
        >
          <Icon icon={Sparkles} color={t.colors.onActionSoft} />
          <Text style={{ flex: 1, color: t.colors.onActionSoft }}>{note}</Text>
        </View>
      ) : null}
      {title && recipeId ? (
        <PressableScale
          accessibilityRole="link"
          accessibilityLabel={`${title}. See the recipe`}
          onPress={() => router.push(`/recipe/${recipeId}`)}
          style={{
            backgroundColor: t.colors.surface,
            borderRadius: t.radius.lg,
            padding: t.space.sm,
            gap: t.space.sm,
            boxShadow: t.shadow.card,
          }}
        >
          <RecipeArt title={title} width="100%" height={140} radius={t.radius.md} emojiSize={64} />
          <Text variant="heading" style={{ paddingHorizontal: t.space.sm }}>
            {title}
          </Text>
        </PressableScale>
      ) : null}
      <View accessibilityLiveRegion="polite">
        <ErrorText message={error} />
      </View>
      {title ? <Button title="Plan for tonight" loading={approving} onPress={onPlan} /> : null}
      <Button title="Back to ideas" variant="secondary" onPress={onBack} />
    </ScrollView>
  );
}
