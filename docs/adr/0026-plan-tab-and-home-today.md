# 26. A Plan tab, Household behind the cog, and a Home that never changes shape

Date: 2026-11-18 · Status: Accepted

## Context

The Meal Plan was a screen opened from a "This week" strip on Home (slice 6, "not a new tab"). The redesigned Home ("What's cooking today?", from the user's mockups) has no room for that strip, and the week is something people check every day. Household settings, by contrast, are opened rarely but held a whole tab.

## Decision

- **The Meal Plan becomes the Plan tab** (`/meal-plan`, tab "Plan"): This week / Next week, one row per day with ••• for the recipe, Cooked, Swap and Remove. Only this week and next, because a plan covers today and the next 13 days.
- **Household settings move behind the cog** (and the avatar) on Home, as a stack screen at the same `/household` path. Nav: Home, Lists, Kitchen, Plan, Recipes.
- **Home's hero never changes shape.** It always asks the question. Below it sits the Tonight card (Find dinner ideas, tonight's dinner with Cooked, or Cooked ✓ with Undo), or **Your meal plan** once a day other than today has a dinner (`hasPlan`). Tapping a day there shows its dinner.
- **The lime button is never greyed out** (`homeCta`): Plan my week → Edit my week once there's a plan → Plan next week from Friday while next week is empty. All three open the same Plan my week sheet (ADR 0015) for the right week.
- **Swap and Add on a saved plan reuse Dinner Ideas for that day** (`/tonight?date=`), planned straight away by code (ADR 0025). Asking Sweep is hidden there, because Sweep's pick is always for tonight. We rejected a new swap endpoint for saved meals: `PUT /meal-plan/days/{day}` already replaces an uncooked meal.

## Consequences

- One sheet behind every "plan" button, so there's one place to test and the remembered days apply everywhere.
- Planned meals now carry `total_minutes` ("25 min · Serves 4"); the client cache buster was bumped.
- "Tomorrow" after Cooked is no longer on Home: with a plan it's in the day strip, and without one there's no tomorrow to show.
