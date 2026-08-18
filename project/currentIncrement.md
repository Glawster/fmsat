# Current Development Increment

## Status

Active
<!-- Options: Active, Idle, Blocked, InReview -->

## Objective

Deliver requirement 007B: turn the completed Generic Role Fit foundation into dependable
role-depth and player-role analysis in the existing Squad Analysis tab.

The key constraint is that depth represents simultaneous tactical requirements. The same
player must not be allocated to more than one required slot in the same assignment result.

## Governing References

- Primary Requirement: `project/requirements/features/007-roleCentricSquadAssessment.md`
- Supporting Requirements:
  - `project/requirements/features/006-structuredTacticExtraction.md`
  - `project/requirements/features/010-positionAttributeRoleDefinitions.md`
- Supporting ADRs: None
- Milestone / Roadmap: requirement 007B role-depth and player-role analysis

## Role Identity Contract

- `roleCode` is the durable semantic identity used by OCR normalization, persisted role
  knowledge and Generic Role Fit policy lookup.
- Football Manager abbreviations, display names and OCR aliases resolve to `roleCode`; they
  are evidence and presentation values rather than persistence keys.
- Historical numeric `roleID` values are compatibility/surrogate metadata only and must never
  decide which role a captured definition represents.
- Legacy role files that pre-date `roleCode` are resolved from their confirmed display name
  and abbreviation before any numeric metadata is considered.

## Scope

- Calculate Generic Role Fit consistently for every available player/role combination where
  the required evidence exists.
- Build required-role depth from the tactic's simultaneous slots.
- Allocate unique players across simultaneous required slots when deriving best candidate and
  backup depth.
- Identify each player's best and alternative roles.
- Identify weak positions, role duplication and unused squad strengths.
- Keep transparent calculation breakdowns behind every score and finding.
- Preserve `Unavailable` whenever evidence or assessment policy is incomplete.
- Present results in the existing Analysis tab before considering later selection or
  recruitment features.

## Explicit Exclusions

- Unique-player simultaneous-slot assignment and role depth (007B).
- Best XI selection.
- Tactical Fit and Position Familiarity.
- Overall Suitability.
- Recruitment analysis or recommendations.
- Competition-level attribute benchmark colouring until an explicit benchmark evidence model
  exists.
- Requirement 009 immutable tactic revision-history work.

## In-Progress Tasks

- [x] Make semantic `roleCode` the role identity used for captured-role reconciliation and
  Generic Role Fit policy lookup; retain numeric IDs only for legacy compatibility.
- [ ] Confirm the all-player/all-role matrix is complete and consistently filtered by role
  positional eligibility.
- [ ] Implement unique-player assignment across simultaneous required tactical slots.
- [ ] Produce best candidate, backup and uncovered status for every required slot.
- [ ] Produce each player's best role and alternative roles from the same Generic Role Fit
  evidence.
- [ ] Produce weak-position, role-duplication and unused-strength findings.
- [ ] Keep calculation traces available for every displayed score/finding.
- [ ] Add regression coverage for duplicate simultaneous roles and unique-player allocation.
- [ ] Run the full automated suite and manually review the current reference squad/tactic.

## Relevant Files & Components

- `config/roleAssessment.yaml`
- `core/parser/tacticVocabulary.py`
- `core/roleKnowledge.py`
- `core/squadAssessment.py`
- `app/squadDetailModel.py`
- `app/squadDetailTabOverrides.py`
- `app/squadDetailView.py`
- `tests/test_roleKnowledge.py`
- `tests/test_tacticVocabulary.py`
- `tests/test_squadAssessment.py`
- `tests/test_squadPresentationRefinements.py`
- `project/roadmap.md`

## Verification Procedures

Run:

```bash
manageProject --check
QT_QPA_PLATFORM=offscreen pytest
```

Then review the current reference squad against its assigned tactic and confirm:

1. every required tactical slot is shown;
2. repeated roles remain separate simultaneous requirements;
3. one player is never allocated to two simultaneous slots in the same depth result;
4. backup candidates do not invalidate the primary assignment;
5. player best/alternative roles use the same Generic Role Fit calculations shown elsewhere;
6. missing evidence remains `Unavailable`; and
7. every displayed score/finding has a transparent calculation/evidence explanation.

For role migration specifically, regenerate `Libero1974` and confirm historical captured roles
such as TAM resolve from their confirmed name/abbreviation even when an old numeric `roleID`
collides with a newer packaged catalogue role.

## Definition of Done

- Every required tactical slot has a best candidate, backup or explicit uncovered state.
- Simultaneous slot allocation uses unique players.
- Every player has a best/alternative role result where evidence permits.
- Weak positions, duplication and unused strengths are derived from the same explicit role-fit
  evidence.
- Role identity is semantic (`roleCode`), never inferred from numeric sequence allocation.
- No Best XI, Tactical Fit or recruitment judgement is introduced by this increment.
- The full automated suite passes.

## Handoff

After 007B is accepted, the next increment can consider tactical modifiers and position
familiarity before any Overall Suitability, Best XI or recruitment recommendation layer.

## Agent Readiness

Run:

```bash
manageProject --check
QT_QPA_PLATFORM=offscreen pytest
```
