# Current Development Increment

## Increment

007D — Role Assessment Weight Matrix

## Status

Active

## Requirement

`project/requirements/features/007-roleCentricSquadAssessment.md`

## Objective

Provide a single visual overview of Generic Role Fit assessment policy and let the user
control which configured Football Manager attributes participate in FMSAT.

## Scope

- Expose **View → Weights** from the main application menu.
- Display roles on the Y axis and configured attributes on the X axis.
- Show each role/attribute 0–10 weight in the matrix.
- Colour Top Three green, Important blue and Nice to Have grey.
- Use the attribute column header itself as the active/inactive control.
- Grey inactive attributes while retaining their configured role weights.
- Apply attribute activation to subsequent capture and UI construction without OCR
  regeneration.
- Open the existing Role Editor when the user clicks a role identifier, then refresh the
  matrix when editing returns.
- Retain validated YAML import/export and explicit legacy 0–5 migration.
- Include confirmed runtime-created semantic roles where available.

## Verification

- [ ] Focused configuration and weight-matrix tests pass.
- [ ] Full automated suite passes.
- [ ] View → Weights opens the matrix in the desktop application.
- [ ] Role identifiers open the Role Editor and saved changes refresh the matrix.
- [ ] Clicking an attribute heading persists and immediately reflects active/inactive state.
- [ ] Activating Long Shots makes it available to subsequent FMSAT capture/presentation;
      deactivating it preserves existing weights and evidence.
- [ ] Explicit squad Reassess consumes changed role policy without OCR regeneration.

## Next

Complete 007D acceptance, then proceed to the tactic Analysis increment.
