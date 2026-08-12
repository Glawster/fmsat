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

### Phase 3 — Tactical parser (In Progress)

Phase 3 turns the captured tactical screens into a current structured tactic,
then defines the requirements needed to assess players against it:

1. read Formation, In Possession and Out of Possession captures;
2. normalize formation slots, positions, roles, duties and team instructions;
3. build and persist the reviewable current tactic;
4. define generic role requirements and attribute weighting;
5. apply explicit tactic modifiers without changing generic role definitions;
6. expose deterministic and explainable inputs for role-centric assessment.

[Requirement 006](requirements/features/006-structuredTacticExtraction.md) owns
steps 1–3. [Requirement 010](requirements/features/010-positionAttributeRoleDefinitions.md)
owns steps 4–6. [Requirement 007](requirements/features/007-roleCentricSquadAssessment.md)
consumes their outputs after these foundations are ready.
