# Sweep — AI Grocery Shopping Agent

A household app that connects what you own, what you need to buy, and what you can cook, so you don't have to keep searching for recipes online.

## Language

### People

**Member**:
A person signed in to the app who belongs to a Household.
_Avoid_: user (in domain discussions), account

**Household**:
The group of Members who share one Cabinet, one set of Shopping Lists, one Meal Plan and one recipe collection. A Member belongs to exactly one Household.
_Avoid_: family, team, group

**Owner**:
The Member who created the Household. Can invite and remove Members.
_Avoid_: admin

### The three pillars

**Cabinet**:
The household's record of the Ingredients it currently has at home.
_Avoid_: kitchen inventory, pantry, virtual kitchen cabinet, stock

**Shopping List**:
The list of items the Household intends to buy, shared across Members' devices.
_Avoid_: grocery list, basket

**Recipe Knowledge Base**:
The collection of recipes the app can search, recommend and plan from.
_Avoid_: recipe database, cookbook

### Ingredients and the Cabinet

**Ingredient**:
A canonical food item ("plain flour", "chicken thigh") that recipes, the Shopping List and the Cabinet all refer to, so they can be compared.
_Avoid_: product, item (an item is a line on a list)

**Staple**:
An Ingredient the Household is assumed to have until a Member marks it as run out (salt, oil, common spices). No quantity is tracked.
_Avoid_: pantry item, basic

**Tracked Ingredient**:
An Ingredient whose quantity the Cabinet records because it decides whether a meal is possible (meat, pasta, rice, cheese).
_Avoid_: inventory item

**Confirmed**:
A Cabinet quantity a Member recently stated or that came from ticking off a Shopping List item.

**Estimated**:
A Cabinet quantity the app calculated, e.g. by deducting a Cooked meal. Always shown as an estimate.

**Unknown**:
A Cabinet entry the app no longer trusts. The agent asks instead of assuming. Estimated entries become Unknown after a period without confirmation.

### Recipes

**Seed Recipe**:
A recipe loaded from an open dataset, available to every Household.
_Avoid_: default recipe, built-in recipe

**Imported Recipe**:
A recipe a Member saved from a URL. It belongs to that Household and is preferred over Seed Recipes when planning.
_Avoid_: saved recipe, user recipe

**Recipe Adaptation**:
A clearly labelled variation of an existing recipe (e.g. an ingredient swap), always linked to the recipe it came from.
_Avoid_: generated recipe, AI recipe

### Planning

**Meal Plan**:
The Household's set of Planned Meals for a given week.
_Avoid_: menu, schedule

**Planned Meal**:
One recipe (or Recipe Adaptation) assigned to a day, with a number of servings.
_Avoid_: meal slot, dinner

**Cooked**:
A Member's confirmation that a Planned Meal was actually made. Only Cooked meals deduct from the Cabinet.
_Avoid_: completed, done

**Dietary Rule**:
A hard constraint that must never be broken, such as an allergy or "no mushrooms". Enforced by the app, not left to the agent's judgement.
_Avoid_: preference, restriction (ambiguous)

**Preference**:
A soft taste the agent should lean towards ("likes Mediterranean", "quick weeknight meals"). Can be traded off.
_Avoid_: dietary requirement

### The agent

**Conversation**:
One ongoing chat between a Member and the agent. Follow-up requests continue the same Conversation and keep its context.
_Avoid_: session, thread (implementation term)

**Draft Plan**:
The work-in-progress Meal Plan and Shopping List changes the agent is building inside a Conversation. Visible to the Member, but not yet Household data.
_Avoid_: suggestion, result

**Proposal**:
A Draft Plan the agent presents for approval. Nothing in a Proposal changes Household data until it is approved.
_Avoid_: recommendation, change request

**Approval**:
A Member's decision to accept, reject or edit a Proposal. Recorded permanently.
_Avoid_: confirmation (Confirmed means something else)

### Money

**Estimated Price**:
A price from the simulated catalogue, always shown as an estimate and never as a real current shelf price.
_Avoid_: price, real price

**Estimated Cost**:
The total of Estimated Prices for the items a Proposal would add to the Shopping List.
_Avoid_: total, budget (the budget is the limit, not the cost)

## Relationships

- A **Household** has many **Members**, one **Cabinet**, one or more **Shopping Lists** and one **Meal Plan** per week
- The **Cabinet**, **Shopping List** and **Recipe Knowledge Base** all refer to the same **Ingredients**. That shared vocabulary is what connects them.
- Ticking an item off a **Shopping List** adds it to the **Cabinet** as **Confirmed** (if it's linked to an **Ingredient**)
- Marking a **Planned Meal** as **Cooked** deducts its Ingredients, which makes those quantities **Estimated**
- **Estimated** becomes **Unknown** over time. **Staples** never carry a quantity.
- The **Recipe Knowledge Base** contains **Seed Recipes** and each Household's **Imported Recipes**
- The agent only recommends recipes in the **Recipe Knowledge Base**, or **Recipe Adaptations** of them. It never invents a recipe from nothing.
- A **Conversation** builds a **Draft Plan**, which becomes a **Proposal**. Only an **Approval** turns it into **Meal Plan** and **Shopping List** changes.
- **Dietary Rules** are enforced before anything reaches a **Proposal**. **Preferences** only influence ranking.

## Example dialogue

> **Member:** "Plan four dinners. We've got chicken and rice."
> **Agent:** builds a **Draft Plan** from Seed and Imported Recipes, checks the **Cabinet** (chicken: Confirmed 1kg, rice: Estimated ~500g), and shows a **Proposal**: 4 **Planned Meals**, 9 Shopping List additions, **Estimated Cost** ~$64, and "I'm assuming you still have ~500g rice."
> **Member:** "Swap Tuesday for something vegetarian." → the agent edits the Draft Plan. It doesn't rebuild it.
> **Member:** approves → the Meal Plan and Shopping List update for the whole Household.

## Flagged ambiguities

- "kitchen inventory", "virtual kitchen cabinet", "pantry". Resolved: **Cabinet**.
- "dietary preferences" in the brief mixed hard and soft constraints. Resolved: split into **Dietary Rule** and **Preference**.
- "basket" in the brief meant both the Shopping List and a priced product selection. Resolved: use **Shopping List** for the list and **Estimated Cost** for the money. Product-level basket optimisation is a later experiment.
- Live supermarket pricing: **not required**. All prices are **Estimated Prices**.
