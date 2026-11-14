# 4. FastAPI is the only writer; devices sync via change notifications

Date: 2026-11-08 · Status: Accepted

## Context

Shopping Lists and the Cabinet are shared across Members' devices, and both humans and the agent change them. Options considered:

- **Clients write straight to a managed database** (e.g. Supabase with row-level security, or a sync engine like PowerSync/ElectricSQL). Excellent real-time and offline behaviour, but business rules (tick → Cabinet update, Dietary Rules, audit) would be split between database policies and the API, and the agent's writes would go through a different path from humans'.
- **FastAPI owns every write; devices are notified of changes.** One place for rules, permissions and audit. Real-time is simpler and offline is weaker.

## Decision

- Every change (human or agent) goes through FastAPI service functions. Those services are the only code that writes to Postgres.
- Mutations send **intent, not toggles**: `PUT /items/{id}/checked {checked: true}`, never "toggle". Every mutation carries an `Idempotency-Key`, so retries over bad supermarket signal are safe.
- The API runs Postgres `NOTIFY` inside the write's transaction, so Postgres sends it only if the change commits. A WebSocket endpoint passes "Shopping List X changed (version N)" to that Household's connected devices, which refetch through TanStack Query.
- Conflicts: last write wins per field. Checking off an item is safe to repeat (the same request twice has the same effect).
- MVP offline behaviour: optimistic UI updates plus a persisted retry queue for mutations ("flaky signal tolerant"). Full offline-first is a later enhancement.

## Consequences

- Each change takes one extra network hop (notify → refetch) compared with a sync engine. Fine at household scale.
- Works with several API instances because the fan-out goes through Postgres, not process memory.
- Moving to an offline-first sync engine later would mean revisiting this ADR.

## Implementation notes (slice 2, 2026-11-14)

- **One shared channel (`sweep_changes`), not one per Household.** Each notice includes its `household_id`, and each API instance's Hub forwards it only to that Household's sockets. Per-Household channels would need LISTEN/UNLISTEN on a connection that is busy waiting for notices. At household scale, every instance seeing every notice costs nothing.
- Notices carry ids and versions only, never data. Devices refetch through REST, so permission checks always apply.
- WebSocket auth uses the first message (`{"type":"auth","token":...}`), not a URL query string, because tokens in URLs end up in logs. A device refetches after `subscribed` to cover the gap before its subscription started.
- A device that falls behind, or a listener that reconnects, gets `{"type":"resync"}` and refetches everything.
- Known gap: a removed Member's open socket keeps receiving ids and versions until it disconnects. Their refetches fail with 403, so no data leaks.
