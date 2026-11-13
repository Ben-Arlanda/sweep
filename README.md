# Sweep

AI grocery shopping and meal-planning app: a shared Shopping List, a Cabinet of what you have at home, and a Recipe Knowledge Base, connected by a LangGraph agent.

Planning docs: [`CONTEXT.md`](CONTEXT.md) (domain language) · [`docs/plan.md`](docs/plan.md) (architecture) · [`docs/adr/`](docs/adr/) (decisions)

## Layout

```
apps/client/     Expo app (iOS · web · Android)
services/api/    FastAPI backend (Python, uv)
```

## Run locally

```bash
docker compose up -d                                   # Postgres + pgvector
cd services/api && uv sync && uv run fastapi dev app/main.py   # API on :8000
cd apps/client && npm install && npx expo start        # press w for web, scan QR with Expo Go for iPhone
```

On a real iPhone, `localhost` means the phone itself. Set `EXPO_PUBLIC_API_URL` in `apps/client/.env.local` to your Mac's LAN IP (e.g. `http://192.168.1.20:8000`), and run the API with `--host 0.0.0.0`.
