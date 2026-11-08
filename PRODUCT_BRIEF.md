# AI Grocery Shopping Agent — Product & Engineering Brief

## 1. Project Overview

I want to build an AI-powered grocery shopping and meal-planning application that helps households save money, reduce food waste, and simplify their weekly shopping.

The application should use an autonomous AI agent to plan meals, discover recipes, compare supermarket prices, manage household inventory, and optimise shopping baskets.

The application will be built using Expo and React Native, targeting iOS, Android, and web from a shared frontend codebase.

The initial market is Australia, with a focus on Coles, Woolworths, and Aldi.

### Project Objectives

This project has two equally important objectives:

1. Build a genuinely useful AI grocery shopping product that solves a real customer problem.
2. Develop advanced AI engineering skills to improve my chances of securing an AI Engineer or AI-focused Software Engineer role.

This is a personal portfolio and learning project that should follow professional software engineering practices.

**A genuine LangGraph AI agent is a core requirement, not an optional enhancement.**

---

## 2. Problem Statement

Weekly grocery shopping requires households to manage multiple disconnected activities:

- Deciding what meals to cook.
- Finding recipes that suit dietary preferences.
- Checking ingredients already available at home.
- Calculating ingredient quantities.
- Comparing supermarket products and prices.
- Staying within a weekly grocery budget.
- Remembering what needs to be purchased.
- Coordinating shopping lists between household members.
- Tracking ingredients after purchasing them.
- Avoiding unnecessary purchases and food waste.

Existing shopping lists, recipe applications, and supermarket comparison tools often address these activities separately.

### Proposed Solution

An AI grocery shopping agent that combines meal planning, grocery optimisation, shared shopping lists, and kitchen inventory management into one application.

Users should be able to describe their requirements naturally.

The agent independently determines which tools and information it needs, researches options, creates a plan, and adapts when circumstances change.

The application should reduce the amount of manual information users need to provide by maintaining household preferences, shopping history, and approximate kitchen inventory.

The user remains in control of important decisions.

---

## 3. Target Users

The initial target audience is Australian households who want to:

- Reduce weekly grocery spending.
- Spend less time planning meals.
- Follow dietary preferences.
- Make better use of existing ingredients.
- Reduce food waste.
- Share shopping responsibilities.
- Maintain one shopping list across multiple devices.
- Use AI to simplify household planning.

The application must be accessible to non-technical users.

---

## 4. Platforms and Frontend Architecture

### Confirmed Technology Decision

Use:

- Expo.
- React Native.
- React Native Web.
- TypeScript.
- Expo Router.

The goal is to support iOS, Android, and web using as much shared application code as practical.

Do not replace this approach with Next.js or a PWA during planning.

Investigate the most appropriate Expo architecture and supporting libraries.

### Platform Requirements

#### iOS

The iPhone experience is a primary product requirement.

It should support:

- Shared grocery shopping lists.
- Adding and completing grocery items.
- Kitchen inventory management.
- Conversational AI interaction.
- Meal planning.
- Push notifications where useful.
- Authentication.
- Fast, touch-friendly navigation.

Investigate offline shopping-list functionality and background synchronisation.

#### Android

Provide equivalent core functionality using the shared React Native application.

#### Web

Provide a responsive web experience supporting:

- Meal planning.
- AI conversations.
- Shopping lists.
- Kitchen inventory.
- Grocery price comparisons.
- Household preferences.
- Account management.

The web interface should make appropriate use of larger screens.

### Cross-Platform Engineering

Prefer shared:

- Business logic.
- API clients.
- Authentication.
- State management.
- Data models.
- Validation.
- Design tokens.
- Reusable UI components where practical.

Use platform-specific implementations when necessary.

Do not force identical interfaces across mobile and desktop if this compromises usability.

Investigate Expo's current capabilities and limitations before finalising the frontend architecture.

---

## 5. Example User Experience

A user asks:

"Plan five healthy dinners for two people this week. Our budget is $120. We like Mediterranean food, don't eat mushrooms, and already have chicken, rice and olive oil. Find the cheapest sensible shopping basket."

The AI agent should independently decide which actions are necessary.

It may:

1. Retrieve household preferences.
2. Check kitchen inventory.
3. Search suitable recipes.
4. Evaluate dietary requirements.
5. Calculate ingredient quantities.
6. Identify missing ingredients.
7. Search supermarket product data.
8. Compare prices and package sizes.
9. Identify substitutions.
10. Calculate shopping costs.
11. Reconsider recipes if the budget is exceeded.
12. Present a meal plan and shopping basket.
13. Request approval before saving the proposed changes.

### Follow-up Requests

Users should be able to say:

- "Replace Tuesday's dinner with something vegetarian."
- "Can you make this $20 cheaper?"
- "Only shop at Woolworths."
- "We already have pasta."
- "Use more ingredients from our kitchen."
- "Find healthier alternatives."
- "Make enough for leftovers."

The agent should preserve the existing context and decide which tools need to run again.

It should not unnecessarily rebuild the entire plan.

---

## 6. Shared Grocery Shopping List

The application must include a built-in grocery shopping list with functionality comparable to Apple Reminders.

This replaces the earlier idea of integrating directly with Apple Reminders.

### Core Features

Users should be able to:

- Create grocery shopping lists.
- Add items manually.
- Edit item names and quantities.
- Mark items as purchased.
- Remove items.
- Organise items into categories.
- Share lists with household members.
- See updates across connected devices.
- Add products recommended by the AI agent.
- Reuse previous shopping items.

### Shared Household Functionality

Multiple household members should be able to access the same shopping list.

For example:

- One person adds milk using their iPhone.
- Another sees the item on their phone.
- Someone purchases milk and checks it off.
- Both devices reflect the updated status.
- The kitchen inventory receives the purchased item.

Investigate real-time synchronisation using an appropriate backend approach.

### Mobile Experience

The shopping-list experience should prioritise:

- Large touch-friendly checkboxes.
- Fast item entry.
- Minimal navigation.
- Clear purchased/unpurchased states.
- Responsive interactions.
- Reliable synchronisation.

Offline support is desirable but does not need to block the initial MVP.

---

## 7. Smart Kitchen Inventory

The application must include a virtual kitchen cabinet that tracks ingredients available in the household.

### Core Concept

When a grocery item is marked as purchased, the application should automatically update the household inventory.

For example:

1. The shopping list contains "Pasta — 500g".
2. The user purchases the pasta.
3. They mark the item as completed.
4. The application adds 500g of pasta to the kitchen inventory.
5. The AI agent can now use that inventory information when planning meals.

This reduces the need for users to repeatedly tell the agent which ingredients they own.

### Inventory Requirements

- Maintain a household ingredient inventory.
- Track quantities and units.
- Automatically add purchased groceries.
- Support manual inventory updates.
- Normalise ingredient names.
- Prevent duplicate inventory additions.
- Support quantity corrections.
- Allow users to remove ingredients.
- Optionally track expiry dates.
- Estimate remaining quantities when ingredients are used.

### Inventory Consumption

When a user confirms that they cooked a planned meal, the application should be able to deduct the estimated ingredient quantities.

For example:

- Existing rice: 1kg.
- Recipe requires: 250g.
- Estimated remaining rice: 750g.

Do not automatically assume recipes have been cooked simply because they were added to a meal plan.

### Data Accuracy

Kitchen inventory should distinguish between:

- Confirmed quantities.
- Estimated quantities.
- Unknown quantities.

Provide simple ways for users to correct inaccurate information.

The system should not present estimated stock levels as guaranteed facts.

### AI Integration

The agent should have tools to:

- Retrieve inventory.
- Identify available ingredients.
- Compare inventory with recipe requirements.
- Calculate missing ingredients.
- Recommend meals using existing ingredients.
- Suggest substitutions.
- Prepare shopping lists.
- Propose inventory adjustments.

Inventory mutations must be validated and authorised through backend services.

---

## 8. Agentic AI — Core Architecture Requirement

The application must be designed around a genuine AI agent using LangGraph.

Building and understanding agentic AI systems is one of the primary learning objectives.

Do not reduce the core experience to a deterministic workflow.

### Agent Behaviour

The AI agent must be capable of:

1. Understanding a user's goal.
2. Determining which information is needed.
3. Dynamically selecting appropriate tools.
4. Executing tools through controlled interfaces.
5. Interpreting tool results.
6. Deciding whether additional information is needed.
7. Replanning when results are insufficient.
8. Recovering from tool failures.
9. Maintaining state across interactions.
10. Requesting approval for appropriate actions.
11. Producing validated results.

The agent should adapt its execution path depending on the request and tool responses.

### Proposed Agent Tools

Potential tools include:

- `search_recipes`
- `retrieve_recipe_context`
- `get_household_preferences`
- `get_kitchen_inventory`
- `search_supermarket_products`
- `compare_product_prices`
- `calculate_ingredient_quantities`
- `optimise_shopping_basket`
- `find_ingredient_substitutions`
- `validate_meal_plan`
- `get_shopping_list`
- `propose_shopping_list_changes`
- `save_meal_plan`
- `suggest_inventory_adjustments`

These are candidate tools, not final API contracts.

Define the final interfaces during planning.

### LangGraph Requirements

Implement and understand:

- Stateful agent orchestration.
- LLM-driven tool selection.
- Conditional routing.
- Planning and replanning.
- Persistent checkpoints.
- Interruptions and resumptions.
- Human-in-the-loop approval.
- Tool execution loops.
- Error handling.
- Retries and timeouts.
- Execution limits.
- Agent tracing.

Begin with a single-agent architecture unless planning identifies a clear reason for multiple agents.

Multi-agent systems may be explored later as learning experiments.

### Deterministic Business Logic

The agent must not handle critical calculations solely through LLM reasoning.

Use deterministic backend services for:

- Price calculations.
- Ingredient quantity calculations.
- Budget validation.
- Unit conversions.
- Inventory updates.
- Permission checks.
- Dietary constraint enforcement.
- Shopping basket optimisation.

The agent decides which tools to invoke, while backend code performs controlled operations.

---

## 9. Core Meal Planning Capabilities

### Meal Recommendations

- Generate meal plans from natural-language requests.
- Respect dietary preferences.
- Account for household size.
- Consider cooking time.
- Consider available ingredients.
- Support budget constraints.
- Suggest alternative meals.
- Allow users to modify individual meals.

### Recipe Retrieval

Build a recipe knowledge base.

The application should support:

- Recipe searching.
- Ingredient-based retrieval.
- Dietary filtering.
- Semantic similarity.
- Ranking and re-ranking.
- Recipe explanations.

### Grocery Basket Generation

The application should:

- Consolidate ingredients across recipes.
- Subtract available pantry quantities.
- Match ingredients to purchasable products.
- Account for packaging sizes.
- Compare available product prices.
- Calculate estimated total costs.
- Suggest substitutions.
- Optimise against the user's budget.

The system must distinguish real supermarket prices from estimated or simulated prices.

---

## 10. AI Engineering Learning Objectives

This project is both a product and an AI engineering learning exercise.

I will provide a separate AI engineering learning roadmap.

The roadmap describes the skills I want to develop, not a fixed development timeline.

### 10.1 LLM Engineering

Learn:

- LLM API integration.
- AWS Bedrock.
- Prompt engineering.
- Context engineering.
- Structured outputs.
- Tool calling.
- Model selection.
- Latency optimisation.
- Token usage and cost management.

### 10.2 Advanced RAG

Build a recipe and food knowledge retrieval pipeline.

Learn:

- Data ingestion.
- Chunking.
- Embeddings.
- PostgreSQL with pgvector.
- Semantic search.
- Hybrid search.
- Re-ranking.
- Grounded generation.
- Retrieval evaluation.
- Hallucination reduction.

Compare retrieval approaches and measure their effectiveness.

### 10.3 LangGraph

Learn:

- Agent orchestration.
- State management.
- Tool selection.
- Conditional routing.
- Persistent execution.
- Checkpointing.
- Interruptions.
- Human approval.
- Recovery from failures.

### 10.4 Model Context Protocol

Build an MCP server exposing appropriate application capabilities.

Learn:

- MCP architecture.
- Tool definitions.
- Tool discovery.
- Input schemas.
- Authentication.
- Tool validation.
- Error handling.
- Secure execution.

Understand how MCP differs from native LLM function calling.

### 10.5 Applied Machine Learning

Investigate:

- Content-based recommendation systems.
- Collaborative filtering.
- Embedding similarity.
- Ranking algorithms.
- User preference modelling.
- Recommendation quality metrics.
- Feedback-driven personalisation.

Understand where conventional ML methods are more appropriate than LLM reasoning.

### 10.6 LLM Evaluations

Evaluate:

- Agent task completion.
- Tool selection accuracy.
- Retrieval relevance.
- Recommendation quality.
- Budget compliance.
- Dietary constraint compliance.
- Basket correctness.
- Grounding and hallucinations.
- Failure recovery.
- Latency.
- Cost.

Build test datasets and automated evaluation pipelines.

### 10.7 Observability

Explore LangSmith or Langfuse.

Implement:

- Agent execution traces.
- Structured application logs.
- Tool call logs.
- Error reporting.
- Performance metrics.
- Audit trails.
- Model usage monitoring.

### 10.8 Security

Learn:

- Authentication.
- Authorisation.
- Prompt injection defence.
- Tool argument validation.
- Secure credential handling.
- Least-privilege permissions.
- Data isolation.
- Audit logging.
- Execution limits.
- Human approval mechanisms.

### 10.9 Cloud Engineering

Develop experience with:

- AWS Bedrock.
- AWS IAM.
- Docker.
- Cloud deployment.
- PostgreSQL hosting.
- Secrets management.
- Background jobs.
- Cloud monitoring.
- GitHub Actions.
- CI/CD.

### Learning Requirements

These are deliberate learning objectives.

Do not skip a technology simply because a simpler implementation could deliver the same functionality.

When a technology is not suitable for the main application, propose a separate experiment.

Explain technical concepts, trade-offs, and implementation decisions.

Avoid introducing unnecessary complexity into the core product solely to satisfy learning objectives.

---

## 11. Backend Architecture

### Preferred Stack

- Python.
- FastAPI.
- Pydantic.
- PostgreSQL.
- pgvector.
- LangGraph.
- AWS Bedrock.

### Backend Responsibilities

The backend should manage:

- Authentication and authorisation.
- Household membership.
- Shopping lists.
- Kitchen inventory.
- Recipe retrieval.
- Product catalogue integration.
- Grocery basket optimisation.
- Agent orchestration.
- LLM tool execution.
- Persistent agent state.
- Auditing.
- Evaluations.

### Architecture Principles

Maintain clear separation between:

- API routes.
- Request validation.
- Application services.
- Business rules.
- Agent orchestration.
- Tool execution.
- Data access.
- External integrations.

Prefer typed schemas, small focused services, and testable business logic.

Avoid unnecessary abstractions.

---

## 12. Data Sources and External Integrations

Investigate legitimate data sources for:

- Coles.
- Woolworths.
- Aldi.
- Recipe databases.
- Ingredient metadata.
- Nutritional information.

Before choosing integrations, verify:

- API capabilities.
- Authentication.
- Rate limits.
- Licensing.
- Commercial restrictions.
- Data freshness.
- Reliability.

Do not assume supermarkets provide unrestricted public APIs.

### Development Strategy

If reliable live supermarket data is unavailable, use a realistic simulated catalogue or licensed dataset.

The application must clearly label simulated prices.

Design provider integrations behind interfaces that allow real providers to be introduced later.

Do not block AI engineering development because live supermarket integrations are unavailable.

---

## 13. Authentication and Household Sharing

The application should support user accounts and shared households.

### Requirements

- Secure sign-in.
- Persistent user sessions.
- Household creation.
- Inviting household members.
- Shared shopping lists.
- Shared kitchen inventory.
- Household-specific preferences.
- User-level permissions.

Investigate an authentication solution compatible with Expo, React Native Web, and FastAPI.

All household data access must be authorised in the backend.

Do not rely on frontend checks for security.

### Synchronisation

Updates should be visible across devices.

Investigate:

- Real-time subscriptions.
- WebSockets.
- Managed real-time services.
- Optimistic UI updates.
- Conflict handling.
- Idempotent mutations.

Choose the approach during planning.

---

## 14. Human-in-the-Loop Approval

Human approval is a core AI engineering learning objective.

The agent should request approval before:

- Saving major meal plan changes when appropriate.
- Replacing an approved shopping basket.
- Making substantial shopping list modifications.
- Performing consequential external actions.

Use LangGraph interruption and resumption capabilities where appropriate.

### Approval Requirements

- Display proposed changes.
- Allow approval or rejection.
- Support modifications.
- Preserve agent state while awaiting approval.
- Resume execution after a decision.
- Record approvals and rejected actions.

Routine user-driven actions, such as manually ticking off a grocery item, should not require an unnecessary AI approval step.

---

## 15. AI Evaluation and Reliability

Treat evaluation as a core engineering responsibility.

### Evaluation Datasets

Create representative test scenarios covering:

- Simple meal planning.
- Complex dietary requirements.
- Tight budgets.
- Missing ingredients.
- Conflicting preferences.
- Unavailable products.
- Failed API calls.
- Incorrect tool arguments.
- Replanning.
- Human approval.
- Inventory inconsistencies.

### Metrics

Measure:

- Task completion rate.
- Tool selection accuracy.
- Retrieval relevance.
- Constraint compliance.
- Recommendation quality.
- Agent execution steps.
- Latency.
- Cost.
- Failure rate.
- Recovery success.

Compare the agent against simpler deterministic approaches where useful.

### Reliability

Implement:

- Tool timeouts.
- Retry policies.
- Execution limits.
- Checkpointing.
- Error handling.
- Idempotency.
- Structured logs.
- Graceful degradation.

Avoid unbounded agent execution.

---

## 16. Git Workflow and Pull Requests

Use a lightweight, professional Git workflow.

### Branching

- Keep `main` stable.
- Use feature branches for meaningful changes.
- Keep pull requests focused.
- Use descriptive commit messages.
- Remove merged branches.

Example branches:

- `feature/expo-foundation`
- `feature/authentication`
- `feature/shared-shopping-list`
- `feature/kitchen-inventory`
- `feature/recipe-rag`
- `feature/langgraph-agent`
- `feature/mcp-tools`
- `feature/basket-optimisation`
- `feature/agent-evaluations`
- `feature/aws-deployment`

### Pull Request Requirements

Each significant PR should include:

1. Summary of changes.
2. Important architecture decisions.
3. Technical trade-offs.
4. Tests performed.
5. Security and reliability considerations.
6. AI engineering concepts learned.

### Claude Code Git Rules

- Do not push without my approval.
- Do not create PRs without my approval.
- Do not automatically merge PRs.
- Do not force-push without explicit approval.
- Never commit secrets or credentials.
- Explain significant generated changes before review.

---

## 17. Testing and CI/CD

Use GitHub Actions for automated testing and validation.

### Frontend Testing

Investigate appropriate tools for:

- TypeScript checking.
- ESLint.
- Component tests.
- React Native tests.
- Web tests.
- iOS and Android build validation.
- End-to-end testing of critical user journeys.

### Backend Testing

Include:

- Python linting.
- Python type checking.
- Unit tests.
- Integration tests.
- API validation.
- Agent workflow tests.
- Tool validation.
- RAG evaluations.
- Security tests.

### Deployment

Investigate:

- Expo EAS Build.
- Expo EAS Update.
- iOS distribution.
- Android distribution.
- Web hosting.
- AWS backend deployment.
- Database migrations.
- CI/CD deployment pipelines.

Control paid model API usage in automated tests.

Do not run expensive LLM evaluations unnecessarily on every commit.

---

## 18. AI-Assisted Development

I will use Claude Code extensively to accelerate development.

However, Claude should also act as an experienced AI engineering mentor.

### Developer Background

I am a mid-level full-stack software engineer.

My experience includes:

- React.
- Next.js.
- TypeScript.
- Python.
- FastAPI.
- PostgreSQL.
- REST APIs.
- AWS integrations.
- LLM APIs.
- Agentic applications.

I previously built an AI website builder called SuperNinja.

I am familiar with software engineering fundamentals but want to deepen my AI engineering knowledge.

I am also learning Expo and React Native, so explain important platform-specific differences from React and Next.js.

### Teaching Expectations

When introducing unfamiliar concepts:

1. Explain what the technology does.
2. Explain why it is needed.
3. Explain how it works.
4. Compare reasonable alternatives.
5. Discuss technical trade-offs.
6. Identify security and reliability concerns.
7. Explain how to test and evaluate it.

Keep explanations concise and practical.

Do not turn routine implementation into lengthy tutorials.

### After Major AI Features

Provide:

- Architecture summary.
- Execution flow.
- Important files and functions.
- Key engineering decisions.
- Failure scenarios.
- Testing strategy.
- Evaluation approach.
- Relevant AI engineering interview questions.

Help me understand the implementation rather than blindly accepting generated code.

### Development Speed

Do not artificially stretch implementation across 12 weeks.

Use AI-assisted development to move quickly.

The learning roadmap represents the period allocated to technical development and experimentation, not the expected MVP build duration.

Use additional time to deepen understanding, compare implementations, and improve reliability.

---

## 19. Planning with Grill with Docs

I will use Matt Pocock's Grill with Docs skill to plan this application.

This is the only planning skill I intend to use.

Follow the installed skill's actual instructions.

### Planning Process

Use Grill with Docs to:

1. Challenge and clarify the product requirements.
2. Identify missing requirements and assumptions.
3. Investigate grocery and recipe data availability.
4. Define the MVP and scope.
5. Plan the Expo and React Native architecture.
6. Investigate cross-platform compatibility.
7. Define authentication and household sharing.
8. Design shopping list and inventory synchronisation.
9. Design the LangGraph agent architecture.
10. Determine tool calling and MCP integrations.
11. Define the backend and database architecture.
12. Plan RAG and recommendation systems.
13. Establish security and approval requirements.
14. Define evaluation and testing strategies.
15. Document technical decisions and trade-offs.
16. Produce an implementation plan.

### Confirmed Decisions

The following requirements have already been decided:

- Use Expo and React Native.
- Target iOS, Android, and web.
- Use a shared frontend codebase where practical.
- Use Python and FastAPI for the backend.
- Build a genuine LangGraph agent.
- Support dynamic tool selection.
- Include a shared grocery shopping list.
- Include automatic kitchen inventory updates.
- Build RAG and recommendation capabilities.
- Develop the AI engineering skills in the learning roadmap.
- Use feature branches and pull requests.
- Use GitHub Actions for CI/CD.

Challenge implementation details, but do not repeatedly reopen confirmed product decisions without identifying a material technical problem.

### Agent Requirement

The agentic architecture is mandatory.

Do not replace the agent with a deterministic workflow during planning.

Deterministic backend services should still handle calculations, validation, permissions, and critical business rules.

---

## 20. MVP Scope

The initial MVP should demonstrate one complete user journey.

### Essential Features

- Expo application running on iOS and web.
- User authentication.
- Basic household support.
- Shared grocery list.
- Marking items as purchased.
- Automatic kitchen inventory updates.
- Manual inventory corrections.
- Natural-language meal planning.
- LangGraph agent with dynamic tool selection.
- Recipe retrieval.
- Ingredient calculations.
- Basic grocery basket optimisation.
- Budget validation.
- User approval of proposed changes.
- Basic tracing and error handling.

Android compatibility should be considered from the start and validated during development.

Using a simulated supermarket catalogue is acceptable.

### Later Enhancements

- Advanced real-time synchronisation.
- Full offline shopping-list support.
- Live supermarket integrations.
- Advanced recommendation algorithms.
- Hybrid RAG and re-ranking.
- More sophisticated shopping optimisation.
- Expiry date tracking.
- Recipe-based inventory consumption.
- Push notifications.
- Advanced MCP integrations.
- Multi-agent experiments.
- Advanced evaluation dashboards.

Learning-focused technologies may be implemented earlier than their normal product priority when appropriate.

---

## 21. Portfolio and Career Objectives

The final project should demonstrate:

- Full-stack AI engineering.
- Cross-platform application development.
- Python and FastAPI.
- LangGraph agent orchestration.
- MCP and tool calling.
- Advanced RAG.
- Applied machine learning.
- Human-in-the-loop workflows.
- Secure backend integrations.
- Shared application state.
- Real-time synchronisation.
- LLM evaluations.
- Observability and audit trails.
- AWS Bedrock.
- Cloud deployment.
- GitHub Actions and CI/CD.
- Automated testing.
- Professional Git workflows.

Record meaningful architecture decisions and measurable results.

Do not invent performance improvements.

Do not claim commercial production experience that has not occurred.

The goal is to demonstrate practical AI engineering ability and confidently explain the architecture in technical interviews.

---

## 22. Initial Instructions for Claude

Before writing application code:

1. Read `PRODUCT_BRIEF.md`.
2. Read `AI_LEARNING_ROADMAP.md`.
3. Read the project's `CLAUDE.md`.
4. Use Grill with Docs to clarify requirements and challenge assumptions.
5. Investigate current Expo and React Native capabilities.
6. Confirm the cross-platform architecture.
7. Investigate recipe and grocery data sources.
8. Define the initial MVP.
9. Design the LangGraph agent architecture.
10. Define tools, state management, and persistence.
11. Design the shopping list and kitchen inventory model.
12. Plan household sharing and synchronisation.
13. Define the backend architecture.
14. Establish testing and evaluation requirements.
15. Produce an implementation plan.
16. Identify how each implementation stage supports the AI learning roadmap.

Do not begin full implementation until planning is complete.

The priority is to build a useful, reliable, cross-platform AI grocery shopping agent while developing transferable, production-oriented AI engineering skills.
