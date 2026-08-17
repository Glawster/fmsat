# Current Development Increment

## Status

InReview
<!-- Options: Active, Idle, Blocked, InReview -->

## Objective

Close requirement 007A after stabilising the tactic evidence and Generic Role Fit foundation,
then merge the completed increment to `main` before starting 007B.

## Governing References

- Primary Requirement: `project/requirements/features/007-roleCentricSquadAssessment.md`
- Supporting Requirements:
  - `project/requirements/features/006-structuredTacticExtraction.md`
  - `project/requirements/features/009-tacticDetailManagement.md`
  - `project/requirements/features/010-positionAttributeRoleDefinitions.md`
- Supporting ADRs: None
- Milestone / Roadmap: requirement 007 generic analysis increment

## Delivered Scope

- Complete explicit Generic Role Fit weights for every canonical tactic role.
- Preserve `Unavailable` whenever required evidence or assessment policy is incomplete.
- Calculate and explain Generic Role Fit through transparent weighted contribution traces.
- Keep tactic extraction player-agnostic and use tactic name as reusable tactic identity.
- Retain OCR geometry history and anomaly classification.
- Stabilise FM26 Formation extraction through CB/GK depth with exact role-label evidence.
- Reconcile OCR-confirmed role definitions with canonical tactical vocabulary.
- Add currently encountered canonical roles including SS, HB and DDM.
- Provide role/candidate browsing, player-role assessment and initial role-depth analysis.
- Use shared QSS styling for normal workspace dropdowns.
- Sort the player selector by surname and display `Surname, Firstname` while retaining the
  original player identity internally.

## Explicit Exclusions

- Best XI selection.
- Tactical Fit and Overall Suitability.
- Recruitment analysis or recommendations.
- Competition-level attribute benchmarks until an explicit benchmark evidence model exists.
- Requirement 009 immutable revision-history and historical-comparison work.

## Completion Tasks

- [x] Complete explicit assessment weights for every canonical tactic role.
- [x] Enforce complete/valid assessment policy and preserve `Unavailable` states.
- [x] Add historical OCR-zone geometry observations and drift classification.
- [x] Stabilise Team Instructions and Formation extraction against current FM26 evidence.
- [x] Verify 11 In Possession and 11 Out Of Possession positions on regeneration.
- [x] Resolve canonical role gaps encountered by regeneration, including SS, HB and DDM.
- [x] Add internal OCR-role to tactical-vocabulary consistency checking.
- [x] Standardise workspace dropdown styling in QSS.
- [x] Run the full automated pytest suite successfully after the final changes.
- [x] Update project status/documentation for 007A closure.
- [ ] Merge the 007A pull request to `main`.

## Verification Procedures

The final local verification completed successfully with:

```bash
QT_QPA_PLATFORM=offscreen pytest
```

The current FM26 reference tactic was regenerated successfully with:

1. 11 In Possession positions;
2. 11 Out Of Possession positions;
3. canonical instruction normalization;
4. role definitions resolving through the canonical tactical vocabulary; and
5. no outstanding SS/HB/DDM knowledge gap expected after the final vocabulary changes.

## Definition of Done

- The full automated test suite passes.
- Current reference regeneration produces 11 positions in both phases.
- Generic Role Fit remains deterministic, explainable and `Unavailable`-safe.
- Known OCR roles are represented by or checked against `tacticalVocabulary.yaml`.
- The normal workspace dropdown look and feel is owned by QSS.
- The 007A branch is merged to `main`.

## Handoff to 007B

007B should begin from the merged 007A baseline. The next work is to refine the existing
Analysis tab around the complete player-role matrix and required-role depth. A player must
not be allocated to more than one simultaneous tactical slot when calculating depth.

The intended 007B outcomes are:

- best candidate, backup and uncovered status for each required tactical slot;
- each player's best and alternative roles;
- weak positions, role duplication and unused squad strengths; and
- transparent explanations for every calculated result.

Best XI, Tactical Fit and recruitment analysis remain later increments.

## Agent Readiness

Run:

```bash
manageProject --check
QT_QPA_PLATFORM=offscreen pytest
```
