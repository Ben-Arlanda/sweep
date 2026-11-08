# AI Grocery Shopping Agent (sweep)

## Project

A cross-platform AI grocery shopping and meal-planning
application built with Expo and React Native.

Backend: Python, FastAPI and PostgreSQL.
AI: LangGraph, RAG, MCP and AWS Bedrock.

See PRODUCT_BRIEF.md for product requirements.
See AI_LEARNING_ROADMAP.md for learning objectives.

## Developer Context

I'm a mid-level software engineer experienced with
React, TypeScript, Python, FastAPI and PostgreSQL.

This project is both a real product and an AI
engineering learning exercise.

## Working Style

- Use AI-assisted development to move quickly.
- Keep explanations concise and practical.
- Explain unfamiliar AI engineering concepts.
- Explain important architectural trade-offs.
- Challenge questionable design decisions.
- Don't overengineer routine functionality.
- Don't skip explicit learning objectives simply
  because a simpler implementation exists.
- Use isolated experiments when a learning objective
  doesn't fit naturally into the product.

## AI Engineering Learning

When implementing a significant AI feature:

1. Explain why we're using the technology.
2. Explain the architecture and data flow.
3. Highlight important trade-offs.
4. Explain testing and evaluation.
5. Identify what I should understand for interviews.

Read AI_LEARNING_ROADMAP.md when planning AI features.

## Architecture Principles

- Use LangGraph for a genuine tool-using agent.
- Keep critical business logic deterministic.
- Validate and authorise tool execution.
- Prioritise security, reliability and testability.
- Use clear boundaries between API, services,
  agent orchestration and database access.

## Planning

Planning outputs (read before implementing):
- CONTEXT.md: domain language. Use these terms in code and conversation.
- docs/plan.md: architecture and implementation slices.
- docs/adr/: decisions and why they were made.

Use Matt Pocock's Grill with Docs skill for planning.

- Challenge assumptions and missing requirements.
- Document important architecture decisions.
- Don't implement major features before planning.
- Don't reopen confirmed decisions without good reason.

## Git Workflow

- Keep main stable.
- Use feature branches for meaningful changes.
- Keep pull requests focused.
- Include tests for new functionality.
- Use GitHub Actions for automated checks.
- Never push, create PRs or merge without approval.
- Never commit secrets.
- Explain significant changes before review.

## Documentation

Keep documentation concise.

Update relevant documentation when architecture,
product behaviour or major decisions change.

Do not create unnecessary documentation files.
