# 8. Call Claude through the Anthropic SDK inside LangGraph nodes, not LangChain's chat model

Date: 2026-11-15 · Status: Accepted

## Context

Plan §8 said to use LangChain's Anthropic chat model so LangGraph tool calling works.
Building slice 5 showed that LangGraph doesn't need it: a node is just an async function,
so it can call any client. Sonnet 5.5 (the agent model) also has API rules that a
wrapper has to keep up with:

- thinking blocks must go back into the history unchanged, and the history must only grow
  (editing an earlier message or the system prompt invalidates them)
- forced `tool_choice` is rejected; strict tool schemas are the way to get valid arguments
- refusal fallbacks (`fallbacks: "default"`), effort and prompt caching are request fields

## Decision

- LangGraph runs the graph, the checkpointer and (slice 6) interrupts.
- The `agent` node calls Claude through the official `anthropic` SDK, behind a small
  `AgentModel` interface (`app/agent/model.py`). `app/llm.py` stays the only module that
  imports a provider SDK.
- The conversation is stored in the Claude API's own message shape, append-only. The system
  prompt never changes; each turn's Household context is added as data in the new user
  message.

## Consequences

- New API features are available as soon as the SDK has them, with no wrapper to wait on.
- We write the tool loop ourselves (about 100 lines in `app/agent/graph.py`), which also
  makes the agent's steps easy to see and test.
- Tests use a scripted model through the same interface, so CI never calls the API.
- Adding Bedrock later (slice 11, E5) means a second `AgentModel`, not a rewrite.
- LangChain's tool and message helpers aren't used. If we ever want them, only `llm.py` and
  the state's message shape change.
