# 14. Approvals pause the graph; Proposals are database records

Date: 2026-11-15 · Status: Accepted

## Context

ADR 0005 says the agent writes nothing until a Member approves a Proposal. Slice 6a builds that. A Proposal may wait for hours, the Member may answer from another device, or may reply in the chat instead of deciding. And a retried Approve (bad signal) must not save the meals twice.

## Decision

- **The graph pauses with `interrupt()`** in an `approve` node after `validate`. The paused graph is saved by the Postgres checkpointer. `POST /proposals/{id}/decision` resumes it with `Command(resume=...)`: approve → `commit` node; reject → end. A chat message sent while it waits resumes it as "message": the Proposal becomes *superseded* and the turn carries on as normal. That turn always ends with a Proposal: if the agent answers without proposing again ("Wednesday is already vegetarian"), a `reshow` node shows the unchanged Draft again, with the same checks as validate and no model call (added 2026-11-16 after the slice 8 eval found Haiku leaving only a superseded plan).
- **Proposals are also rows** (`proposals` table): status, expiry, exactly what was shown (`payload`) and what approving did (`outcome`). The graph's state is for the agent; the row is the record the app, the audit log and the chat history read.
- **Commit is plain code** in one transaction, under the approving Member. It re-checks every kept meal against today's data and skips what no longer passes; a planned day is replaced unless already Cooked; a list addition already unticked on the list is skipped. The confirmation message is written by code.
- **Idempotent by Proposal id**, not an Idempotency-Key header: the commit runs in the graph's own transaction, so a key row couldn't be saved with it. An approved Proposal's stored `outcome` is returned on a retry. Every status change is guarded by `status = 'pending'`.
- **The confirmation isn't added to Claude's history.** Only Claude's own replies go there. The next turn's context says how the last Proposal was answered, and lists the saved Planned Meals.
- **Expiry (24h) is checked when someone acts or reads**, no background job.
- One per-Conversation advisory lock covers both turns and decisions.

## Consequences

- The human-in-the-loop step is real LangGraph pause and resume, not a flag the next turn checks.
- `approve` runs again from the top on every resume, so nothing in it before `interrupt()` may have side effects.
- Two sources of truth to keep in step (graph state, Proposal row). The row wins for status; the graph only knows which Proposal it waits on.
