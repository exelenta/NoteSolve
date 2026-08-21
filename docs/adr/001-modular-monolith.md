# ADR 001: Modular monolith

## Decision

NoteSolve starts as a FastAPI modular monolith. Domain modules communicate through explicit application interfaces.

## Why

This supports a ten-day MVP without making future worker or server extraction prohibitively expensive.

## Consequences

Module boundaries and infrastructure adapters are mandatory even though deployment initially uses one process.

