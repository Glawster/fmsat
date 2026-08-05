# 007 — Role-centric squad assessment

## Status

Backlog

## Objective

Present a confirmed structured tactic primarily as a collection of tactical
roles rather than a list of players. Make each role a long-lived planning object
against which players are ranked, compared and explained, and on which later
squad-depth and recruitment workflows can be built.

## Dependencies

1. Consume the validated structured tactic produced by requirement 006.
2. Use requirement 005's six tactical colour families and role icons.
3. Keep each player's imported natural positions separate from their
   tactic-specific role suitability and assignments.
4. Do not calculate or display a role assessment when its underlying tactic or
   required player attributes are incomplete without clearly reporting that
   limitation.

## Tactic workspace

1. Organize the tactic workspace as **Overview**, **Roles**, **Pitch**,
   **Instructions** and **Sources**.
2. Make **Roles** the default view.
3. Retain **Pitch** as a tactical visualization rather than the primary planning
   interface.
4. Present every role required by the tactic as an individual selectable Role
   Card grouped into goalkeeper, defence, defensive midfield, midfield,
   attacking midfield and striker units.
5. Use the shared palette subtly through headers, borders, role icons or badges
   while preserving readability in light and dark themes.

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

1. Every role in a confirmed tactic appears once as an individual Role Card.
2. Cards are grouped and styled using the shared tactical colour families.
3. Selecting a card opens its Role Workspace.
4. The Candidates view ranks every squad player for the selected role.
5. Each ranking exposes Generic Role Fit, Tactical Fit and Overall Suitability.
6. Every score provides a human-readable, reproducible explanation.
7. Two or more candidates can be compared against the same role.
8. Each player exposes their best alternative roles.
9. Role Health remains visibly and computationally separate from player
   suitability.
10. Roles is the default tactic view and Pitch remains available.
11. Missing or incomplete inputs are shown clearly and never silently converted
    into misleading scores.
12. Automated tests cover scoring, weighting, tactical modifiers, ranking,
    explanations, comparisons, alternative roles, Role Health, invalidation and
    the main workspace behaviors.
13. Existing tactic extraction, squad import and structured-tactic correction
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
