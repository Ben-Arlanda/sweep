import { MealPlanScreen } from '@/features/mealPlan/MealPlanScreen';
import { PageColors } from '@/theme/PageColors';

/** The Plan tab: this week's and next week's dinners (ADR 0026), on its page colour. */
export default function MealPlanTab() {
  return (
    <PageColors page="plan">
      <MealPlanScreen />
    </PageColors>
  );
}
