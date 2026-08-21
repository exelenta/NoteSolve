# NoteSolve development rules

- Keep domain and application code independent from concrete AI SDKs.
- Put external integrations behind Protocols and adapters.
- Never modify the original uploaded file.
- Never modify an Obsidian Vault outside `VaultRepository`.
- Store portable `storage_key` values instead of absolute filesystem paths.
- Add an Alembic migration for every database schema change.
- Return a `job_id` for long-running operations.
- Version prompts, structured-output schemas, and AI evaluation fixtures.
- Regenerate the TypeScript API client after changing the OpenAPI contract.
- Do not weaken tests to make a change pass.
- Run lint, type checking, and tests before declaring work complete.

