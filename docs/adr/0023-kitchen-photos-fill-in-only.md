# 0023: Kitchen Photos only fill in, and a photo's count replaces

Date: 2026-11-17. Status: accepted. Builds on ADR 0003 (precision tiers), 0011 (Places) and 0020 (recipe photos).

## Context

Typing a Kitchen in by hand is slow, so an empty Kitchen stays empty and the planner has little to start from. A photo of the fridge, freezer or cupboard can suggest items instead. But the Kitchen drives what the planner thinks a Household has, a model will misread some items, and a photo is untrusted input (a note on the fridge can try to give orders).

## Decision

- **Fill-in only.** A Kitchen Photo adds or refreshes items and never removes them. A photo can show that something is there, not that it's gone. Hidden items would otherwise be marked run out, which is the "confidently wrong" Kitchen ADR 0003 warns about.
- **A Member approves a pre-ticked list** before anything changes. The happy path is one tap.
- **The Member picks the Place first.** New items go there; existing items keep their Place.
- **Approved items are Confirmed**, with change source `photo`: a person checked them, while Estimated means the app calculated it.
- **A photo shows the total, so its count replaces the stored amount** ("6 eggs" makes 6, not 4 + 6). With no count, a trusted amount is kept and re-confirmed, and an Unknown one becomes "have some". Counts only for countable things: no grams guessed from how full a jar looks.
- Same input rules as recipe photos (ADR 0020): 1–3 photos, never stored, one Haiku call, the shared 20/hour limit.

## Consequences

- Run-out items still need a tap or a Cooked meal. A stocktake (with each removal ticked by hand) can come later, one Place at a time.
- A Member who taps "Add all" without looking gets Confirmed items they didn't really check. The review shows current amounts and Not linked rows start unticked, which limits the damage, and status decays as usual.
- Re-confirming a kept amount can be wrong (most of the chicken was used). The row shows the current amount so the Member can fix it.
- Whether Haiku reads a crowded fridge well enough is decided by an eval with a bar set before running (precision ≥ 90%, recall ≥ 70%, Canary absent 3/3).
