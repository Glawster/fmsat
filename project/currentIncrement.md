# Current Development Increment

## Status

Active — implementation complete; final clean-room acceptance in progress.

## Objective

Deliver requirement 007C: **Best XI and clean-room stabilization**.

007C extends the Generic Role Fit and simultaneous role-depth foundation with an
explainable Best XI while hardening the complete squad/tactic workflow against defects
found during clean-room use. Requirement 007 remains `InProgress`: Tactical Fit, Overall
Suitability, candidate comparison and Role Health are later scope.

## Governing References

- Primary Requirement: `project/requirements/features/007-roleCentricSquadAssessment.md`
- Supporting Requirements:
  - `project/requirements/features/006-structuredTacticExtraction.md`
  - `project/requirements/features/008-welcomeScreen.md`
  - `project/requirements/features/010-positionAttributeRoleDefinitions.md`
- Living Algorithm Guide: `documentation/bestXi.md`
- Milestone / Roadmap: requirement 007C Best XI and clean-room stabilization

## Evidence and Assignment Policy

- `roleCode` remains the durable semantic role identity.
- Generic Role Fit remains the scoring evidence; missing policy or attributes remain
  `Unavailable`.
- Best XI candidates must have captured position-family evidence for the tactic slot.
  Position familiarity is an eligibility boundary, not a tie-break.
- Best XI maximizes covered simultaneous slots, then total fit, then weakest selected fit,
  with deterministic player identity as the final tie-break.
- One player can occupy at most one simultaneous slot.
- An incomplete or malformed phase slot makes that individual slot unavailable; it does
  not invalidate otherwise linked simultaneous slots.
- Manual player corrections are authoritative over OCR and survive reassessment and model
  regeneration.

## Delivered Scope

### Best XI and simultaneous-slot analysis

- UI-independent global Best XI assignment with unique-player allocation and explainable
  whole-XI trade-offs.
- Position-family eligibility for current deployability; unfamiliar high Generic Role Fit
  remains available to role-depth and future retraining analysis but is excluded from Best XI.
- Partial durable-slot recovery: valid linked phase slots remain usable when a neighbouring
  phase slot is incomplete or malformed.
- Role-depth and Best XI regression coverage for coverage, weakest-link, deterministic and
  malformed-slot behaviour.

### Player and squad evidence

- Conservative player-name cleanup and cross-capture identity reconciliation using name,
  position, CA/PA and overlapping attribute evidence.
- Visible uncertainty state for suspicious OCR names; cleaner corroborated evidence wins
  without silently deleting unfamiliar name fragments.
- Player Editor corrections persist as final authority through refresh and regeneration.
- Incremental squad imports merge complementary captures without deleting players absent
  from a filtered screenshot.
- Player editing and explicit removal rebuild derived squad assessment while retained source
  screenshots remain provenance.
- A retained filtered-seven squad screenshot, expected data and opt-in real-OCR regression
  protect the supplementary-import workflow.

### Role policy and vocabulary

- Role Assessment Weight Editor for the canonical 0–10 policy, including validated YAML
  import/export and explicit legacy 0–5 migration in the policy service.
- Role-position compatibility and tracking-role policy corrections.
- Role-profile, semantic vocabulary and runtime role-knowledge reconciliation fixes that
  preserve unresolved observations rather than inventing definitions.

### Clean-room workflow stabilization

- Tactic model loading and screenshot extraction corrections found during clean-room review.
- Welcome/import lifecycle fixes, including safer re-import, reassessment and window state
  transitions.
- Opt-in clean-room role-knowledge acceptance fixture covering confirmed and unresolved OCR
  evidence states.

## Verification Status

Evidence exercised on the final integrated branch:

- full automated suite: **501 passed, 9 skipped**;
- focused Best XI, player identity, squad-model and presentation suite: **37 passed**;
- Ruff passed for the resolved 007C files;
- Black and `git diff --check` passed for the resolved merge files; and
- the real-OCR filtered-seven regression and final clean-room role-knowledge gate remain
  opt-in because they require retained fixtures/runtime flags.

Repository-wide Ruff currently also reports unrelated pre-existing unused imports outside
the 007C change set.

## Remaining Acceptance

- [x] Run the full automated suite on the final integrated commit: 501 passed, 9 skipped.
- [ ] Run the opt-in clean-room role-knowledge gate with `FMSAT_007B_FINAL=1`.
- [ ] Run the real filtered-seven OCR regression with `FMSAT_OCR_FIXTURES=1` in an OCR-capable
  environment.
- [ ] Reassess the Bristol Women reference squad and confirm Best XI uniqueness,
  position-family eligibility, partial-slot isolation and explanatory tooltips.
- [ ] Confirm player corrections and supplementary screenshot merges through the desktop
  workflow.

## Explicit Exclusions

- Tactical Fit and tactic-specific attribute modifiers.
- Overall Suitability and configurable composite scoring.
- Candidate comparison and dynamic role-attribute comparison columns.
- Role Health, recruitment analysis and recommendations.
- Form, morale, condition, injury, suspension or opposition-specific selection.
- Rotation, alternative-XI and automated lineup generation.

## Relevant Files and Components

- `documentation/bestXi.md`
- `core/bestXi.py`
- `core/roleDepth.py`
- `core/playerIdentity.py`
- `core/squadModel.py`
- `core/roleAssessmentPolicy.py`
- `app/roleAssessmentWeightEditor.py`
- `app/squadAnalysisWorkspace.py`
- `app/squadPlayersWorkspace.py`
- `tests/test_bestXi.py`
- `tests/test_roleDepth.py`
- `tests/test_playerIdentity.py`
- `tests/test_squadModel.py`
- `tests/test_roleAssessmentWeightEditor.py`
- `tests/test_filteredSevenSquadOcr.py`
- `tests/test_cleanRoom007b.py`

## Definition of Done

- Best XI uses deterministic global assignment and position-family eligibility.
- One malformed phase slot cannot invalidate otherwise usable simultaneous slots.
- Player identity reconciliation prefers corroborated clean evidence while preserving manual
  authority and exposing uncertainty.
- Incremental squad imports, editing and removal preserve provenance and rebuild assessment.
- Role-policy editing and clean-room lifecycle fixes have focused regression coverage.
- Final automated and manual clean-room acceptance evidence is recorded.
- Requirement 007 remains `InProgress` for its undelivered later analysis stages.

## Handoff

Complete the remaining clean-room acceptance above. After 007C is accepted, return to the
undelivered requirement 007 stages rather than marking the parent requirement complete.
