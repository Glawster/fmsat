# Development status

Last updated: 2026-08-16

## Current delivery point

The working tactic and role-definition workflow establishes the boundary between
Phase 3 tactical knowledge and Phase 4 squad assessment.

The application can now import the three supported tactic screenshots, extract
observed formation and instruction evidence, resolve missing factual role
definitions through user review, generate the football object model and redraw
that model in the tactic viewer. Players visible in a tactic screenshot remain
source evidence and are not treated as tactic assignments.

## Completed requirements

| ID | Requirement | Status |
| --- | --- | --- |
| 002 | Clipboard screenshot guidance | Completed |
| 008 | Welcome screen | Completed |

## Operational Phase 3 baseline

### Requirement 006 — Structured tactic extraction

The end-to-end workflow is operational:

- anchored Formation, In Possession and Out of Possession OCR;
- observed-only formation and selected-instruction extraction;
- canonical position, role and instruction normalization;
- explicit unresolved evidence and integrity-gated regeneration;
- screenshot-derived persistence and football object-model generation;
- missing-role detection and user-assisted factual role acquisition;
- freshness detection, diagnostics and safe retention of an existing model when
  regeneration fails.

A tactic-processing regression exposed that effective OCR recognition geometry
can degrade even when normalized configured regions are unchanged. OCR geometry
stabilisation is therefore the current extraction priority. FMSAT now has an
append-only geometry-history layer and median/MAD drift classifier so validated
zone observations can establish normal historical variation while anomalous or
unvalidated observations are retained without teaching the baseline. The
currently accepted FM26 geometry is also protected by regression tests. See
[OCR zone geometry history](ocrZoneGeometry.md).

Requirement 006 remains `InProgress` until its remaining correction, diagnostic
CLI, acceptance-test and documentation criteria are either delivered or
explicitly deferred. Wiring effective anchor-derived panel/card observations
into every successful extraction and surfacing `ocrZoneDrift` diagnostics is the
next step in this stabilisation increment.

### Requirement 009 — Tactic detail management

The tactic viewer baseline is delivered and accepted for current use. It
provides model-backed Overview, Shape, Instructions and Analysis views,
validation diagnostics, regeneration and squad assignment without reopening
screenshots during normal viewing.

Requirement 009 remains `InProgress` for immutable revision history, historical
revision selection and structured comparison. These items do not block the
squad-viewer work.

### Requirement 010 — Position, attribute and role definitions

The evidence-driven role-definition workflow is operational. Confirmed user
definitions can resolve tactic knowledge gaps without converting displayed
player ratings into role policy.

Requirement 010 remains `InProgress` for the assessment layer: the complete
attribute and position knowledge graph, role requirement profiles, tactical
modifiers, scoring policy, version identity and calculation traces.

## Active next requirement

### Requirement 007 — Role-centric squad assessment

Requirement 007 remains `InProgress`. Its squad-viewer foundation was merged
through PR 5 and provides Overview, Players, Roles and Analysis views in the same
visual family as the tactic viewer.

007A establishes the Generic Role Fit policy foundation: explicit weights for
all canonical roles, exact catalogue validation, missing-evidence unavailable
states and transparent weighted calculations. The assessment identity remains
the unique canonical role, not the formation position or slot. Position remains
supporting eligibility context.

007B — complete all-player role calculation, player best/alternative roles and
role-depth analysis — is deliberately postponed while tactic OCR geometry is
stabilised. Dependable squad analysis must not be built on silently degraded
source extraction.

Implementation continues on `feature/007-squad-viewer`. The editable squad model
keeps OCR evidence intact and marks it superseded when a user saves corrected
values.

## Deferred work

- Requirement 007B all-player role matrix and role-depth analysis until OCR
  geometry stabilisation is complete.
- Requirement 009 immutable tactic revisions and comparison.
- Requirement 006 general structured-tactic correction and diagnostic CLI.
- Requirement 003 and 004 final acceptance and traceability review.
- Requirement 005 standalone palette and icon completion where the existing
  shared tactic colours do not yet satisfy its criteria.

## Technical debt

- Remove generated egg-info from the repository.
- Move parser modules into a dedicated package where compatibility permits.
- Split `MainWindow` into workflow controllers.
- Replace remaining prototype revision controls with persisted revision data
  when requirement 009 resumes.
