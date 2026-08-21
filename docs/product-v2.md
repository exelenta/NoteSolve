# NoteSolve Product V2

## Product identity

NoteSolve converts scanned learning documents into source-faithful Markdown and stores approved
notes in an Obsidian Vault. Question solving, blank filling, explanation, and verification are
context-aware assistance modes—not the shape forced onto every document.

## Analysis behavior

- Accept 1–30 ordered JPG, PNG, or PDF inputs as one document.
- Auto-detect subject, unit, title, and document kind; an optional subject hint takes precedence
  only when compatible with the visible source.
- Preserve headings, paragraphs, lists, tables, definitions, examples, exercises, blanks, quotes,
  and callouts as ordered blocks with source-page references.
- Never convert ordinary prose into questions. Unreadable text becomes `[판독 불가]` with a
  warning and lower confidence instead of invented content.
- Verify only discrete, checkable exercises. Concept notes and reference text bypass verification.

## User controls

| Control | Values | Default |
|---|---|---|
| Subject | Auto-detect or free text | Auto-detect |
| Help | Source only, answers, concise, detailed | Concise |
| Layout | Source-faithful, study notes, summary | Source-faithful |
| Language | API option, initially Korean UI | Korean |
| Custom instruction | Up to 2,000 characters | Empty |

## Device support

The web UI is responsive from 320 px phones through tablets and desktop. File input supports
mobile cameras and photo libraries through the platform browser, while PDF and multi-select
availability follows the OS picker. A later PWA phase can add installability and queued uploads.

## Next side features

1. Page reorder/remove and per-page rotation/crop before upload.
2. Saved presets per subject (for example, English bilingual notes or history timelines).
3. Markdown diff before Vault approval and inline correction of low-confidence blocks.
4. Cost estimate before analysis, page-level retry, and resumable uploads for server operation.
5. Cross-note backlinks, glossary extraction, spaced-repetition cards, and duplicate-note merge.
6. PWA offline upload queue, authentication, object storage, and background workers for hosted use.

These remain side capabilities. They must not compromise source fidelity or the approval boundary
around Vault writes.
