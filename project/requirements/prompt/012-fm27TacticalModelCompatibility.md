# Source prompt — requirement 012

Requirement: 012 — project/requirements/features/012-fm27TacticalModelCompatibility.md
Role: implement

Read the requirement and applicable repository instructions before changing
anything. Deliver only the compatibility boundary described by requirement 012.
Do not redesign Generic Role Fit or implement Tactical Fit from incomplete FM27
information.

## Constraints

- Preserve current Generic Role Fit semantics and existing explicit assessment
  policy unless a separate evidence-backed requirement changes them.
- Preserve separate IP/OOP demand. Do not introduce a synthetic overall demand
  score.
- Use `roleCode` as the semantic role identity.
- Model tactical demand through explicit instruction/behaviour evidence rather
  than hidden score adjustments.
- Keep FM27 version-specific considerations distinguishable from generic role
  knowledge.
- Missing or unsupported evidence remains `Unavailable`.
- Core/business logic stays outside PySide.
- Tactical Tweaks must remain separate from the saved base tactic and generic
  role definition.
- Do not implement or imitate FM27 Tactical Effectiveness until its dedicated
  Sports Interactive material has been reviewed and a follow-up requirement is
  agreed.

## Delivery intent

1. Define the smallest explicit behaviour model needed to separate generic role
   knowledge from tactic/player-instruction demand.
2. Add FM27-compatible player-instruction evidence without changing current role
   weights by implication.
3. Add or reserve a Tactical Tweak representation that is temporary and
   traceable.
4. Preserve compatibility with requirements 007, 010 and 011 and keep their
   regression suites green.
5. Document every version-specific assumption and the evidence supporting it.

If implementing the requirement would require guessing unpublished FM27 Tactical
Effectiveness behaviour, stop that part and leave it deferred rather than
inventing policy.

Handoff with:

- files changed and why;
- acceptance criterion-to-evidence mapping;
- commands run and results;
- assumptions, version-specific evidence, risks and unresolved items.
