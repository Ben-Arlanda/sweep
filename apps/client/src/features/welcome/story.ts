/**
 * The words on the welcome screens, kept apart from the layout so they're easy to
 * review and change. Taken from the chosen design ("Zest + Kitchen Table", ADR 0007).
 *
 * `upcoming` marks a screen about a feature that isn't built yet. Those screens say
 * "Coming soon" so the app never promises something a new user can't try.
 */
export const LANDING = {
  title: "Cook what you've got.",
  highlight: "Buy only what's missing.",
  lede: "Turn what's in your Kitchen into great dinners, a weekly plan, and a smart shopping list.",
} as const;

export type StoryKey = 'shop' | 'kitchen' | 'ask' | 'plan';

export type StoryPage = {
  key: StoryKey;
  eyebrow: string;
  title: string;
  body: string;
  upcoming?: boolean;
};

export const STORY: StoryPage[] = [
  {
    key: 'shop',
    eyebrow: 'Shop together',
    title: 'One list for the whole household',
    body: "See who added what. When Bob ticks an item, his name pops up on Alice's phone and it goes straight into the Kitchen.",
  },
  {
    key: 'kitchen',
    eyebrow: 'Your Kitchen',
    title: 'It lands in your Kitchen',
    body: 'Tick it at the shop and Sweep stocks your Kitchen automatically. No typing in what you bought.',
  },
  {
    key: 'ask',
    eyebrow: 'Ask Sweep',
    title: 'Ask what to cook',
    body: "Recipe ideas built from what's in your Kitchen, each showing exactly what's missing.",
    upcoming: true,
  },
  {
    key: 'plan',
    eyebrow: 'This week',
    title: 'Plan the week together',
    body: "A Draft Plan with who's cooking each night. Approve it and only the missing items go on the list.",
    upcoming: true,
  },
];
