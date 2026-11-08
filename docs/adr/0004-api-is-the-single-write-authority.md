# 4. FastAPI is the only writer; devices sync via change notifications

Date: 2026-11-08 · Status: Accepted

## Context

Shopping Lists and the Cabinet are shared across Members' devices, and both humans and the agent change them. Options considered:

- **Clients write straight to a managed database** (e.g. Supabase with row-level security, or a sync engine like PowerSync/ElectricSQL). Excellent real-time and offline behaviour, but business rules (tick → Cabinet update, Dietary Rules, audit) would be split between database policies and the API, and the agent's writes would go through a different path from humans'.
- **FastAPI owns every write; devices are notified of changes.** One place for rules, permissions and audit. Real-time is simpler and offline is weaker.

## Decision

- Every change (human or agent) goes through FastAPI service functions. Those services are the only code that writes to Postgres.
- Mutations send **intent, not toggles**: `PUT /items/{id}/checked {checked: true}`, never "toggle". Every mutation carries an `Idempotency-Key`, so retries over bad supermarket signal are safe.
- After a commit, the API runs Postgres `NOTIFY` on a per-Household channel. A WebSocket endpoint passes "Shopping List X changed (version N)" to that Household's connected devices, which refetch through TanStack Query.
- Conflicts: last write wins per field. Checking off an item is safe to repeat (the same request twice has the same effect).
- MVP offline behaviour: optimistic UI updates plus a persisted retry queue for mutations ("flaky signal tolerant"). Full offline-first is a later enhancement.

## Consequences

- Each change takes one extra network hop (notify → refetch) compared with a sync engine. Fine at household scale.
- Works with several API instances because the fan-out goes through Postgres, not process memory.
- Moving to an offline-first sync engine later would mean revisiting this ADR.
