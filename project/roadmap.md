# Roadmap

FMSAT is developed incrementally so that each stage produces reviewable,
explainable and testable data before the next layer consumes it.

## Phase 1 — Squad extraction

Completed:

- squad-attribute OCR;
- player extraction;
- validation and review;
- SQLite persistence; and
- historical screenshot storage.

## Phase 2 — Workspace and workflow

Completed baseline:

- welcome workspace;
- tactic and squad management;
- screenshot provenance;
- clipboard workflow; and
- persistent user data.

Requirements 003 and 004 still require a final acceptance and traceability
review before their records can be marked completed.

## Phase 3 — Structured tactical knowledge

Operational baseline delivered:

- anchored tactic screenshot extraction;
- formation-slot and selected-instruction extraction;
- canonical tactical vocabulary;
- evidence-preserving screenshot-derived definitions;
- integrity-gated football object-model generation;
- model freshness and regeneration;
- missing-role detection;
- user-reviewed factual role definitions; and
- a model-backed tactic viewer.

Remaining Phase 3 work is non-blocking for the squad-viewer start:

- structured-tactic correction and diagnostic CLI completion under requirement
  006;
- immutable revision history and comparison under requirement 009; and
- the assessment-policy portion of requirement 010, which will be delivered as
  the squad assessment consumes it.

## Phase 4 — Squad assessment

Current development phase.

First increment:

- a squad viewer using the tactic viewer's visual language;
- explicit squad, tactic revision and knowledge-version context;
- Overview, Players and Roles views;
- configuration-driven Generic Role Fit;
- reproducible score explanations and unavailable states; and
- initial starter, backup and uncovered-role assessment.

Later increments:

- Tactical Fit and Position Familiarity;
- Overall Suitability;
- candidate comparison;
- alternative-role ranking;
- Role Health;
- squad depth and Best XI; and
- recruitment analysis built on confirmed assessment results.

## Future

- match analysis;
- training recommendations;
- reporting;
- recruitment planning; and
- tactical comparison beyond factual revision differences.
