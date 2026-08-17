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

### Phase 3 — Structured tactical knowledge (Operational baseline)

The current baseline reads Formation, In Possession and Out Of Possession captures,
normalizes formation slots, positions, roles and team instructions, persists
screenshot-derived evidence, builds the football object model and supports factual
role-definition review. OCR geometry history, regeneration integrity gates and canonical
role-vocabulary checks protect the evidence consumed by later analysis.

Requirements 006, 009 and 010 retain follow-on work, but no known Phase 3 defect currently
blocks requirement 007B.

### Phase 4 — Role-centric squad assessment (In Progress)

[Requirement 007](requirements/features/007-roleCentricSquadAssessment.md) is the active
product increment.

007A is complete and ready to merge: Generic Role Fit policy, all-player role scoring,
transparent calculation traces, unavailable states, role/candidate browsing, player-role
assessment and initial role-depth analysis are implemented on top of the stable tactic
evidence baseline.

007B is next and will refine required-role depth using unique-player assignment across
simultaneous tactical slots, then surface best/backup/uncovered roles, player best and
alternative roles, weak positions, role duplication and unused squad strengths.

Best XI, Tactical Fit and recruitment analysis remain later increments.
