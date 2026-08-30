# Current Development Increment

## Increment

011 — Explain Tactic Analysis follow-up

## Status

Active

## Requirement

`project/requirements/features/007-roleCentricSquadAssessment.md`

## Objective

Make squad-independent Tactic Analysis understandable to a Football Manager user while
retaining deterministic calculation evidence and the existing requirement boundaries.

## Scope

- Add plain-English guidance to all three analysis sections.
- Make useful rows click-accessible through a reusable explanation dialog.
- Separate plain meaning, football meaning and deterministic calculation evidence.
- Retain explicit Attribute Demand phase-role contributors in immutable core results.
- Explain evidence and transition states without recommendations or squad content.

## Verification

- [x] Focused core, display and Qt interaction tests pass.
- [x] Full automated suite passes.
- [x] Each table row opens the correct deterministic explanation.
- [x] Tracking observations use display names in primary UI text.
- [x] No squad-dependent or qualitative tactical advice appears.

## Next

Run focused and full checks, then manually inspect dialog layout in the desktop UI.
