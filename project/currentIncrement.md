# Current Development Increment

## Status

Active
<!-- Options: Active, Idle, Blocked, InReview -->

## Objective

Finish requirement 007A by closing the remaining tactic-evidence and role-identity defects discovered during final validation before opening the 007A pull request to `main`.

The immediate acceptance case is the saved `Libero1974` tactic: OCR already reads `TAM`, so regeneration must normalize it to the existing Tracking Attacking Midfielder role without requesting a duplicate role definition.

## Governing References

- Primary Requirement: `project/requirements/features/007-roleCentricSquadAssessment.md`
- Supporting Requirements:
  - `project/requirements/features/006-structuredTacticExtraction.md`
  - `project/requirements/features/010-positionAttributeRoleDefinitions.md`
- Supporting ADRs: None
- Milestone / Roadmap: requirement 007A Generic Role Fit and tactic-evidence foundation

## Role Identity Contract

- `roleCode` is the durable semantic identity used by OCR normalization, persisted role knowledge and Generic Role Fit policy lookup.
- Football Manager abbreviations, display names and OCR aliases resolve to `roleCode`; they are evidence and presentation values rather than persistence keys.
- Historical numeric `roleID` values are compatibility/surrogate metadata only and must never decide which role a captured definition represents.
- Legacy role files that pre-date `roleCode` are resolved from their confirmed display name and abbreviation before any numeric metadata is considered.

## Scope

- Complete explicit assessment weights for all roles intended to participate in Generic Role Fit.
- Calculate Generic Role Fit consistently for every available player where required evidence exists.
- Keep results `Unavailable` where role assessment evidence or policy is incomplete.
- Preserve transparent score breakdowns.
- Stabilise role recognition and tactic regeneration needed by the 007A assessment foundation.
- Ensure confirmed/canonical role abbreviations such as `TAM` resolve to their semantic role identity during regeneration.
- Finish documentation, automated tests and manual `Libero1974` validation before PR to `main`.

## Explicit Exclusions

- Unique-player simultaneous-slot assignment and role depth (007B).
- Best XI selection.
- Tactical Fit and Position Familiarity.
- Overall Suitability.
- Recruitment analysis or recommendations.
- Competition-level attribute benchmark colouring until an explicit benchmark evidence model exists.

## In-Progress Tasks

- [x] Make semantic `roleCode` the role identity used for captured-role reconciliation and Generic Role Fit policy lookup; retain numeric IDs only for legacy compatibility.
- [x] Add `TAM` / Tracking Attacking Midfielder to tactic-role recognition without inventing assessment weights.
- [x] Add targeted logging through captured-role refresh, formation normalization and object-model role resolution.
- [ ] Confirm the current checkout is running the latest 007A branch code and that the new role-resolution diagnostics appear.
- [ ] Regenerate `Libero1974` and confirm OCR-observed `TAM` normalizes to `trackingAttackingMidfielder` with no missing-role prompt.
- [ ] Run the full automated suite.
- [ ] Update final 007A development status/documentation.
- [ ] Squash as desired and open the 007A PR to `main`.

## Relevant Files & Components

- `config/tacticalVocabulary.yaml`
- `config/roleAssessment.yaml`
- `core/parser/tacticVocabulary.py`
- `core/builder/tacticScreenshotExtractor.py`
- `football/roleVocabulary.py`
- `core/roleKnowledge.py`
- `core/squadAssessment.py`
- `tests/test_tacticVocabulary.py`
- `tests/test_roleKnowledge.py`
- `tests/test_roleAssessmentPolicy.py`
- `tests/test_squadAssessment.py`

## Verification Procedures

Run:

```bash
manageProject --check
QT_QPA_PLATFORM=offscreen pytest
```

Then restart FMSAT and regenerate `Libero1974`. Confirm:

1. Formation OCR reads 11 genuine in-possession and 11 genuine out-of-possession role tiles;
2. `TAM` is observed and normalized to `trackingAttackingMidfielder`;
3. no duplicate/missing role-definition prompt is shown for TAM or any other already-known role;
4. known team instructions do not produce bogus review-required issues;
5. the regenerated tactic model is saved successfully; and
6. Generic Role Fit remains `Unavailable` for any recognition-only role without an explicit assessment policy.

## Definition of Done

- Full automated suite passes.
- `Libero1974` regenerates cleanly from saved screenshots.
- Known roles, including TAM, resolve from semantic role identity rather than numeric sequence allocation.
- No known role/instruction produces a bogus Review Required prompt.
- Generic Role Fit remains evidence-driven and explainable.
- 007A documentation/status is current and the branch is ready for squash/PR to `main`.

## Handoff

Only after 007A is merged to `main`, create 007B from the accepted `main` baseline and begin simultaneous-slot role-depth analysis, including the rule that one player cannot fill multiple required slots in the same assignment.

## Agent Readiness

Run:

```bash
manageProject --check
QT_QPA_PLATFORM=offscreen pytest
```
