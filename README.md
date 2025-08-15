# BEAT Every Day — Strava-first MVP (Strava-only)

FastAPI backend + PostgreSQL + Strava OAuth & Webhooks.

See the ChatGPT canvas for full context. Quick start:
1. `cp .env.example .env` and fill values
2. `docker compose up -d db`
3. `poetry install && poetry run alembic upgrade head`
4. `poetry run uvicorn app.main:app --reload`
