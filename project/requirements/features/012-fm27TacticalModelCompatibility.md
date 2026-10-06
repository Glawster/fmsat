# 012 — FM27 tactical model compatibility

## Status

ToDo

## Outcome

As a manager using FMSAT with Football Manager 2027, I need FMSAT's tactical
analysis model to represent phase-specific behaviours and FM27 tactical
instructions without corrupting Generic Role Fit, so that later Tactical Fit,
Best XI and recruitment analysis can use an explicit, explainable evidence
model rather than hidden score adjustments.

## Context

Football Manager 2027 developer material published during development describes
changes that are relevant to FMSAT's tactical model, including stronger
match-engine significance for selected attributes, player instructions that
control how players attack the penalty area, temporary Tactical Tweaks, and
expanded match-analysis evidence such as heat maps, action zones and pass maps.

Requirement 011 already models tactic demand separately for In Possession and
Out Of Possession and deliberately avoids a synthetic overall attribute-demand
score. Requirement 007 owns Generic Role Fit and squad-vs-tactic assessment.
Requirement 010 owns explicit role-assessment knowledge and tactical modifiers.
Those boundaries remain valid and must not be weakened by FM27-specific work.

FM27 match-engine observations must not silently alter generic role weights.
FMSAT must distinguish a role's generic requirements from tactical behaviours
and from version-specific match-engine considerations. This requirement creates
that compatibility boundary and reserves future model concepts where the FM27
feature set makes them necessary.

Sports Interactive has also announced a new Tactical Effectiveness system for
FM27. Its full behaviour is not yet sufficiently evidenced for FMSAT to model.
Design of FMSAT Tactical Fit/Tactical Effectiveness remains deferred until that
material is published and reviewed.

## Scope

- Preserve Generic Role Fit as a generic, explainable role assessment rather
  than an FM27-specific effectiveness score.
- Preserve separate In Possession and Out Of Possession demand rather than
  introducing a single overall attribute-demand score.
- Introduce or reserve an explicit behaviour layer between tactical
  instructions and attribute demand: role → phase/behaviour → attribute demand.
- Allow a tactic slot/role assignment to acquire phase-specific player
  instructions independently of the generic role definition.
- Represent FM27 box-attacking instructions as tactical behaviour evidence when
  captured, including late arrival, attacking the defensive line, near-post,
  central and far-post behaviours where Football Manager evidence supports the
  distinction.
- Keep Football Manager version-specific match-engine considerations separate
  from generic role-assessment weights.
- Record FM27 developer evidence that Stamina, Marking, Anticipation, Flair,
  Dribbling and Off The Ball have explicit or changed match-engine significance
  without automatically reweighting Generic Role Fit.
- Reserve an explicit Tactical Tweak model capable of describing a temporary
  change, its affected roles/units/behaviours and any resulting demand changes.
- Keep room for later observed-performance evidence from Football Manager
  analysis outputs such as heat maps, action zones and pass maps without making
  those inputs mandatory for current analysis.
- Ensure any FM27-derived conclusion is traceable to explicit captured evidence,
  packaged policy, or documented Football Manager source material.
- Keep missing or unsupported FM27 evidence `Unavailable` rather than inventing
  behaviour, modifiers or tactical conclusions.

## Out of scope

- Recalculating or globally changing current Generic Role Fit weights solely
  because an FM27 developer blog says an attribute has increased match-engine
  significance.
- Implementing FMSAT Tactical Fit or reproducing FM27 Tactical Effectiveness
  before the dedicated FM27 Tactical Effectiveness material has been reviewed.
- Recommending Tactical Tweaks from squad strengths in this requirement.
- Match-result ingestion, automated match review or claims that one tactical
  configuration performs better than another.
- Importing heat maps, action zones or pass maps in this requirement.
- Opposition-specific tactical advice.
- Best XI, recruitment recommendations or transfer-target selection.
- Replacing requirement 010 role knowledge with FM27-specific role definitions.
- Treating developer-blog observations as hidden constants in scoring code.

## Acceptance criteria

1. Given an existing Generic Role Fit calculation, when FM27 compatibility is
   introduced, then the generic score remains based on explicit role-assessment
   policy and is not silently changed by FM27 match-engine observations.
2. Given tactic demand, when attributes are presented, then IP and OOP remain
   distinct and no new synthetic overall-demand score is required.
3. Given a tactical instruction that changes what a player is expected to do,
   when it is modelled, then the instruction can resolve to one or more explicit
   behaviours and those behaviours can contribute transparent attribute demand
   independently of the generic role definition.
4. Given two players or slots using the same role but different supported player
   instructions, when tactic demand is analysed, then their instruction-driven
   behaviour demands can differ without requiring duplicate role definitions.
5. Given an FM27 version-specific match-engine consideration, when it affects
   analysis, then it is identifiable as version-specific evidence or policy and
   is not represented as a generic Football Manager role fact.
6. Given unsupported, ambiguous or uncaptured FM27 behaviour evidence, when
   analysis is built, then the result remains `Unavailable` rather than using an
   inferred default.
7. Given a Tactical Tweak, when the compatibility model represents it, then it
   is separate from the base tactic and can identify affected roles, units,
   behaviours and demand changes without mutating the generic role definition.
8. Given future observed-performance evidence such as heat maps, action zones or
   pass maps, then the model can associate that evidence with expected tactical
   behaviours without requiring current Generic Role Fit to consume it.
9. Given the forthcoming FM27 Tactical Effectiveness feature, then FMSAT does
   not implement an equivalent Tactical Fit calculation under this requirement;
   a follow-up decision is required after the dedicated SI material is reviewed.
10. Core compatibility logic is testable without Qt and every calculated demand
    or modifier remains explainable from source instruction/behaviour through to
    contributing attributes.

## Dependencies and decisions

- Requirement 007 owns Generic Role Fit, player rankings, Role Depth and
  squad-vs-tactic assessment.
- Requirement 009 owns saved tactic detail and the Analysis workspace shell.
- Requirement 010 owns role/attribute knowledge, assessment policy and tactical
  modifier conventions.
- Requirement 011 owns squad-independent tactic demand and IP/OOP structural
  analysis.
- `roleCode` remains the semantic role identity; do not build new FM27 logic on
  legacy coarse role-enum translations.
- FM27 compatibility extends the evidence model; it does not redefine existing
  generic role identity.
- Tactical Effectiveness/Tactical Fit design is explicitly deferred pending
  review of the dedicated FM27 developer material.

## Verification

- Regression tests proving existing Generic Role Fit values do not change merely
  by enabling FM27 compatibility metadata.
- Core tests for instruction → behaviour → attribute-demand traceability.
- Core tests proving identical roles can have different instruction-driven
  behaviour demand.
- Tests for unsupported evidence returning `Unavailable`.
- Tests proving a Tactical Tweak is additive/temporary and does not mutate base
  role knowledge or the saved base tactic.
- Tests proving FM27 version-specific modifiers are labelled and explainable.
- Existing requirement 007, 010 and 011 suites remain green.

## Traceability

- Planned branch: `feature/012-fm27-tactical-model-compatibility`
- Source review: Football Manager 2027 developer feature material reviewed
  2026-10-06, including tactical/match-engine changes and the announced future
  Tactical Effectiveness deep dive.
- Implementation: not yet allocated.
- Tests: not yet allocated.
- Documentation: not yet allocated.

## Change history

- 2026-10-06: created — preserve existing Generic Role Fit and IP/OOP demand
  boundaries while reserving an explicit FM27 behaviour and Tactical Tweak
  compatibility model; Tactical Effectiveness design deferred pending further
  Sports Interactive evidence.
