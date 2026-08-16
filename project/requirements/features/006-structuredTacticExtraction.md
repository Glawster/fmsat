# 006 — Structured tactic extraction

## Status

InProgress

The end-to-end extraction, role-gap and model-generation workflow is
operational. Completion remains open for the general correction workflow,
diagnostic CLI, final acceptance verification and documentation reconciliation.
The current stabilisation work additionally verifies anchor-relative Team
Instructions extraction against newer FM26 captures before requirement 007B
consumes the resulting tactic evidence.

## Objective

Convert a stored tactic's Formation, In Possession and Out of Possession
screenshots into typed, reviewable, correctable and persistent tactical data.
The resulting structured tactic must be trustworthy enough for later player
suitability and recruitment analysis, but those analyses are not part of this
requirement.

## Tactical domain model

1. Represent the three tactical phases explicitly: Formation, In Possession and
   Out of Possession.
2. Represent every visible formation slot with a stable slot identifier,
   tactical phase, canonical position, canonical role, duty, normalized pitch
   coordinates, optional displayed player, extraction confidence, source import
   session and validation state.
3. Preserve useful original OCR text alongside canonical values so corrections
   and extraction issues remain explainable.
4. Represent each team instruction with its phase, category, canonical value,
   display value, confidence, source import and validation state.
5. Represent a structured tactic with its identity, name, phase-specific slots,
   instructions, extraction issues, completeness and confirmation state.
6. Keep typed tactical domain objects separate from SQLAlchemy persistence
   models and Qt widgets.
7. Persist only values actually observed by an extractor or explicitly supplied
   and confirmed by the user. Missing slot or instruction extraction must create
   unresolved issues; templates, neutral defaults and formation-to-phase copying
   must not be persisted as extracted facts.
8. A player displayed in a Formation screenshot is extraction evidence only.
   It may be retained in `ScreenshotDerivedTacticDefinition` and used transiently
   to link the same slot across phases, but it must not become a player assignment
   in the reusable football object model. Player assignments require a separate,
   explicit squad-assignment action. Duplicate or imperfect displayed-player OCR
   must not by itself invalidate the reusable tactic definition.
9. FMSAT owns tactic identity. The legacy/template formation label displayed by
   Football Manager is not tactic identity and is not required extraction
   evidence. The generated football object model derives its phase formation
   names from the user-owned tactic name as `<tactic name> IP` and
   `<tactic name> OOP`.

## Canonical vocabulary

1. Define positions, roles, duties and team instructions in reusable YAML
   configuration rather than scattering display strings through code.
2. Support aliases and known OCR variants while preserving the observed text.
3. Support canonical duties `DEFEND`, `SUPPORT`, `ATTACK`, `AUTOMATIC` and
   `NONE`.
4. Include the positions and roles visible in supported FM26 fixtures, including
   goalkeeper, defensive, defensive-midfield, midfield, attacking-midfield and
   striker variants.
5. Each role definition must provide a code, display name, abbreviations,
   allowed positions and supported duties.
6. Unknown aliases must create review issues rather than crashes or invented
   tactical meaning.

The initial canonical position vocabulary must include:

`GK`, `DR`, `DCR`, `DC`, `DCL`, `DL`, `WBR`, `DMCR`, `DM`, `DMCL`, `WBL`,
`MR`, `MCR`, `MC`, `MCL`, `ML`, `AMR`, `AMCR`, `AMC`, `AMCL`, `AML`, `STCR`,
`STC` and `STCL`.

The initial role vocabulary must include observed FM26 identities for:

- Ball-Playing Goalkeeper and Sweeper Keeper;
- Full-Back, Wing-Back, Centre-Back and Ball-Playing Centre-Back;
- Deep-Lying Playmaker, Box-to-Box Midfielder, Defensive Midfielder and
  Pressing Defensive Midfielder;
- Wide Midfielder, Winger, Inside Forward and Attacking Midfielder; and
- Centre Forward, Target Forward, Channel Forward and Tracking Centre
  Forward.

Use the actual FM26 display names and abbreviations confirmed by fixtures. The
vocabulary must not infer attribute weights or behavior that is not observable
from those fixtures.

## Formation extraction

1. Extend the existing tactic parser while preserving Phase 2 tactic identity
   and public behavior.
2. Extract mentality from the Formation screenshot when available. Do not
   require or validate Football Manager's legacy/template formation label;
   FMSAT's user-owned tactic name is authoritative identity.
3. Use screen-specific parsers with shared reusable components where useful.
4. Locate the tactic window from the stable `Squad > Tactics Planner`
   breadcrumb, then apply normalized configurable pitch regions inside that
   detected reference frame. Desktop resolution, Steam window position and
   unrelated surrounding UI must not determine tactical geometry.
5. Formation extraction must remain player-agnostic. Displayed player names may
   assist transient extraction diagnostics/linking but are not reusable tactic
   assignments and duplicate OCR names must not make the tactic invalid.

## Team Instructions extraction

1. Locate `Team Instructions` as the primary modal breadcrumb/location anchor.
2. Locate the visible `In Possession` and `Out of Possession` tab labels and use
   their row/spacing plus the active underline as local scale, orientation and
   phase evidence wherever available.
3. Apply normalized instruction-card regions inside that local reference frame,
   not directly against whole-screen coordinates.
4. The same extraction must work when the Team Instructions modal appears
   inside a larger FM screenshot and when the supplied capture is already
   tightly cropped around the modal.
5. Whole-screen percentage panel estimation is a legacy fallback only when
   stronger local anchors cannot be established; it must not override valid
   local anchor evidence.
6. Failure to determine the active underline or a canonical instruction value
   must remain explicit review evidence rather than silently inventing a value.

## OCR geometry stability

1. Retain normalized historical observations for OCR/reference geometry by
   compatible layout/profile and zone.
2. Classify new geometry transparently using robust historical statistics
   (median and median absolute deviation) rather than silently accepting drift.
3. Preserve anomalous observations for diagnosis but never allow anomalous or
   unvalidated observations to train the accepted baseline.
4. Regression tests must lock the accepted configured OCR zones so accidental
   coordinate movement is visible in the test suite.
5. Geometry history must distinguish incompatible reference frames/layout
   profiles rather than mixing them into one distribution.

## Current verification evidence

Implementation and regression coverage for the current stabilisation includes:

- `core/parser/tacticLayout.py` — local Team Instructions anchoring and legacy
  fallback behaviour;
- `core/ocrZoneHistory.py` — robust drift classification;
- `database/ocrZoneHistory.py` — append-only observation persistence and
  baseline eligibility;
- `config/tacticExtraction.yaml` — accepted normalized extraction geometry;
- `tests/test_tacticLayoutAnchor.py` — cropped/current instruction-reference
  regression cases;
- `tests/test_ocrZoneHistory.py` — history, anomaly and configured-zone
  regression coverage; and
- `documentation/ocrZoneGeometry.md` — geometry/reference-frame model and
  diagnostic workflow.

The current acceptance gate is to run the full suite and regenerate the latest
Formation/In Possession/Out Of Possession reference captures, confirming that
systematic one-card instruction displacement and player-name validation noise
are absent before requirement 007B begins.

## Change history

- 2026-08-16: clarified that FM's legacy/template formation label is not tactic
  identity; phase formation names derive from the FMSAT tactic name.
- 2026-08-16: recorded anchor-relative Team Instructions extraction,
  historical OCR geometry drift protection and player-agnostic tactic evidence
  as current requirement-006 stabilisation work.
