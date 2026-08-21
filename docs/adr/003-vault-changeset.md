# ADR 003: Vault changes require ChangeSets

## Decision

No analyzer or chat agent may write directly to an Obsidian Vault. Every write is represented as a previewable and reversible ChangeSet.

## Why

The user's Vault is the durable source of truth and must be protected from silent AI overwrites.

## Consequences

All Vault adapters must implement conflict detection, approval, revision recording, and rollback.

