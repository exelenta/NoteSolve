# NoteSolve

NoteSolve turns worksheet photos or PDFs into structured, reviewable solutions and Obsidian-ready notes.

## Day 1 foundation

The current foundation provides:

- React upload UI
- FastAPI health, document upload, and job-status APIs
- SHA-256 duplicate detection
- SQLite persistence with Alembic migrations
- local object storage using portable storage keys
- replaceable analyzer, storage, job-runner, and Vault interfaces
- backend and frontend tests

## Prerequisites

- Python 3.12+
- uv
- Node.js 22+
- pnpm 10+

## Setup

```bash
cp .env.example .env
uv sync
pnpm install
uv run alembic upgrade head
```

Run the API:

```bash
uv run uvicorn notesolve.main:app --app-dir apps/api --reload
```

Run the web app in another terminal:

```bash
pnpm dev
```

Open `http://localhost:5173`.

## Checks

```bash
uv run ruff check apps/api
uv run mypy apps/api/notesolve
uv run pytest
pnpm check
pnpm test
pnpm build
```

Uploaded files and the local SQLite database are stored under `.notesolve-data/` by default.

