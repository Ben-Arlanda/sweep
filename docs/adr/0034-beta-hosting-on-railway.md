# 0034: Beta hosting on Railway, AWS later

Date: 2026-11-22. Status: accepted. Splits slice 11: 11a (this) before 11b (AWS + Bedrock).

## Context

TestFlight ships only the app. The API ran on the product owner's Mac at a home Wi-Fi address, so no tester elsewhere could use it. Slice 11 (ECS, RDS, Secrets Manager, S3, Bedrock) is 3–5 days and about $50–90 a month, which a beta with few users doesn't need.

## Decision

1. **The API runs as one Docker container on Railway** (`services/api/Dockerfile`, `railway.json`), with Railway's Postgres (pgvector) in the same project. One copy only (`numReplicas: 1`).
2. **Migrations run before each deploy** (`preDeployCommand: alembic upgrade head`); a failed migration stops the deploy, and the old version keeps serving. `/health` is the health check.
3. **Secrets are Railway variables**, never files in the image (`.dockerignore` drops `.env`).
4. **Member photos live on a Railway volume** at `/data` (`PHOTO_DIR=/data/photos`, ADR 0031's folder store), so redeploys keep them. The container runs as root because the volume is root-owned.
5. **Seed Recipes are loaded once from the Mac** (`python -m app.seed_recipes` against Railway's public database URL), not on every deploy: embedding calls a paid API.
6. **Bedrock is not part of the beta**: the Anthropic API already works. AWS and Bedrock stay a learning goal for 11b, which can copy this Dockerfile.

## Consequences

- Live in about a day, roughly $5–20 a month for hosting; AI calls stay the larger cost, capped by the daily budget per Household.
- Railway runs amd64. The arm64 image crashes on Apple Silicon (`cryptography` dies with "Illegal instruction"), so local checks use `--platform linux/amd64`.
- One copy and one volume: no high availability. Fine for a beta; S3 and several copies come with 11b.
- Pillow moved from dev to runtime dependencies: Member photos need it, and the image installs no dev packages.
