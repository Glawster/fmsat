# Source prompt — requirement 011

Requirement: 011 — project/requirements/features/011-tacticDemandAnalysis.md
Role: implement

Read the requirement and applicable repository instructions before changing
anything. Deliver the agreed Tactic Analysis outcome only. Preserve the stated
exclusions and keep Squad Analysis conceptually separate.

Tactic Analysis answers: what does this tactic demand, and how do simultaneous
slots change between In Possession and Out Of Possession, regardless of squad?

Squad Analysis remains: how well does this squad satisfy this tactic?

## Constraints

- Core/business logic stays outside PySide (`core/`, not `app/`).
- Use `roleCode` as the semantic role identity.
- Missing evidence remains `Unavailable`. Do not invent defaults, ordinal
  IP/OOP pairing, or 0–100 demand scores.
- Role weights are explicit assessment policy, not Football Manager facts.
- Do not silently infer football knowledge or opposition judgements.
- Do not read `Position.player`, duty, CA/PA or any squad/player model.

## Delivery order

1. This record (PR 0) — already created.
2. Extract shared IP/OOP position pairing only, without changing Role Depth
   resolution or Best XI.
3. `TacticAnalysisService` and immutable result objects, with tests.
4. Tactic Analysis dashboard through `MainWindow.tacticShow`, after 007C is
   accepted or paused if it would mix reviews.
5. Living algorithm guide `documentation/tacticAnalysis.md` and 011
   traceability.

If the requirement is ambiguous or the outcome must change, stop and report the
decision needed. Do not infer new scope.

Handoff with:

- files changed and why;
- acceptance criterion-to-evidence mapping;
- commands run and results;
- assumptions, risks and unresolved items.
