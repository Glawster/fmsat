# 007 — Role-centric squad assessment

## Status

InProgress

## Objective

Provide a model-backed squad viewer in the same visual family as the tactic
viewer. Combine a selected stored squad with a selected tactic revision and
known assessment configuration so every required tactical role can rank,
compare and explain the available players. Keep each role as a long-lived
planning object on which squad depth and later recruitment workflows can be
built.

## Current delivery state

The squad-viewer foundation and three analysis sub-increments are implemented
on the feature branch. Requirement 007 remains `InProgress` because Tactical
Fit, Overall Suitability, comparison and Role Health remain later scope.

007A established the assessment-policy foundation:

- packaged assessable canonical roles have explicit Generic Role Fit weights;
- policy validation rejects missing packaged roles, unknown roles, unknown
  attributes and weights outside the supported range;
- the Generic Role Fit calculation retains its weighted-attribute trace and
  returns `Unavailable` rather than fabricating a score when required evidence
  is missing; and
- regression tests protect the assessment-policy catalogue.

007B builds on that foundation with role-depth intelligence and player-evidence
maintenance:

- simultaneous tactic slots are linked by durable `slotId` evidence and use
  unique-player primary/backup assignment;
- Analysis exposes IP role, OOP role, primary, backup and phase-specific Generic
  Role Fit evidence without claiming Best XI selection;
- each player receives best and alternative roles from the same Generic Role Fit
  calculations;
- calculable weak positions, role duplication and unused strengths are surfaced
  without duplicating missing evidence as a weakness;
- the most recently applied tactic persists as the squad's active/default tactic;
- Players is a browse/filter/sort surface and double-clicking a row opens a
  focused Player Editor for factual name, positions, CA/PA, attribute and known
  trait corrections;
- saving a player uses the existing squad-model persistence path and immediately
  rebuilds Roles and Analysis from the corrected evidence;
- missing role abbreviations are shown as `Unknown` rather than invented and are
  directed to the existing Role Editor workflow; and
- FM26 squad regeneration includes conservative header recovery for
  Acceleration, Agility and Natural Fitness while keeping unsupported Long Shots
  out of the stored squad model.

007C adds Best XI and clean-room stabilization:

- Best XI uses global unique-player assignment and requires captured
  position-family eligibility for each slot;
- malformed or incomplete phase evidence isolates the affected slot instead of
  invalidating otherwise linked simultaneous slots;
- player names reconcile across captures using corroborating squad facts,
  uncertain OCR names remain visible for review, and manual corrections remain
  authoritative;
- incremental squad imports merge complementary screenshots, while player
  editing and removal rebuild derived assessment without deleting provenance;
- the Role Assessment Weight Editor provides 0–10 policy editing and validated
  YAML import/export; and
- role/vocabulary, OCR, welcome/import and reassessment lifecycle fixes are
  protected by focused and opt-in clean-room regressions.

007C is implemented and undergoing final clean-room acceptance.

## Dependencies

1. Consume the validated football object-model tactic produced by requirement
   006 and displayed by requirement 009.
2. Use requirement 005's six tactical colour families and role icons.
3. Keep each player's imported natural positions separate from their
   tactic-specific role suitability and assignments.
4. Do not calculate or display a role assessment when its underlying tactic or
   required player attributes are incomplete without clearly reporting that
   limitation.

## Squad workspace

1. Open a stored squad in a dedicated squad viewer rather than extending the
   welcome screen or tactic viewer into a second responsibility.
2. Use the tactic viewer's visual language and reusable widgets where they have
   the same responsibility, while keeping squad-specific views and view models
   separate.
3. Organize the initial workspace as **Overview**, **Players**, **Roles** and
   **Analysis**. Additional **Depth** or **Comparison** views may be introduced
   when their calculations are delivered.
4. Display the selected squad, selected tactic revision, squad-data date and
   knowledge/scoring identity. Changing tactic context must not mutate the
   imported squad or tactic. The most recently selected applied tactic is the
   persisted default when the squad is reopened.
5. Provide an explicit empty or selection state when no tactic is assigned. The
   Players view remains usable, but tactic-dependent role assessment must be
   reported as unavailable.
6. Present every role required by the selected tactic once as an individual
   selectable Role Card grouped into goalkeeper, defence, defensive midfield,
   midfield, attacking midfield and striker units.
7. Use the shared palette subtly through headers, borders, role icons or badges
   while preserving readability in light and dark themes.
8. Treat the canonical Football Manager role as the assessment identity. A
   position is eligibility and presentation context only; the same role used in
   multiple positions or tactic slots is assessed once at role level while
   simultaneous slot depth remains slot-specific.
9. Allow corrections to squad object-model values from the Players view through
   a focused Player Editor. Saving a correction makes the edited object model
   authoritative and marks its retained screenshot evidence as superseded
   without deleting that evidence. Derived role scores and depth are never
   editable fields; they are rebuilt after factual player changes.
10. Display every configured attribute using its configured abbreviation and a
    consistent compact column width, followed by the player's left-aligned,
    comma-separated known traits. Attribute headers expose their full names as
    hover text. Known traits are edited through a searchable, categorized and
    collapsible checklist using the canonical player-trait vocabulary rather
    than free-text entry. A selected-only view makes reviewing a player's small
    active trait set straightforward, while frequently used traits appear first
    as browse shortcuts without implying that they are selected.
11. Allow the Players table to be filtered by goalkeeper, defender, defensive
    midfielder, midfielder, attacking midfielder and attacker units. Filtering
    changes presentation only and must not remove players from the squad model.
12. Hide goalkeeper-specific attribute columns in mixed or outfield views and
    expose them when Goalkeepers is the only selected position filter.

## Initial delivery increment

1. Deliver the squad viewer shell, Overview, Players and Roles views first.
2. Load squad, tactic and role-knowledge data through UI-independent services;
   the view must not query SQLAlchemy or calculate scores.
3. Implement configuration-driven **Generic Role Fit** before adding tactical
   modifiers or a composite score.
4. Rank all players for a role, including explicit unavailable results when
   attributes or an assessment requirement are missing.
5. Show the best available candidate, backup candidate and uncovered state for
   each role without automatically assigning a lineup.
6. Retain the complete calculation trace required to explain and test each
   available Generic Role Fit result.
7. Use explicit role assessment weights only. Undefined weights or missing
   player attributes produce `Unavailable`, never a fabricated zero.

Tactical Fit, Position Familiarity, Overall Suitability, candidate comparison,
alternative roles and Role Health remain part of this requirement but follow
the initial increment.

## Generic analysis increment

The Generic Role Fit analysis increment must:

1. define explicit, versioned Generic Role Fit weights for every packaged
   assessable tactic role;
2. calculate every available player against the complete available role
   catalogue;
3. show best candidate, backup candidate and uncovered state for required roles;
4. show each player's best role and ordered alternative roles using the same
   scoring context;
5. identify weak required roles, concentrated role duplication and strong best
   roles unused by the selected tactic through documented thresholds;
6. retain and display the complete weighted-attribute calculation trace;
7. keep every affected result `Unavailable` when weights or required player
   attributes are missing; and
8. derive Required Role Depth from simultaneous tactic slots, ensuring a player
   cannot fill two simultaneous primary slots in the same assignment result and
   requiring complete IP/OOP evidence for a slot candidate.

Present these results in the existing Analysis tab. Best XI is delivered by
007C. Tactical Fit, Overall Suitability and recruitment recommendations remain
later increments.

## Role assessment policy management

The 0–10 Weight Editor, validated policy service, YAML import/export and legacy
scale migration are implemented in 007C. Runtime-created-role coverage and the
final explicit reassessment workflow remain subject to clean-room acceptance.

1. Provide a user-facing Role Assessment Weight Editor for Generic Role Fit
   assessment policy rather than requiring every role's weights to be maintained
   individually through the Role Profile editor.
2. Use the canonical 0–10 weight scale for all editable and persisted role
   assessment weights. Legacy 0–5 policy data must be explicitly migrated to
   0–10 rather than interpreted ambiguously at runtime.
3. Allow assessment policy to be bulk imported from and exported to a
   human-readable, versioned file keyed by semantic `roleCode`.
4. Validate imported policy before application, including unknown role codes,
   unknown attributes, invalid weights and invalid importance assignments.
5. Include confirmed runtime-created roles in the editor. A role without an
   explicit assessment policy remains `Unavailable`; the editor must not invent
   default weights.
6. Keep factual FM role-definition evidence separate from FMSAT assessment
   policy. Captured role attributes describe the role; weights and importance
   describe FMSAT's scoring policy.
7. Saving or importing assessment policy must make affected Generic Role Fit,
   role-depth and Best XI results eligible for explicit reassessment without
   requiring tactic or squad OCR regeneration.

This work remains within requirement 007 and does not require a separate
product requirement.

## Role Cards

Each Role Card must show enough information to understand the role at a glance,
including:

1. role name, abbreviation, formation row and duty;
2. current starter when assigned;
3. overall Role Health;
4. whether suitable backup is available; and
5. whether the current state indicates a future squad-planning need.

The card must remain concise and selectable. Selection opens the corresponding
Role Workspace.

## Role Workspace

1. Use **Role Workspace** consistently rather than **Role Detail**.
2. Show the selected role, duty, canonical position and tactical context.
3. Provide an Overview of current starter, backup, emergency cover and Role
   Health.
4. Provide a Candidates view ranking every player in the selected squad.
5. Provide a Comparison view for two or more selected candidates.
6. Structure the workspace so History, Development and Recruitment views can be
   added later without making them part of this requirement.

## Candidate ranking

1. Consider every player in the squad; do not silently exclude players because
   their natural-position familiarity is low.
2. Rank candidates by Overall Suitability from highest to lowest by default.
3. Show each candidate's score, name, natural-position familiarity and relevant
   assessment state.
4. Prepare filters for Natural only, Accomplished+, Competent+ and All players;
   **All players** must preserve the complete candidate set.
5. Make ranking deterministic when candidates have equal scores.
6. Clearly identify unavailable scores caused by missing attributes or tactical
   data rather than treating them as zero.
7. Show each player's best calculable role within the selected tactic alongside
   every role-candidate row; show `Unavailable` when no role can be calculated.

## Suitability model

Calculate and display three independent scores for each player-role pairing:

1. **Generic Role Fit** — how well the player's attributes match the configured
   generic Football Manager role profile.
2. **Tactical Fit** — how well the player fits the role within the selected
   tactic, including applicable tempo, passing, defensive-line, pressing,
   width and transition modifiers.
3. **Overall Suitability** — a configurable weighted combination of Generic
   Role Fit, Tactical Fit and Position Familiarity.

Role definitions, attribute weights, tactical modifiers and overall weighting
must be configuration-driven, versioned or otherwise traceable, and testable.
Scores must use one documented scale and apply rounding consistently. Do not
invent a modifier when the structured tactic provides no supporting evidence.

## Explainability

1. Every displayed suitability score must have a human-readable explanation.
2. Show the key attributes and tactical factors that contributed positively or
   negatively.
3. Present understandable Strengths and Weaknesses rather than exposing only an
   unexplained percentage.
4. Allow the user to distinguish generic role contribution, tactical modifiers
   and position-familiarity contribution to the overall score.
5. Retain enough calculation detail to reproduce a result during testing and
   troubleshooting.
6. When a role is defined for a player highlight the key stats for that role against the player, good stats in green and weak stats in red.

## Candidate comparison

1. Allow two or more candidates to be selected for comparison within one role.
2. Compare Generic Role Fit, Tactical Fit, Overall Suitability, position
   familiarity, key attributes, strengths and weaknesses side by side.
3. Keep all candidates evaluated against the same tactic, role, duty,
   configuration version and scoring scale.

## Alternative roles

1. Show each player's best alternative tactical roles.
2. Rank alternatives using the same suitability engine and explainability rules.
3. Display role identity, tactical unit and score or rating.
4. Do not confuse an alternative tactical role with the player's stored natural
   position.

## Role Health

1. Calculate Role Health separately from individual player suitability.
2. Make the health model explainable and configuration-driven.
3. It may consider candidate quality, depth, tactical suitability, age profile
   and succession coverage only where the necessary data is available.
4. Show unavailable components explicitly and do not infer missing age or
   succession data.
5. Summarize whether the role has starter, backup and reserve coverage without
   presenting future recruitment targets in this requirement.

## Services and persistence

1. Keep scoring, explanation, ranking and Role Health independent from Qt.
2. Use application services to load a tactic, squad and scoring configuration,
   then produce Role Workspace view models.
3. The UI must not calculate scores or query SQLAlchemy directly.
4. Preserve sufficient scoring inputs, configuration identity and generated
   results to explain the current view consistently after restart where results
   are persisted or cached.
5. Recalculate or invalidate affected assessments when the tactic, squad data,
   role assignment or scoring configuration changes.

## Acceptance criteria

1. Opening a stored squad displays the squad viewer and identifies its selected
   tactic revision and assessment context; reopening the squad restores the most
   recently selected applied tactic.
2. Overview, Players, Roles and Analysis views are available, with useful empty
   states for analysis not yet generated or tactic context not yet selected.
3. Every role in a confirmed selected tactic appears once in the role-level
   navigator, while simultaneous Required Role Depth remains slot-specific.
4. Roles are grouped/ordered using the shared tactical-unit ordering and styled
   using the shared visual language.
5. Selecting a role exposes its candidate workspace.
6. The Candidates view ranks every squad player for the selected role subject to
   the currently defined presentation eligibility rules.
7. Each ranking exposes Generic Role Fit and later Tactical Fit/Overall
   Suitability as those calculation stages become available; an unavailable
   stage is never displayed as zero.
8. Every displayed score provides a human-readable, reproducible explanation.
9. Required Role Depth uses unique-player simultaneous assignment and retains
   separate IP/OOP evidence for each slot.
10. Each player exposes their best alternative roles where evidence permits.
11. Role Health remains visibly and computationally separate from player
   suitability when that later stage is delivered.
12. Missing or incomplete inputs are shown clearly and never silently converted
    into misleading scores; missing abbreviations show `Unknown`.
13. Double-clicking a player opens a dedicated Player Editor for factual model
    corrections, and saving those corrections persists the model and rebuilds
    the derived Roles/Analysis views.
14. Automated tests cover scoring, weighting, role-depth assignment, ranking,
    explanations, alternative roles, player editing, tactic persistence,
    invalidation and the main workspace behaviours delivered to date.
15. Existing tactic extraction, tactic viewing, squad import and
    structured-tactic correction workflows remain compatible.

## Out of scope

- Recruitment searches, transfer targets and transfer recommendations.
- Historical occupants or match appearances within a role.
- Injury-management and contract-planning workflows.
- Youth-development projections.
- Automated starter selection or lineup changes.
- Modifying Football Manager or reading its save files.

## Verification and traceability

### 007A — Generic Role Fit policy foundation

- Implementation: `config/roleAssessment.yaml`, role-assessment configuration
  loading/validation and the existing Generic Role Fit calculation service.
- Tests: `tests/test_roleAssessmentPolicy.py` plus the existing Generic Role Fit
  calculation tests.
- Behaviour: packaged assessable roles require explicit valid weights; missing
  weights or required player attributes remain `Unavailable`; complete weighted
  contributions are retained for explanation.
- Status: implemented.

### 007B — Role depth and player evidence workflow

- Implementation: `core/roleDepth.py`, `core/squadAssessment.py`,
  `app/squadDetailModel.py`, `app/squadRolesWorkspace.py`,
  `app/squadAnalysisWorkspace.py`, `app/playerEditorDialog.py`,
  `app/squadPlayersWorkspace.py`, `database/activeTacticDatabase.py` and the FM26
  squad-header recovery in `core/parser/squadAttributesFm26.py`.
- Tests: `tests/test_roleDepth.py`, `tests/test_squadAnalysisWorkspace.py`,
  `tests/test_squadRolesWorkspace.py`, `tests/test_playerEditorDialog.py`,
  `tests/test_tacticSelectionPersistence.py`, `tests/test_naturalFitnessHeader.py`
  and related squad assessment/presentation tests.
- Behaviour: slot depth is simultaneous and unique-player; missing evidence stays
  explicit; factual player edits and active tactic selection persist; derived
  analysis is rebuilt rather than edited directly.
- Status: implementation complete; awaiting final full-suite and manual
  reference-squad verification.

### 007C — Best XI and clean-room stabilization

- Implementation: `core/bestXi.py`, `core/roleDepth.py`,
  `core/playerIdentity.py`, `core/squadModel.py`,
  `core/roleAssessmentPolicy.py`, `app/roleAssessmentWeightEditor.py`,
  `app/squadPlayersWorkspace.py` and the welcome/import lifecycle services.
- Tests: `tests/test_bestXi.py`, `tests/test_bestXiWorkspace.py`,
  `tests/test_roleDepth.py`, `tests/test_playerIdentity.py`,
  `tests/test_squadModel.py`, `tests/test_roleAssessmentWeightEditor.py`,
  `tests/test_filteredSevenSquadOcr.py`, `tests/test_cleanRoom007b.py` and
  related parser, vocabulary and window-lifecycle regressions.
- Behaviour: Best XI requires position-family eligibility and optimizes the
  whole simultaneous assignment; malformed phase evidence is isolated per
  slot; player identity reconciles across captures while manual corrections
  remain authoritative; filtered squad captures merge incrementally; role
  policy is editable on the canonical 0–10 scale; clean-room OCR and lifecycle
  defects retain focused regression coverage.
- Status: implemented; the integrated full suite passes (501 passed, 9 skipped),
  with opt-in OCR and manual clean-room acceptance remaining. Requirement 007 remains
  `InProgress` for later Tactical Fit,
  Overall Suitability, comparison and Role Health scope.

## Change history

- 2026-08-16: recorded completion of the 007A assessment-policy foundation and
  explicit pause before 007B while structured tactic extraction was verified.
- 2026-08-18: recorded 007B role-depth intelligence, active-tactic persistence,
  Player Editor, Unknown-role workflow and final FM26 squad-header recovery as
  implemented pending final verification.
- 2026-08-24: added Role Assessment Policy Management as requirement 007
  follow-up work, covering the 0–10 editor, bulk import/export, runtime-created
  roles and explicit reassessment.
- 2026-08-26: recorded 007C Best XI position-family eligibility and clean-room
  stabilization, including partial-slot recovery, player identity
  reconciliation, incremental squad imports and the implemented Weight Editor.

## Future foundation

The Role Workspace must be extensible for later History, Development and
Recruitment views. Future Squad Planner, Recruitment Centre, Injury Management,
Contract Planning, Youth Development and Transfer Recommendation features
should consume tactical roles rather than treating individual player records as
the primary planning object.
