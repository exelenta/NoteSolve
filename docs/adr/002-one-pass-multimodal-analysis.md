# ADR 002: One-pass multimodal analysis

## Decision

The default path sends the worksheet image or PDF directly to a capable multimodal model and requests a strict `WorksheetResult`.

## Why

It reduces the MVP pipeline and preserves the quality observed in consumer multimodal chat products.

## Consequences

Low-confidence problems require optional independent verification. Traditional OCR remains a future adapter.

