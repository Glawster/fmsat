# Implementation prompt — Requirement 007

## Project

Football Manager Squad Assessment Tool — FMSAT

- Repository: `Glawster/fmsat`
- Prerequisites: requirement 006 structured tactic extraction, requirement 009
  tactic viewer baseline and requirement 010 factual role definitions

## Objective

Implement requirement
[`007-roleCentricSquadAssessment.md`](../features/007-roleCentricSquadAssessment.md).
Create a dedicated squad viewer in the same visual family as the tactic viewer.
Make the tactical role the primary squad-planning object inside that viewer.
Players are evaluated against roles; roles are not reduced to labels on player
records.

## Architecture boundary

Inspect the delivered Phase 3 domain, service, persistence and review
architecture before changing code. Extend it without creating a parallel model.
Preserve project conventions, dependency injection, camelCase project-owned
Python names, configuration-driven behavior, SQLAlchemy boundaries, mocked OCR
tests and existing desktop and CLI workflows.

Keep these layers separate:

1. role profiles, weights and tactical modifiers in validated configuration;
2. pure scoring, explanation, ranking and Role Health domain services;
3. application services that load structured tactics and squad snapshots;
4. optional persistence or cache invalidation; and
5. PySide6 Role Cards and Role Workspaces that render view models only.

The UI must not implement scoring formulas or query SQLAlchemy directly.

## Initial delivery workflow

1. Open a stored squad in a dedicated squad viewer.
2. Provide Overview, Players, Roles and Analysis navigation with useful states
   when no tactic or generated analysis is available.
3. Show the selected squad, tactic revision, squad-data date and
   knowledge/scoring identity without coupling those sources.
4. Group one selectable Role Card per required tactic role using requirement
   005's colour families and abbreviation icons.
5. Open a Role Workspace with Overview and Candidates views prepared for later
   Comparison support.
6. Rank every squad player using configuration-driven Generic Role Fit.
7. Treat missing attributes or role requirements as unavailable, not zero.
8. Explain the weighted attribute contributions for every available result.
9. Show the best candidate, backup candidate and uncovered state without
   automatically assigning a lineup.

After the initial increment, add Tactical Fit, Position Familiarity, Overall
Suitability, candidate comparison, alternative roles and Role Health through
the same domain and application-service boundaries.

Use **Role Workspace**, never **Role Detail**, in new user-facing text and
documentation.

## Scoring constraints

- Consider all players unless the user applies an explicit familiarity filter.
- Use configuration-driven role attribute weights, tactical modifiers and
  overall component weights.
- Apply one documented numeric scale and deterministic rounding and tie-breaking.
- Never invent tactical modifiers unsupported by the structured tactic.
- Treat unavailable inputs as unavailable, not zero.
- Make every result reproducible from its player snapshot, structured tactic,
  role/duty and scoring-configuration identity.
- Invalidate affected results when any of those inputs changes.

The explanation model must expose why a score changed and distinguish generic
role fit, tactical fit and position familiarity. An unexplained percentage is
not acceptable.

## Role Health boundary

Role Health is a role-level planning measure, not a player-quality score. Keep
it separate in the domain and UI. It may combine available quality, depth,
tactical suitability, age profile and succession coverage, but missing data
must be declared and excluded through documented behavior.

Show starter, backup and reserve coverage. Do not implement recruitment searches
or targets; only leave an extensible foundation for a future Recruitment view.

## Tests

Use deterministic fixtures and do not require live OCR. Cover at minimum:

- generic role weights and boundary scores;
- supported tactical modifiers and absent modifiers;
- position-familiarity contribution;
- configurable overall weights and rounding;
- missing input behavior;
- complete ranking and deterministic ties;
- human-readable explanation contributions;
- comparisons using identical scoring context;
- alternative-role ordering;
- Role Health separation and incomplete components;
- cache/result invalidation;
- one card per structured role, tactical grouping and colour mapping;
- Role Workspace navigation and all-player candidate visibility; and
- backward compatibility with structured tactic review and squad import.

## Documentation

Update FMSAT user and architecture documentation with the role-centric workflow,
scoring model, configuration, explainability, Role Health distinction, known
limitations and future extension points.

## Definition of done

The initial squad-viewer increment is ready for review when its defined workflow
is implemented, Generic Role Fit is explainable and reproducible, existing
workflows remain compatible, and the complete applicable test, Ruff and Black
checks pass. Requirement 007 is complete only when every acceptance criterion
in the stable requirement is met.

## Explicit non-goals

Do not implement recruitment execution, transfer searches, history, injury or
contract planning, youth projections, automatic lineup selection, Football
Manager automation or save-file reading.
