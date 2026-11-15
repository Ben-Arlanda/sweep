# 15. Plans carry their days and mode; validate holds the agent to the days

Date: 2026-11-15 · Status: Accepted

## Context

"Plan my week" sent a fixed message, so the agent chose how many days and which. Members want to pick the days (only weeknights, or the whole week) and the kind of plan: from the Kitchen (ADR 0013) or new recipes to shop for. 5c showed that instructions written only in the first message fade as a chat goes on.

## Decision

- **One sheet** opens from "Plan my week" (Home, the chat, the Meal Plan screen): a Mon–Sun week strip to pick days (past days off, days already planned start unticked), Weeknights / Every day shortcuts, this week or next (it opens on next week at the weekend), then *Cook from my Kitchen* or *New recipes to shop for*. "Just tonight" stays Kitchen-first, with no sheet.
- **Mode and days live on the Conversation** (`plan_mode`, `plan_days`), set when it's created and checked by the server (from today, within the 14-day plan window, each once). Every turn's context states them. The fixed system prompt explains both modes, so it stays identical between turns (prompt caching).
- **Validate refuses meals on other days**, like any other date problem: the agent is sent back to fix it, and after the replans run out the meal is left out and listed. The model can't get round it.
- **Usual days are remembered per Household** as ISO weekdays, through their own route (`PUT /households/current/plan-weekdays`), so saving them can't overwrite another Member's change to the rest of the Preferences. Only days the Member could choose change the pattern; a day left out because it was past or already planned keeps its old setting.
- **The Meal Plan reads Mon–Sun weeks**, and the server says what today is. Its strip is a picker too (this week and next): tap days, then the same two choices appear under it. A strip that looks like a calendar gets tapped; the first version was display-only and the product owner couldn't pick days on it.

## Consequences

- Asking for an extra day mid-chat ("add Saturday") needs a new plan from the sheet; the agent says so. A tool to change the days would let the model undo the guardrail.
- On a Sunday, "This week" on the Meal Plan is mostly past; upcoming dinners are under next week.
- Two places know the plan window (validate and Conversation creation); both use 14 days.
