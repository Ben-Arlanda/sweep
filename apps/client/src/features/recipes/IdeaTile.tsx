import { router } from 'expo-router';
import { Check, Clock } from 'lucide-react-native';
import { View } from 'react-native';

import { HeartButton } from '@/components/HeartButton';
import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { RecipeArt } from '@/components/RecipeArt';
import { Text } from '@/components/ui';
import type { DinnerIdea } from '@/lib/api/planning';
import { useTheme } from '@/theme/useTheme';

/** Dinner Ideas ranked by the Kitchen alone: Home's and Recipes' "for you" cards. */
export const KITCHEN_FIRST = {
  mood: 'kitchen',
  q: '',
  lean: null,
  maxMinutes: null,
  serves: null,
} as const;

/**
 * A recipe card with its Kitchen Match: "✓ Uses 4 Kitchen items" when nothing's
 * missing, else "2 to buy". `path` keeps Back working: the Recipes tab opens it in its
 * own stack, Home opens the root recipe screen.
 */
export function IdeaTile({
  idea,
  path,
}: {
  idea: DinnerIdea;
  path: '/recipes/[id]' | '/recipe/[id]';
}) {
  const t = useTheme();
  const ready = idea.missing.length === 0;
  const uses = `Uses ${idea.have.length} Kitchen ${idea.have.length === 1 ? 'item' : 'items'}`;
  const meta = [idea.total_minutes ? `${idea.total_minutes} min` : null, `Serves ${idea.servings}`]
    .filter(Boolean)
    .join(' · ');
  return (
    <View
      style={{
        flexGrow: 1,
        flexBasis: 140,
        backgroundColor: t.colors.surface,
        borderRadius: t.radius.lg,
        overflow: 'hidden',
        boxShadow: t.shadow.card,
      }}
    >
      <PressableScale
        accessibilityRole="link"
        accessibilityLabel={`${idea.title}. ${meta}. ${ready ? uses : `${idea.missing.length} to buy`}`}
        onPress={() => router.push({ pathname: path, params: { id: idea.id } })}
      >
        <View>
          <RecipeArt
            title={idea.title}
            image={idea.image}
            width="100%"
            height={104}
            radius={0}
            emojiSize={48}
          />
          <View
            style={{
              position: 'absolute',
              left: t.space.sm,
              right: t.space.sm,
              bottom: t.space.sm,
              alignSelf: 'flex-start',
              flexDirection: 'row',
            }}
          >
            <View
              style={{
                flexDirection: 'row',
                alignItems: 'center',
                gap: 2,
                backgroundColor: ready ? t.stock.in_stock.bg : t.colors.surface,
                borderRadius: t.radius.pill,
                paddingHorizontal: t.space.sm,
                paddingVertical: 2,
              }}
            >
              {ready ? <Icon icon={Check} size={12} color={t.stock.in_stock.fg} strong /> : null}
              <Text
                variant="caption"
                numberOfLines={1}
                style={{ color: ready ? t.stock.in_stock.fg : t.colors.text }}
              >
                {ready ? uses : `${idea.missing.length} to buy`}
              </Text>
            </View>
          </View>
        </View>
        <View style={{ padding: t.space.sm, gap: 2 }}>
          <Text variant="label">{idea.title}</Text>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
            <Icon icon={Clock} size={13} color={t.colors.textMuted} />
            <Text variant="caption" muted>
              {meta}
            </Text>
          </View>
        </View>
      </PressableScale>
      <View style={{ position: 'absolute', top: t.space.xs, right: t.space.xs }}>
        <HeartButton recipeId={idea.id} title={idea.title} favourite={idea.favourite ?? false} />
      </View>
    </View>
  );
}
