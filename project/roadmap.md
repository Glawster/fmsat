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
- user-reviewed factual role definitions;
- OCR-role to tactical-vocabulary consistency checking; and
- a model-backed tactic viewer.

The current FM26 reference tactic regenerates with 11 In Possession and 11 Out Of
Possession roles, including canonical SS, HB and DDM handling.

Remaining Phase 3 work is non-blocking for squad assessment:

- structured-tactic correction and diagnostic CLI completion under requirement 006;
- immutable revision history and comparison under requirement 009; and
- broader role/position knowledge and tactical modifiers under requirement 010.

## Phase 4 — Squad assessment

Current development phase.

### 007A — Generic Role Fit foundation — complete

Delivered:

- a squad viewer using the tactic viewer's visual language;
- Overview, Players, Roles and Analysis views;
- complete, versioned Generic Role Fit weights for every canonical tactic role;
- deterministic all-player role calculations;
- transparent weighted contribution traces;
- explicit `Unavailable` states for incomplete evidence;
- role/candidate browsing and player-role assessment;
- initial required-role depth and squad findings;
- common QSS-owned dropdown styling; and
- surname-sorted player selection displayed as `Surname, Firstname`.

### 007B — Role-depth and player-role analysis — implemented

Delivered:

- the complete all-player/all-role matrix;
- unique-player assignment across simultaneous required tactical slots;
- best candidate, backup and uncovered roles;
- each player's best and alternative roles;
- weak positions, concentrated role duplication and unused squad strengths; and
- transparent evidence for every score and finding.

### 007C — Best XI and clean-room stabilization — acceptance

Delivered implementation includes:

- a global unique-player Best XI constrained by captured position families;
- robust simultaneous-slot analysis that isolates malformed phase evidence;
- player identity reconciliation and durable manual corrections;
- incremental squad import/merge, player editing and removal;
- 0–10 role-assessment policy editing and validated YAML transfer; and
- role/vocabulary, OCR and welcome/import lifecycle regressions found during
  clean-room use.

Final full-suite, opt-in OCR and manual reference-squad acceptance remain.

Later requirement 007 increments:

- Tactical Fit and Position Familiarity;
- Overall Suitability;
- competition-level role attribute benchmarks once an evidence model exists;
- candidate comparison;
- Role Health;
- recruitment analysis built on confirmed assessment results.

## Future

- match analysis;
- training recommendations;
- reporting;
- recruitment planning; and
- tactical comparison beyond factual revision differences.
