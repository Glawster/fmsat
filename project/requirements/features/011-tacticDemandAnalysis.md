# 011 — Tactic demand analysis

## Status

InProgress

## Outcome

As a manager inspecting a saved tactic, I need a squad-independent explanation
of what the tactic demands and how its simultaneous slots change between In
Possession and Out Of Possession, so that later squad fit and recruitment work
from an explicit demand model rather than from imported screenshots.

## Context

Requirement 009 reserved the Tactic workspace Analysis tab and requires only a
useful empty state that does not misrepresent generated conclusions as imported
facts. That placeholder is still what the tab shows.

Squad Analysis, owned by requirement 007, answers a different question: how well
does this squad satisfy this tactic? It already presents Best XI, Required Role
Depth, player rankings and squad findings. Those results consume players and
must not migrate onto the Tactic Analysis tab.

Tactic Analysis must answer: what does this tactic demand, and what are its
structural characteristics, regardless of the current squad? It uses the saved
football object model, `roleCode` identity, simultaneous slot linkage, position
families and explicit role-assessment weights. Missing evidence remains
`Unavailable`. Role weights are FMSAT assessment policy, not Football Manager
facts. No speculative football judgements are invented.

## Scope

- A distinct Tactic Analysis purpose: tactic demand and structure, independent
  of any squad or player.
- Simultaneous slot requirements: canonical position, IP role, OOP role,
  evidence state, and IP→OOP transition class.
- Aggregate attribute demand from explicit 1–5 or packaged-scale assessment
  weights, overall and by phase, with coverage of how many phase-roles
  contributed.
- Factual, count-based structural observations (repeated roles, flank
  asymmetry when L/R pairs exist, tracking-role counts from packaged codes,
  family-change counts, demand concentration).
- `Unavailable` for missing weights, unresolved `roleCode`, ambiguous IP/OOP
  linkage and unmapped position families. No invented defaults, ordinal
  pairing, or 0–100 demand scores.
- Core calculation in UI-independent services that emit immutable result
  objects. The PySide tab only presents those objects.
- Construction owned by the main window when a tactic object model exists;
  empty-shell copy remains requirement 009 when no model exists.
- Reanalyse from the saved object model and current role-assessment policy
  without regenerating screenshots.

## Out of scope

- Best XI, unique-player assignment, role-depth primary/backup, player
  rankings.
- Recruitment recommendations or transfer targets.
- Tactical Fit, Overall Suitability, Role Health, traits, form, morale, injury.
- Opposition-specific conclusions such as weakness against a low block.
- Reinterpreting team instructions as quality or style labels.
- Persisted analysis snapshots, last-analysed date, or immutable analysis
  revisions.
- `majorStructuralTransition` labels without an explicit evidence model.
- Reading `Position.player`, CA/PA, player attributes, duty, or any squad
  model field as analysis inputs.
- Physical/work-rate profile counts until attribute categories exist in
  requirement 010.
- Two-tactic comparison UI.
- Implementing this as an increment of requirement 007.

## Acceptance criteria

1. Given a saved football object model with simultaneous slots, when the Tactic
   Analysis tab opens, then it presents role requirements, aggregate attribute
   demand, phase-change classes and structural observations derived only from
   that tactic and current role-assessment policy.
2. Given no football object model, when the Analysis tab opens, then the 009
   empty shell is shown and no demand numbers are invented.
3. Given missing role weights, unresolved `roleCode`, ambiguous IP/OOP linkage
   or unmapped position families, when analysis is built, then those items are
   `Unavailable` and are not replaced by zero, a default role, or ordinal
   pairing.
4. Given a squad assigned to the tactic, or `Position.player` set on slots, when
   analysis is built, then the result does not change and no player names appear.
5. Given the same tactic and policy, when analysis is rebuilt, then the result
   is deterministic.
6. Given Best XI, role depth or recruitment content, when the Tactic Analysis
   tab is shown, then that content is absent; it remains on Squad Analysis or
   later requirements.
7. Given a change to role-assessment policy, when the user reanalyses, then
   demand is recalculated from the saved object model without screenshot OCR.
8. Core analysis is testable without a Qt event loop. The view does not sum
   weights, classify transitions or resolve roles.

## Dependencies and decisions

- Requirement 009 owns the Analysis tab shell and incomplete-model empty state.
- Requirement 007 owns squad-vs-tactic assessment (Best XI, depth, player
  rankings). 011 must not absorb that outcome.
- Requirement 006 supplies `slotId`, canonical role/position and the rule that
  missing evidence is not invented.
- Requirement 010 supplies knowledge layers; assessment weights remain FMSAT
  policy.
- Design record: Tactic Analysis tab purpose (2026-08-22), implemented as this
  requirement rather than 007C or 007D.

## Verification

- Core tests for demand aggregation, IP/OOP separation, phase transitions,
  repeated roles, missing weights, unresolved identity, ambiguous linkage,
  one-phase tactics, deterministic output and no squad/player dependency.
- UI tests for empty-model copy, Unavailable cells, Reanalyse without OCR, and
  absence of player names.
- Role Depth and Best XI suites must remain green if shared slot pairing is
  extracted.

## Traceability

- Implementation: `core/tacticSlots.py`, `core/tacticAnalysis.py`; UI pending
- Tests: `tests/test_tacticSlots.py`, `tests/test_tacticAnalysis.py`; Role Depth
  and Best XI suites remain green
- Documentation: pending (`documentation/tacticAnalysis.md` after behaviour is
  delivered)
- Pull request: pending
- Agent runs: None

## Change history

- 2026-08-28: created — allocate tactic demand analysis as requirement 011
  before core/UI delivery; 009 keeps the empty shell.
- 2026-08-28: PR 1 — extract shared IP/OOP position pairing without changing
  Role Depth resolution or Best XI.
- 2026-08-28: PR 2 — add TacticAnalysisService and immutable demand results;
  Analysis tab still 009 empty shell.
