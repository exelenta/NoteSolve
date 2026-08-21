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
- threshold-based independent verification for low-confidence or review-required problems
- safe Markdown and LaTeX rendering in the review UI
- approval-required Obsidian ChangeSet previews with subject/unit folder classification
- persisted Vault ChangeSets with explicit apply, conflict detection, revision history, and rollback
- asynchronous AI note-edit jobs that produce approval-required update ChangeSets
- retry-aware OpenAI Responses client with persisted token usage
- startup recovery for interrupted analysis and agent jobs
- versioned worksheet evaluation fixtures

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
NOTESOLVE_OPENAI_NOTE_EDITOR_MODEL=gpt-5.4
NOTESOLVE_OPENAI_MAX_RETRIES=2
NOTESOLVE_VERIFICATION_THRESHOLD=0.9
NOTESOLVE_VERIFICATION_ENABLED=true
```

Upload a file, start analysis with `POST /api/v1/jobs/{job_id}/analyze`, and retrieve the
structured result from `GET /api/v1/documents/{document_id}/result`.

Generate a read-only Obsidian preview with
`GET /api/v1/documents/{document_id}/vault-preview`. The response is a ChangeSet marked
`requires_approval=true`.

To persist and approve a Vault change:

```text
POST /api/v1/documents/{document_id}/vault-change-sets
POST /api/v1/vault-change-sets/{change_set_id}/apply
POST /api/v1/vault-change-sets/{change_set_id}/rollback
```

Set `NOTESOLVE_VAULT_DIR` to an existing Obsidian Vault path. If omitted, development uses
`.notesolve-data/vault`. Apply and rollback both reject the operation if the target file changed
since the expected revision.

## AI note edits

After a Vault ChangeSet has been applied, request a natural-language edit:

```text
POST /api/v1/vault-change-sets/{change_set_id}/edit-proposals
GET  /api/v1/agent-edit-jobs/{job_id}
```

The agent receives the current Markdown and returns a complete revised note through a strict
structured-output schema. It cannot choose or change the Vault path. The resulting update is
stored as another pending ChangeSet and still requires explicit approval before any file write.

## Reliability and usage

OpenAI calls retry transient HTTP 408, 409, 429, and 5xx responses with capped exponential
backoff. Responses API input, output, and total token counts are persisted for worksheet analysis
and note-edit jobs and returned by their APIs. On startup, jobs interrupted by a previous process
shutdown are moved to an explicit failed state so the UI can offer a retry instead of polling
forever.

Versioned quality cases live under `evals/worksheet/` and run with the backend test suite.
