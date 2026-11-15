import { ErrorText } from '@/components/ui';
import { Tile } from '@/components/Tile';
import { useMealPlan } from '@/lib/api/mealPlan';

/** Home board tile into the Meal Plan: how many dinners are planned this week. */
export function MealPlanTile() {
  const week = useMealPlan(null);
  const meals = week.data?.meals ?? [];
  const left = meals.filter((m) => m.cooked_at === null).length;
  const subtitle = !week.data
    ? undefined
    : meals.length === 0
      ? 'Nothing planned yet'
      : `${meals.length} ${meals.length === 1 ? 'dinner' : 'dinners'} this week · ${left} to cook`;
  return (
    <>
      <Tile href="/meal-plan" tint="lilac" emoji="🗓️" title="Meal Plan" subtitle={subtitle} />
      <ErrorText message={week.error?.message} />
    </>
  );
}
