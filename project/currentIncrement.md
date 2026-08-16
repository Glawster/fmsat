# Current Development Increment

## Status

Active
<!-- Options: Active, Idle, Blocked, InReview -->

## Objective

Stabilise the evidence required by requirement 007's generic squad analysis so
Generic Role Fit and squad-depth work can resume on dependable player, role and
tactic data. The squad-viewer foundation and 007A assessment policy are in
place; the immediate work is verification of the structured tactic extraction
used as supporting evidence before starting 007B.

## Governing References

- Primary Requirement: `project/requirements/features/007-roleCentricSquadAssessment.md`
- Supporting Requirements:
  - `project/requirements/features/006-structuredTacticExtraction.md`
  - `project/requirements/features/009-tacticDetailManagement.md`
  - `project/requirements/features/010-positionAttributeRoleDefinitions.md`
- Supporting ADRs: None
- Milestone / Roadmap: requirement 007 generic analysis increment

## Scope

- Preserve the completed 007A explicit Generic Role Fit assessment policy.
- Verify anchor-relative Team Instructions extraction against the current FM26
  screenshot layouts before consuming tactic evidence in later analysis.
- Retain historical OCR-zone geometry and classify normal drift separately from
  anomalous geometry without allowing anomalous observations to train the
  baseline.
- Keep tactic extraction player-agnostic: displayed player names are evidence,
  not reusable tactic assignments or tactic identity.
- Use the user-owned tactic name as tactic identity and derive the football
  object-model formation names as `<tactic name> IP` and `<tactic name> OOP`.
- Support persistent tactic renaming without regenerating screenshot evidence.
- Resume requirement 007 generic player/role analysis after extraction
  verification is dependable.

## Explicit Exclusions

- 007B player-wide role ranking and squad-depth presentation until the current
  tactic-processing regression is verified.
- Best XI selection.
- Tactical Fit and Overall Suitability.
- Recruitment analysis or recommendations.
- Requirement 009 immutable revision-history and historical-comparison work.

## In-Progress Tasks

- [x] Complete explicit assessment weights for every canonical tactic role.
- [x] Enforce complete/valid assessment policy and preserve `Unavailable` for
  missing required evidence.
- [x] Add historical OCR-zone geometry observations and median/MAD drift
  classification with anomaly exclusion from baseline learning.
- [x] Anchor Team Instructions extraction to visible local evidence rather than
  whole-screen position wherever possible.
- [x] Remove displayed player identity from reusable tactic validation/model
  semantics.
- [x] Make tactic name user-editable and derive `<name> IP` / `<name> OOP`
  formation identities.
- [ ] Run the full automated suite after the latest OMP and extraction changes.
- [ ] Reprocess the current Formation, In Possession and Out Of Possession
  screenshots and verify instruction zones/values and active-tab detection.
- [ ] Start 007B once the preceding verification is clean enough to trust the
  evidence base.

## Relevant Files & Components

- `config/roleAssessment.yaml`
- `config/tacticExtraction.yaml`
- `core/assessment/`
- `core/parser/tacticLayout.py`
- `core/ocrZoneHistory.py`
- `database/ocrZoneHistory.py`
- `core/builder/tacticBuilder.py`
- `core/builder/tacticMetadataExtractor.py`
- `tests/test_roleAssessmentPolicy.py`
- `tests/test_ocrZoneHistory.py`
- `tests/test_tacticLayoutAnchor.py`
- `tests/test_tacticNaming.py`
- `documentation/ocrZoneGeometry.md`

## Verification Procedures

Run:

```bash
manageProject --check
QT_QPA_PLATFORM=offscreen pytest
```

Then regenerate a tactic from the current three FM26 reference captures and
confirm:

1. both phases contain 11 positions;
2. instruction-card overlays align with the visible cards;
3. active Team Instructions tabs are detected correctly;
4. canonical instruction values no longer exhibit systematic one-card shift;
5. displayed player-name ambiguity does not invalidate the reusable tactic;
6. the football object model uses `<tactic name> IP` and `<tactic name> OOP`.

## Definition of Done

- `manageProject --check` passes under OMP 0.4.
- The full automated test suite passes.
- Current reference screenshots no longer show systematic instruction-zone
  displacement or player-identity validation failures.
- 007A remains deterministic, explainable and `Unavailable`-safe.
- Requirement 007 can proceed to 007B without depending on known-bad tactic
  extraction evidence.

## Handoff & Unresolved Context

007A is the completed assessment-policy foundation. 007B is deliberately paused
only while the latest tactic extraction is verified. Once verification is
satisfactory, the next development work is the complete player-role matrix,
best/alternative roles and required-role depth in the existing Analysis tab.

## Agent Readiness

Run:

```bash
manageProject --check
```
