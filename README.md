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
- Fake/OpenAI worksheet analyzers with strict structured output
- background analysis jobs and persisted `WorksheetResult` retrieval
- backend and frontend tests
- threshold-based independent verification for low-confidence or self-checked problems

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

## AI provider

Development defaults to the deterministic fake analyzer. To call OpenAI, set:

```bash
NOTESOLVE_AI_PROVIDER=openai
NOTESOLVE_OPENAI_API_KEY=your-key
NOTESOLVE_OPENAI_MODEL=gpt-5.4
# Optional: use a separate model and tune the verification trigger.
NOTESOLVE_OPENAI_VERIFICATION_MODEL=gpt-5.4
NOTESOLVE_VERIFICATION_THRESHOLD=0.9
NOTESOLVE_VERIFICATION_ENABLED=true
```

Upload a file, start analysis with `POST /api/v1/jobs/{job_id}/analyze`, and retrieve the
structured result from `GET /api/v1/documents/{document_id}/result`.
