# Development status

Last updated: 2026-08-26

## Current delivery point

The active increment is **007C — Best XI and clean-room stabilization**. Its implementation
combines global Best XI assignment with position-family eligibility and a broad set of
clean-room fixes across squad evidence, role policy, OCR and import/window lifecycle.

FMSAT can import the supported tactic screenshots, extract and validate 11 In Possession
and 11 Out Of Possession slots, normalize canonical tactic roles and instructions, retain
unresolved evidence rather than guessing, build the football object model, and regenerate
from retained screenshots. Canonical tactic vocabulary now includes the roles encountered
in the current FM26 reference tactic, including SS, HB and DDM, and startup performs an
internal cross-check between OCR-confirmed role definitions and tactical vocabulary.

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
  regeneration fails;
- FM26 formation recovery through the full pitch, including CB and GK rows;
- rejection of formation candidates without role-label evidence; and
- vocabulary reconciliation for roles already known by FMSAT.

OCR geometry history remains part of the operational baseline. See
[OCR zone geometry history](ocrZoneGeometry.md).

Requirement 006 remains `InProgress` for its remaining correction, diagnostic CLI and
acceptance/documentation criteria, but no known tactic-extraction defect currently blocks
007C acceptance.

### Requirement 009 — Tactic detail management

The tactic viewer baseline is delivered and accepted for current use. It provides
model-backed Overview, Shape, Instructions and Analysis views, validation diagnostics,
regeneration and squad assignment without reopening screenshots during normal viewing.

Requirement 009 remains `InProgress` for immutable revision history, historical revision
selection and structured comparison. These items do not block squad assessment.

### Requirement 010 — Position, attribute and role definitions

The evidence-driven role-definition workflow is operational. Confirmed user definitions can
resolve tactic knowledge gaps without converting displayed player ratings into role policy.
The canonical vocabulary and Generic Role Fit policy now cover all currently supported
canonical tactic roles, and confirmed OCR role definitions are checked against that catalogue
at startup.

Requirement 010 remains `InProgress` for the broader knowledge graph, tactical modifiers and
future competition-level benchmark policy.

## Requirement 007 — Role-centric squad assessment

### 007A — Generic Role Fit foundation

007A is complete.

Delivered:

- explicit Generic Role Fit weights for every canonical tactic role;
- deterministic all-player role scoring with transparent weighted breakdowns;
- `Unavailable` states whenever required evidence is missing;
- role and candidate browsing in the Squad Workspace;
- player role assessment with surname-sorted `Surname, Firstname` selection;
- initial required-role depth, best-role and squad-finding presentation;
- tactic role vocabulary reconciliation, including SS, HB and DDM;
- stable regeneration of the current FM26 reference tactic with 11 IP and 11 OOP slots;
- common QSS-owned workspace dropdown styling; and
- regression coverage for the assessment, OCR and presentation contracts.

The full automated pytest suite passed after the final UI and vocabulary changes.

### 007B — Role-depth and player-role analysis

007B is implemented. It provides unique-player simultaneous role depth, best and alternative
roles, squad findings, factual Player Editor corrections and persisted active-tactic context.

### 007C — Best XI and clean-room stabilization

007C is implemented and under final clean-room acceptance. Delivered areas include:

- global Best XI assignment using position-family eligibility;
- isolation of an incomplete or malformed phase slot without discarding otherwise linked
  simultaneous slots;
- conservative cross-capture player identity/name reconciliation with visible uncertainty
  and durable manual corrections;
- incremental filtered-squad import/merge, player editing and removal;
- a 0–10 Role Assessment Weight Editor with validated YAML policy import/export;
- role policy, position compatibility and vocabulary corrections;
- welcome/import/reassessment lifecycle fixes; and
- focused, opt-in OCR and clean-room regression fixtures.

Requirement 007 remains `InProgress`. Tactical Fit, Overall Suitability, candidate comparison
and Role Health are not delivered by 007C.

## Deferred work

- Requirement 009 immutable tactic revisions and comparison.
- Requirement 006 general structured-tactic correction and diagnostic CLI completion.
- Requirement 003 and 004 final acceptance and traceability review.
- Requirement 005 standalone palette and icon completion where the shared workspace styling
  does not yet satisfy its criteria.
- Competition-level role attribute benchmarks until an explicit evidence/model is defined.

## Technical debt

- Remove generated egg-info from the repository.
- Move parser modules into a dedicated package where compatibility permits.
- Split `MainWindow` into workflow controllers.
- Replace remaining prototype revision controls with persisted revision data when
  requirement 009 resumes.
