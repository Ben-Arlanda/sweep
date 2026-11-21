/**
 * The words on the welcome screens, kept apart from the layout so they're easy to
 * review and change. Design: direction A "Clean Slate" on the onboarding canvas
 * (2026-11-21). Every page shows a feature that exists today.
 */
export const LANDING = {
  title: "Cook what you've got.",
  highlight: "Buy only what's missing.",
  lede: 'Sweep tracks your Kitchen, suggests dinners from what you have, plans your week and writes the shopping list for you.',
} as const;

export type StoryKey = 'snap' | 'ideas' | 'recipes' | 'plan' | 'list' | 'sync';

export type StoryPage = {
  key: StoryKey;
  title: string;
  /** Words on a lime highlight after the title (the last page's "One app."). */
  highlight?: string;
  body: string;
};

export const STORY: StoryPage[] = [
  {
    key: 'snap',
    title: 'Stock your kitchen with a photo.',
    body: 'Snap your fridge or pantry and Sweep adds what it sees for you.',
  },
  {
    key: 'ideas',
    title: 'Dinner from what you already have.',
    body: 'Get personalised dinner ideas based on your kitchen and food preferences.',
  },
  {
    key: 'recipes',
    title: 'All your recipes in one place.',
    body: 'Bring in family favourites from text, photos, links or PDFs.',
  },
  {
    key: 'plan',
    title: 'Your week of dinners, sorted.',
    body: "Plan around what's in your Kitchen. Swap, edit or ask for changes.",
  },
  {
    key: 'list',
    title: "Shop only for what's missing.",
    body: 'Your plan adds just what you need, so you buy less and waste less.',
  },
  {
    key: 'sync',
    title: 'Everything in sync.',
    highlight: 'One app.',
    body: 'Your kitchen, recipes, shopping list and meal plan, all working together.',
  },
];
