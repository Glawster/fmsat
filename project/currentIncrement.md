# Current Development Increment

## Status

Active
<!-- Options: Active, Idle, Blocked, InReview -->

## Objective

Deliver requirement 007C: turn the dependable Generic Role Fit and simultaneous role-depth
foundation into an explainable Best XI selection for the currently applied tactic.

Best XI is a whole-team assignment problem. It must not greedily select the strongest player
for each slot in isolation when moving that player elsewhere produces a stronger or more
complete XI.

## Governing References

- Primary Requirement: `project/requirements/features/007-roleCentricSquadAssessment.md`
- Supporting Requirements:
  - `project/requirements/features/006-structuredTacticExtraction.md`
  - `project/requirements/features/010-positionAttributeRoleDefinitions.md`
- Living Algorithm Guide: `documentation/bestXi.md`
- Supporting ADRs: None
- Milestone / Roadmap: requirement 007C Best XI analysis

## Evidence Contract

- `roleCode` remains the durable semantic role identity.
- Generic Role Fit remains the player/role scoring evidence; Best XI does not introduce a
  hidden replacement rating.
- Simultaneous tactic slots retain their explicit IP/OOP role requirements.
- A slot score is calculable only when every required phase role has calculable Generic Role
  Fit evidence.
- Missing role policy, unresolved role identity or missing player attributes remain
  `Unavailable`; Best XI must not invent substitute evidence.
- Captured player-position families are retained as familiarity/training evidence.

## Best XI Assignment Policy

The global optimiser applies these priorities in order:

1. maximise the number of covered simultaneous tactic slots;
2. assign each player to at most one simultaneous slot;
3. maximise total selected slot Generic Role Fit;
4. where totals tie, maximise the weakest selected slot fit;
5. where role-fit objectives tie, prefer captured positional familiarity;
6. use deterministic alphabetical identity only as the final tie-break.

A slightly weaker local assignment is therefore valid when it allows a stronger player to
cover another slot and improves the whole XI. The motivating regression example is selecting
Laura Freigang at Second Striker so Lauren Hemp can cover AML when that produces a complete
and stronger global assignment.

## Delivered Scope

- 007A Generic Role Fit and transparent weighted evidence.
- 007B simultaneous Required Role Depth, unique-player depth allocation, player best/alternative
  roles, weak positions, role duplication and unused strengths.
- Role assessment integrity reporting and editable 0-10 role weights.
- Recognition of tracking wide roles and explicit reassessment without rerunning OCR.
- Determinate squad/tactic regeneration progress where extraction milestones are known.
- Existing Best XI Analysis presentation in the four-quadrant Analysis workspace.

## Current Change Set

- [x] Add a UI-independent global Best XI assignment service.
- [x] Maximise coverage before role-fit quality.
- [x] Enforce one player per simultaneous slot.
- [x] Add total-fit, weakest-link, familiarity and deterministic tie-break priorities.
- [x] Retain explanatory evidence for global trade-offs.
- [x] Wire the Analysis Best XI table to the global optimiser rather than the Role Depth
  primary assignment.
- [x] Add the Hemp/Freigang global-assignment regression case.
- [x] Add core tests for coverage, weakest-link, familiarity and deterministic behaviour.
- [x] Document the algorithm in `documentation/bestXi.md` and link it from the root README.
- [ ] Run focused Best XI tests.
- [ ] Run the full automated suite.
- [ ] Manually reassess the Bristol Women reference squad and verify the resulting Best XI.

## Explicit Exclusions

- Dynamic role-attribute comparison columns in the Roles workspace; this is the next UI change
  set after Best XI is accepted.
- Renaming provisional `role-newrole` screenshots after OCR resolves their semantic role; this
  is a later persistence cleanup.
- Tactical interaction or partnership modifiers.
- Player traits as tactical-fit modifiers.
- Form, morale, condition, fatigue, injury, suspension or match-sharpness selection.
- Opposition-specific selection.
- Rotation/alternative XI generation.
- Recruitment analysis or recommendations.

## Relevant Files & Components

- `documentation/bestXi.md`
- `core/bestXi.py`
- `core/roleDepth.py`
- `core/squadAssessment.py`
- `app/squadAnalysisWorkspace.py`
- `app/squadDetailModel.py`
- `tests/test_bestXi.py`
- `tests/test_bestXiWorkspace.py`
- `tests/test_roleDepth.py`
- `tests/test_squadAnalysisWorkspace.py`

## Verification Procedures

Run focused coverage first:

```bash
QT_QPA_PLATFORM=offscreen pytest tests/test_bestXi.py tests/test_bestXiWorkspace.py tests/test_squadAnalysisWorkspace.py
```

Then run the full suite:

```bash
QT_QPA_PLATFORM=offscreen pytest
```

Finally reassess the current Bristol Women reference squad without regeneration and confirm:

1. every selected Best XI player is unique;
2. calculable complete coverage is preferred to a stronger-looking partial XI;
3. Hemp can be moved from an individually stronger SS assignment to AML when Freigang at SS
   produces the stronger complete XI;
4. Required Role Depth remains visible as separate depth evidence rather than being replaced by
   the Best XI result;
5. positional familiarity/training status remains explicit;
6. missing role or player evidence remains `Unavailable`/`Uncovered` rather than guessed; and
7. selected-player tooltips explain the global assignment evidence and any local-score trade-off.

## Definition of Done

- Best XI is selected by a deterministic whole-team assignment rather than tactic-slot order.
- Coverage, uniqueness, total role fit, weakest-link quality and positional familiarity are
  applied in the documented priority order.
- The Hemp/Freigang regression case passes.
- Best XI explanations retain enough evidence to explain why a locally weaker player may be
  selected in one slot.
- Required Role Depth remains a separate analysis surface.
- Focused and full automated suites pass.
- Manual Bristol Women reassessment produces a plausible complete XI from current evidence.

## Handoff

After this change set is accepted and squashed, proceed to the Roles workspace attribute-table
change: selected-role candidates should show the role's required attributes as individual
columns, and the player-role pane should show the union of attributes required by its displayed
roles.
