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
   imported squad or tactic.
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
   multiple positions or tactic slots is assessed once.
9. Allow corrections to squad object-model values from the Players view. Saving
   a correction makes the edited object model authoritative and marks its
   retained screenshot evidence as superseded without deleting that evidence.
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

The next increment after the merged squad-viewer foundation must:

1. define explicit, versioned Generic Role Fit weights for every canonical
   tactic role;
2. calculate every available player against the complete role catalogue;
3. show best candidate, backup candidate and uncovered state for required roles;
4. show each player's best role and ordered alternative roles using the same
   scoring context;
5. identify weak required roles, concentrated role duplication and strong best
   roles unused by the selected tactic through documented thresholds;
6. retain and display the complete weighted-attribute calculation trace; and
7. keep every affected result `Unavailable` when weights or required player
   attributes are missing.

Present these results in the existing Analysis tab. Best XI, Tactical Fit,
Overall Suitability and recruitment recommendations remain later increments.

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
   tactic revision and assessment context.
2. Overview, Players, Roles and Analysis views are available, with useful empty
   states for analysis not yet generated or tactic context not yet selected.
3. Every role in a confirmed selected tactic appears once as an individual Role
   Card.
4. Cards are grouped and styled using the shared tactical colour families.
5. Selecting a card opens its Role Workspace.
6. The Candidates view ranks every squad player for the selected role.
7. Each ranking exposes Generic Role Fit, Tactical Fit and Overall Suitability
   as those calculation stages become available; an unavailable stage is never
   displayed as zero.
8. Every score provides a human-readable, reproducible explanation.
9. Two or more candidates can be compared against the same role.
10. Each player exposes their best alternative roles.
11. Role Health remains visibly and computationally separate from player
   suitability.
12. Missing or incomplete inputs are shown clearly and never silently converted
    into misleading scores.
13. Automated tests cover scoring, weighting, tactical modifiers, ranking,
    explanations, comparisons, alternative roles, Role Health, invalidation and
    the main workspace behaviors.
14. Existing tactic extraction, tactic viewing, squad import and
    structured-tactic correction
    workflows remain compatible.

## Out of scope

- Recruitment searches, transfer targets and transfer recommendations.
- Historical occupants or match appearances within a role.
- Injury-management and contract-planning workflows.
- Youth-development projections.
- Automated starter selection or lineup changes.
- Modifying Football Manager or reading its save files.

## Future foundation

The Role Workspace must be extensible for later History, Development and
Recruitment views. Future Squad Planner, Recruitment Centre, Injury Management,
Contract Planning, Youth Development and Transfer Recommendation features
should consume tactical roles rather than treating individual player records as
the primary planning object.
