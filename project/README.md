# FMSAT project records

- [Requirements](requirements/README.md)
- [Architecture decision records](adr/)

Product requirements and their source prompts are retained here as stable project
records. Living implementation and user guidance belongs in `../documentation/`.

## Phase status

### Phase 2 — Complete (2026-08-06)

The data-management foundation is complete: managed screenshot persistence,
source screenshot viewing, tactic and squad lists, safe owner deletion, adaptive
squad capture, editable OCR review, persisted-squad cleanup and immediate
post-edit validation are implemented.

Completion evidence: the FMSAT automated suite passes with the Phase 2 database,
UI lifecycle, screenshot provenance, OCR validation and cleanup coverage; Ruff
and `git diff --check` also pass. Screenshot-level selective removal and the
full player examination UI remain later requirement work.
