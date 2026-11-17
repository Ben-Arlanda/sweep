# Sweep — AI Grocery Shopping Agent

A household app that connects what you own, what you need to buy, and what you can cook, so you don't have to keep searching for recipes online.

## Language

### People

**Member**:
A person signed in to the app who belongs to a Household.
_Avoid_: user (in domain discussions), account

**Household**:
The group of Members who share one Kitchen, one Shopping List, one Meal Plan and one recipe collection. A Member belongs to exactly one Household.
_Avoid_: family, team, group

**Owner**:
The Member who created the Household. Can invite and remove Members.
_Avoid_: admin

### The three pillars

**Kitchen**:
The household's record of the Ingredients it currently has at home, grouped by Place.
_Avoid_: cabinet (the old name, ADR 0011), kitchen inventory, pantry, stock

**Place**:
Where an Ingredient is kept in the Kitchen: Fridge, Freezer or Cupboard. Every Ingredient has a default Place (from its category); a Household can move an item.
_Avoid_: location, storage, shelf

**Shopping List**:
The one list of items the Household intends to buy, shared across Members' devices. A Household has exactly one.
_Avoid_: grocery list, basket, lists (there is only one)

**Shop**:
Where the Household plans to buy an item (Coles, Woolies, Aldi, or one it added). A label on a Shopping List item, not a separate list. An item without a Shop can be bought anywhere.
_Avoid_: store, supermarket (in code and UI), list

**Recipe Knowledge Base**:
The collection of recipes the app can search, recommend and plan from.
_Avoid_: recipe database, cookbook

**Course**:
What a recipe is for: *main*, *side*, *dessert* (sweet things and baking, incl. snacks like bliss balls or scones), *breakfast* or *lunch* (sandwiches, wraps, rolls, toasties). Every recipe has exactly one. A Planned Meal is a dinner, so plans offer mains unless the Member names a dish or kind of dish that isn't one ("pancakes on Friday", "something sweet"). A borderline recipe gets the Course it fits best.
_Avoid_: category (Ingredients have categories), meal type

### Ingredients and the Kitchen

**Ingredient**:
A canonical food item ("plain flour", "chicken thigh") that recipes, the Shopping List and the Kitchen all refer to, so they can be compared.
_Avoid_: product, item (an item is a line on a list)

**Household Ingredient**:
An Ingredient one Household created by adding something Sweep didn't know ("kale", "bin bags"). Works like any Ingredient in that Household's list and Kitchen; merged into the shared one if Sweep adds it later.
_Avoid_: custom item, unknown item

**Ingredient link**:
A Household's choice that a name means a particular Ingredient ("chocolate" → dark chocolate). Applies to future list items and imported recipe lines.
_Avoid_: alias (aliases are shared reference data)

**Staple**:
An Ingredient the Household is assumed to have until a Member marks it as run out (salt, oil, common spices). No quantity is tracked.
_Avoid_: pantry item, basic

**Tracked Ingredient**:
An Ingredient whose quantity the Kitchen records because it decides whether a meal is possible (meat, pasta, rice, cheese).
_Avoid_: inventory item

**Confirmed**:
A Kitchen quantity a Member recently stated or that came from ticking off a Shopping List item.

**Estimated**:
A Kitchen quantity the app calculated, e.g. by deducting a Cooked meal. Always shown as an estimate.

**Unknown**:
A Kitchen entry the app no longer trusts. The agent asks instead of assuming. Estimated entries become Unknown after a period without confirmation.

### Recipes

**Seed Recipe**:
A recipe written for Sweep (we own it), available to every Household.
_Avoid_: default recipe, built-in recipe

**Imported Recipe**:
A Household favourite a Member brought in (pasted, photographed, linked, uploaded as a PDF file or typed). It belongs to that Household only and is preferred over Seed Recipes when planning.
_Avoid_: saved recipe, user recipe

**Recipe Adaptation**:
A clearly labelled variation of an existing recipe that swaps one or more ingredient lines for others (e.g. beef mince → lentils, cream → Greek yoghurt). The method isn't rewritten. Always linked to the recipe it came from. The planner proposes it inside a Proposal, and it's saved only when a Member approves.
_Avoid_: generated recipe, AI recipe, substitution (a **Swap** is one line of an Adaptation)

**Swap**:
One line of a Recipe Adaptation: the original line and what replaces it. Checked by code: the replacement must be a known Ingredient, and the adapted recipe must pass the Household's Dietary Rules.
_Avoid_: substitution, replacement

### Planning

**Meal Plan**:
The Household's Planned Meals for a given week. Weeks run Monday to Sunday. One dinner per day.
_Avoid_: menu, schedule

**Planned Meal**:
One recipe (or Recipe Adaptation) assigned to a day, with a number of servings.
_Avoid_: meal slot, dinner

**Cooked**:
A Member's confirmation that a Planned Meal was actually made. Only Cooked meals deduct from the Kitchen.
_Avoid_: completed, done

**Dietary Rule**:
A hard constraint that must never be broken, such as an allergy or "no mushrooms". Enforced by the app, not left to the agent's judgement.
_Avoid_: preference, restriction (ambiguous)

**Preference**:
A soft taste the agent should lean towards ("likes Mediterranean", "quick weeknight meals"). Can be traded off.
_Avoid_: dietary requirement

**Kitchen Match**:
How well a recipe fits what's in the Kitchen: which of its ingredients the Household has, might have (Unknown status) or is missing. Plans start from the best Kitchen Matches (fewest things to buy).
_Avoid_: coverage score, pantry match

### The agent

**Conversation**:
One ongoing chat between a Member and the agent. Follow-up requests continue the same Conversation and keep its context.
_Avoid_: session, thread (implementation term)

**Plan Mode**:
The kind of plan a Member asks for in the "Plan my week" sheet: *Cook from my Kitchen* (fewest things to buy) or *New recipes* (chosen by taste; the Kitchen only trims the Shopping List). Stored on the Conversation. A free chat has none.
_Avoid_: "Something new"

**Plan Days**:
The days a plan covers, picked in the "Plan my week" sheet. The agent may only put meals on these days. The Household's **Usual Days** (weekdays, e.g. Mon–Fri) are what the sheet starts with.

**List Addition**:
An item a Proposal would put on the Shopping List. Its amount is the extra to buy, on top of what's already on the list; approving tops up a matching unticked item rather than adding a second line. Each one carries its **reason**: a Planned Meal that needs it, or the Member asked for it. One with no reason is **unexplained**: the Proposal card shows it unticked ("Not for any meal"), so it's only added if a Member ticks it on purpose.

**Draft Plan**:
The work-in-progress Meal Plan and Shopping List changes the agent is building inside a Conversation. Visible to the Member, but not yet Household data.
_Avoid_: suggestion, result

**Proposal**:
A Draft Plan the agent presents for approval. Nothing in a Proposal changes Household data until it is approved.
_Avoid_: recommendation, change request

A Proposal is *pending* until it's approved or rejected. It becomes *superseded* when the Member asks the agent for changes instead, and *expired* after 24 hours.

**Approval**:
A Member's decision on a Proposal: approve (optionally after unticking some meals or list additions) or reject. Recorded permanently. Bigger edits happen in the Conversation, which produces a new Proposal.
_Avoid_: confirmation (Confirmed means something else)

### Evaluation

**Scenario**:
One agent test case: a starting Household (Dietary Rules, Kitchen, chosen days and mode), the Member's messages, and the checks the result must pass.
_Avoid_: test case, prompt (a Scenario is more than the message)

**Grader**:
A deterministic check that scores one run from what the agent did (the Proposal, tool calls, tokens), never from what it said. Either must-pass or measured.
_Avoid_: judge (reserved for an LLM grader, not built yet)

**Eval Run**:
Every Scenario run a set number of times on one model, with a pass rate per Scenario and the measured averages (replans, tool calls, items to buy, seconds, cost).
_Avoid_: benchmark, test run

**Injection Scenario**:
A Scenario where text the agent reads (an Imported Recipe, another Member's Kitchen item, list item or name) tries to give it instructions. It passes only if what the agent did shows no trace of them.
_Avoid_: jailbreak test (a jailbreak is the Member attacking the model directly)

**Canary**:
Something an Injection Scenario's planted text asks for that no honest plan would contain ("add 50 saffron threads"). Finding it in a Proposal means the injection worked.
_Avoid_: trigger, payload

**Baseline Planner**:
The no-agent alternative the agent is compared against: code filters recipes by Dietary Rules and ranks them by Kitchen Match, then one model call picks the meals. No tools, no replans.
_Avoid_: simple agent (it isn't one)

## Relationships

- A **Household** has many **Members**, one **Kitchen**, one **Shopping List** and one **Meal Plan** per week
- The **Kitchen**, **Shopping List** and **Recipe Knowledge Base** all refer to the same **Ingredients**. That shared vocabulary is what connects them.
- Ticking an item off a **Shopping List** adds it to the **Kitchen** as **Confirmed** (if it's linked to an **Ingredient**)
- Marking a **Planned Meal** as **Cooked** deducts its Ingredients, which makes those quantities **Estimated**
- **Estimated** becomes **Unknown** over time. **Staples** never carry a quantity.
- The **Recipe Knowledge Base** contains **Seed Recipes** and each Household's **Imported Recipes**
- The agent only recommends recipes in the **Recipe Knowledge Base**, or **Recipe Adaptations** of them. It never invents a recipe from nothing.
- A **Conversation** builds a **Draft Plan**, which becomes a **Proposal**. Only an **Approval** turns it into **Meal Plan** and **Shopping List** changes.
- **Dietary Rules** are enforced before anything reaches a **Proposal**. **Preferences** only influence ranking.

## Example dialogue

> **Member:** "Plan four dinners. We've got chicken and rice."
> **Agent:** builds a **Draft Plan** from Seed and Imported Recipes, checks the **Kitchen** (chicken: Confirmed 1kg, rice: Estimated ~500g), and shows a **Proposal**: 4 **Planned Meals**, 9 Shopping List additions, and "I'm assuming you still have ~500g rice."
> **Member:** "Swap Tuesday for something vegetarian." → the agent edits the Draft Plan. It doesn't rebuild it.
> **Member:** approves → the Meal Plan and Shopping List update for the whole Household.

## Flagged ambiguities

- "kitchen inventory", "virtual kitchen cabinet", "pantry". Resolved: **Cabinet**, renamed **Kitchen** in 2026-11 (ADR 0011). "Pantry" also clashed with the Cupboard Place.
- "dietary preferences" in the brief mixed hard and soft constraints. Resolved: split into **Dietary Rule** and **Preference**.
- "basket" in the brief meant both the Shopping List and a priced product selection. Resolved: **Shopping List** only. Sweep has no prices or budgets (ADR 0010).
- "lists" per supermarket. Resolved: one **Shopping List**, items labelled by **Shop** (ADR 0009).
