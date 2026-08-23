# Current Development Increment

## Status

Active
<!-- Options: Active, Idle, Blocked, InReview -->

## Objective

Deliver requirement 007B: turn the completed Generic Role Fit foundation into dependable
role-depth and player-role analysis in the existing Squad Analysis tab, with a practical
player-evidence editing workflow.

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
- A missing role abbreviation is shown as `Unknown`; FMSAT does not invent an acronym. The
  Roles workspace directs the user to the existing Role Editor workflow to complete the role
  knowledge.

## Delivered Scope

- Calculate Generic Role Fit consistently for every available player/role combination where
  the required evidence exists.
- Build required-role depth from the tactic's simultaneous `slotId`-linked positions.
- Allocate unique players across simultaneous required slots when deriving primary and backup
  depth.
- Identify each player's best and alternative roles.
- Identify calculable weak positions, role duplication and unused squad strengths.
- Keep transparent calculation breakdowns behind every score and finding.
- Preserve `Unavailable` whenever evidence or assessment policy is incomplete.
- Present role depth as IP role, OOP role, primary and backup in the existing Analysis tab.
- Present Tactic Roles as IP/OOP role abbreviations with compact eligible coverage.
- Persist the most recently applied tactic as the squad's active/default tactic on reload.
- Provide a focused Player Editor from the Players tab for factual name, positions, CA/PA,
  attributes and known-trait corrections. Saving uses the existing squad-model persistence
  path and immediately rebuilds Roles and Analysis.
- Keep the Players table as a browse/filter/sort surface rather than a wide inline editor.
- Recover FM26 Acceleration, Agility and Natural Fitness columns with conservative geometric
  header inference when OCR drops those headings. Long Shots is only an OCR geometry anchor
  and is not part of the captured squad model.

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
- [x] Confirm the all-player/all-role matrix is complete and consistently filtered by role
  positional eligibility for presentation.
- [x] Implement unique-player assignment across simultaneous required tactical slots.
- [x] Produce primary, backup and uncovered/unavailable status for every required slot.
- [x] Produce each player's best role and alternative roles from the same Generic Role Fit
  evidence.
- [x] Produce weak-position, role-duplication and unused-strength findings and suppress
  duplicate weak-position noise where the real state is already `Unavailable`.
- [x] Keep calculation traces available for every displayed score/finding.
- [x] Add a Player Editor and make accepted player corrections immediately rebuild analysis.
- [x] Persist the active tactic selection for a squad.
- [x] Surface missing role abbreviations as `Unknown` and route them to the Role Editor.
- [x] Add regression coverage for duplicate simultaneous roles, unique-player allocation,
  tactic persistence, Player Editor behaviour and FM26 attribute-header recovery.
- [ ] Run the full automated suite after the final 007B presentation/editor changes.
- [ ] Manually review the current Bristol Women reference squad/tactic, including Natural
  Fitness regeneration, Player Editor save/refresh, Unknown role editing and active-tactic
  persistence after restart.

## Relevant Files & Components

- `config/roleAssessment.yaml`
- `core/parser/squadAttributesFm26.py`
- `core/parser/tacticVocabulary.py`
- `core/roleDepth.py`
- `core/roleKnowledge.py`
- `core/squadAssessment.py`
- `core/squadModel.py`
- `app/playerEditorDialog.py`
- `app/presentation.py`
- `app/squadPlayersWorkspace.py`
- `app/squadRolesWorkspace.py`
- `app/squadAnalysisWorkspace.py`
- `app/squadDetailModel.py`
- `app/squadDetailView.py`
- `database/activeTacticDatabase.py`
- `tests/test_playerEditorDialog.py`
- `tests/test_roleDepth.py`
- `tests/test_squadAnalysisWorkspace.py`
- `tests/test_squadRolesWorkspace.py`
- `tests/test_tacticSelectionPersistence.py`
- `tests/test_naturalFitnessHeader.py`
- `project/roadmap.md`

## Verification Procedures

Run:

```bash
manageProject --check
QT_QPA_PLATFORM=offscreen pytest
```

Then regenerate and review the current reference squad against its assigned tactic and confirm:

1. every required tactical slot is shown in the hidden-position tactical order;
2. repeated roles remain separate simultaneous requirements;
3. one player is never allocated to two simultaneous slots in the same primary assignment;
4. backup candidates do not invalidate the primary assignment;
5. player best/alternative roles use the same Generic Role Fit calculations shown elsewhere;
6. missing evidence remains `Unavailable` and missing role abbreviations remain `Unknown`;
7. Natural Fitness is populated from the retained FM26 squad capture where visible;
8. double-clicking a Players row opens the Player Editor, and Save Player immediately refreshes
   Roles and Analysis from the corrected facts;
9. selecting a different tactic, leaving/restarting FMSAT and reopening the squad restores the
   last selected tactic; and
10. every displayed score/finding has a transparent calculation/evidence explanation.

For role migration specifically, regenerate `Libero1974` and confirm historical captured roles
such as TAM resolve from their confirmed name/abbreviation even when an old numeric `roleID`
collides with a newer packaged catalogue role.

## Definition of Done

- Every required tactical slot has a primary candidate, backup or explicit
  uncovered/unavailable state.
- Simultaneous slot allocation uses unique players.
- Every player has a best/alternative role result where evidence permits.
- Weak positions, duplication and unused strengths are derived from the same explicit role-fit
  evidence without presenting missing evidence as a calculated weakness.
- Player-model corrections can be made through the Player Editor and immediately invalidate and
  rebuild affected analysis.
- Role identity is semantic (`roleCode`), never inferred from numeric sequence allocation.
- Unknown abbreviations remain explicit user-resolvable knowledge gaps.
- No Best XI, Tactical Fit or recruitment judgement is introduced by this increment.
- The full automated suite and final manual reference-squad review pass.

## Handoff

After 007B is accepted, the next increment can consider tactical modifiers and position
familiarity before any Overall Suitability, Best XI or recruitment recommendation layer.

## Agent Readiness

Run:

```bash
manageProject --check
QT_QPA_PLATFORM=offscreen pytest
```
