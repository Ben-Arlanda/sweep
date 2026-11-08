# 6. Run LangGraph in the Python backend, not in the Expo app

Date: 2026-11-08 · Status: Accepted

## Context

LangGraph exists for both Python and JavaScript, and the frontend is TypeScript, so a reader may wonder why the agent isn't next to the UI.

## Decision

The agent runs in the FastAPI service using LangGraph for Python, with the Postgres checkpointer (`langgraph-checkpoint-postgres`, async variant). The app streams agent output over Server-Sent Events and resumes interrupts through an API call.

## Why

- Model credentials (the Anthropic API key now, a Bedrock IAM role later) must never ship inside a mobile or web app.
- Tools call backend services directly, inside the same permission checks and transactions, with no second network hop.
- Checkpoints (paused Conversations awaiting Approval) must survive app restarts and device switches, so they belong in server-side Postgres.
- The Python ecosystem for evaluation, RAG and ML experiments matches the rest of the learning roadmap.

## Consequences

- Agent types and API types live in Python. The TypeScript client is generated from FastAPI's OpenAPI schema.
- Streaming and interrupt/resume need a small, well-defined API contract (see plan §7).
