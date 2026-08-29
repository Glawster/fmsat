# Tactic Analysis

## Purpose

Tactic Analysis answers a different question from Squad Analysis.

**Squad Analysis asks:** how well does this squad satisfy this tactic?

**Tactic Analysis asks:** what does this tactic demand, regardless of who is in the squad?

Squad Analysis, owned by requirement 007, already presents Best XI, Required Role Depth,
player rankings and squad findings. Those results consume players. They must not appear on
the Tactic workspace Analysis tab.

Tactic Analysis is a demand and structure report for one saved football object-model tactic.
It uses simultaneous slot linkage, `roleCode` identity, position families and the current
role-assessment policy. It does not assign players, score Generic Role Fit, or invent
football judgements.

When no football object model exists, the tab keeps the requirement 009 empty shell and
does not invent demand numbers.

## Evidence used

Tactic Analysis does not invent a new rating scale.

Inputs are:

- the saved football object-model tactic (In Possession and Out Of Possession positions);
- canonical tactical vocabulary and confirmed role definitions;
- `RoleKnowledgeService.weightsLoad` (user file if non-empty, otherwise packaged policy);
- `positionFamilyFor` for exact position codes.

It does **not** read an assigned footballer, duty, CA/PA, player attributes, or any squad
model. An assigned name on a position cannot change the result.

Role weights are FMSAT assessment policy, currently the packaged 0–10 Generic Role Fit
scale identified by `config/roleAssessment.yaml` `identity`. They are not Football Manager
facts. Stored `0` is an omitted attribute, matching Generic Role Fit, not a demand of zero.

Missing evidence remains `Unavailable`. The service does not substitute a default role,
ordinal IP/OOP pairing, or a 0–100 demand score.

## Slot linkage

Simultaneous slots are paired in `core/tacticSlots.py` before roles are resolved.

1. Unique matching `slotId` values in every populated phase form durable pairs.
2. If no shared unique id exists, spatial recovery may pair equal-sized phases when
   coordinates exist, the largest pair distance is at most 0.38 in normalised pitch units,
   and the next-best complete mapping is not within 0.05 of the best cost.
3. List order is not evidence. IP position `i` is not paired with OOP position `i` merely
   because they share an index.
4. Failed pairing retains every observed phase position as its own unlinked slot. It does
   not invent a partner.

A one-phase tactic (empty other formation) is complete evidence of that phase. The missing
side is `missingPhase`, not a linkage failure.

`weightExpectedPhaseRoles` is `len(inPossession.positions) + len(outOfPossession.positions)`
on the tactic object. Unlinked 11+11 therefore expects 22, not 11. An IP-only tactic
expects 11.

Role Depth reuses the same pairing helper but still shows one assignment row per
simultaneous slot. That adapter is squad assessment, not Tactic Analysis.

## Role resolution

Each present position is resolved with the Squad Assessment vocabulary path:
`TacticVocabulary.roleNormalize` on `canonicalRole` or the observed profile abbreviation,
then a unique confirmed-definition match. Role Depth's catalogue matcher is not used here.

Evidence state is first-match:

1. no `Position` → `missingPhase`
2. present position, `roleCode is None` → `unresolved`
3. `assessmentRequired` is false and `weightsLoad` is empty after packaged fallback →
   `recognitionOnly` (packaged Tracking Winger and Tracking Wide Midfielder today)
4. resolved identity but no usable 1–10 weights → `missingWeights`
5. otherwise `ready`

Packaged Tracking Attacking Midfielder has weights, so it is `ready` and included in
demand. Tracking Winger without weights is shown and excluded from demand. A stored value
that is not an integer, or is outside 0–10, fails the whole phase-role.

## Attribute demand

Demand is a raw sum of usable policy weights across **weight-complete** phase-roles
(`resolutionState == ready`). It is not Generic Role Fit and is not normalised to 0–100.

```text
demand_overall(attribute) = Σ weight(attribute, r) for ready phase-roles
demand_ip(attribute)      = Σ weight(attribute, r) for ready IP phase-roles
demand_oop(attribute)     = Σ weight(attribute, r) for ready OOP phase-roles
```

A phase column is `Unavailable` only when that phase has no ready role. `0` in a phase
column is legal only when that phase has at least one ready role and the attribute is
omitted (or stored as 0 and stripped) on those roles.

Locked one-slot example using current packaged weights:

- IP Inside Forward omits `work_rate`.
- OOP Tracking Attacking Midfielder has a positive `work_rate` weight.
- Overall Work Rate equals that OOP weight, IP Work Rate is `0`, OOP Work Rate is the
  packaged value, and one phase-role contributed.

If no phase-role is ready, `overallDemand` is empty and the Attribute Demand card shows
`Unavailable` rather than a table of zeros. Excluded roles (unresolved, recognition-only,
missing weights, missing phase) contribute nothing, not zero.

Rows are attributes that appear in at least one ready mapping, ordered by overall demand
descending then attribute identity. Coverage is
`weightCompletePhaseRoles / weightExpectedPhaseRoles`.

Changing role-assessment policy and choosing **Reanalyse Tactic** recalculates from the
saved object model. It does not regenerate screenshots.

## Phase changes

Each slot is classified only after linkage and both phase positions exist.

| Class | Rule |
| --- | --- |
| `unavailable` | Unlinked slot, `missingPhase`, unresolved `roleCode`, or unmapped position family |
| `unchanged` | Both `roleCode` values resolved and equal |
| `roleChangeSameFamily` | Both families resolved and equal; role codes differ |
| `familyChange` | Both families resolved and differ |

Families come from `positionFamilyFor` on the exact canonical position code, not from
role-vs-family eligibility policy. Equal role codes in the same family remain `unchanged`
even when the exact codes differ (`MC` vs `MCL`). There is no `majorStructuralTransition`
class.

The Position cell may show `AML → ML` when the two exact codes differ. That display string
is not a sort key. Slots are ordered from forwards back to goalkeeper using the IP-if-present
canonical position, then the compact code, then `slotId`.

## Structural observations

Observations are counts and identity lists. They are not advice.

| Code | Fact | Omitted when |
| --- | --- | --- |
| `repeatedRole` | Same resolved `roleCode` in two or more slots of one phase | Unique roles; unresolved identities are not grouped |
| `asymmetricFlank` | Both sides of an L/R pair exist in **that** phase and the resolved roles differ | The pair is absent in that phase (not Unavailable) |
| `trackingRoleCount` | Count of phase-roles whose `roleCode` is in the packaged tracking set | Never; `0` is complete evidence |
| `familyChangeCount` | `N of M` linked slots classifiable as `familyChange` | No classifiable slots |
| `demandConcentration` | Top three overall attributes by demand | `overallDemand` is empty |

Tracking membership is the closed set `trackingCentreForward`,
`trackingAttackingMidfielder`, `trackingWideMidfielder`, `trackingWinger`. Do not infer
membership from a `tracking` prefix or a `Tracking` display name. Update the set in the
same change as any new packaged Tracking vocabulary entry.

Flank pairs are the exact codes already in `positionFamilyFor`: `DL/DR`, `DCL/DCR`,
`WBL/WBR`, `DMCL/DMCR`, `MCL/MCR`, `ML/MR`, `AMCL/AMCR`, `AML/AMR`, `STCL/STCR`. Central
codes such as `DC` never pair. IP/OOP pairing failure does not blank a resolved IP flank.

A pair present in a phase with an unresolved side is reported Unavailable for that pair.

## Presentation

`MainWindow.tacticShow` constructs `TacticAnalysisService.analysisBuild` when a football
object model exists. The Analysis tab maps that immutable result to strings in
`app/tacticAnalysisDisplay.py`. The view does not sum weights, classify transitions, or
resolve roles.

The dashboard shows a policy/coverage banner, Role Requirements, Attribute Demand and
Structural Observations. **Reanalyse Tactic** rebuilds demand from the saved model and
current policy. The tooltip states that it does not regenerate screenshots.

Best XI, role-depth primary/backup and player names do not appear on this tab.

## Boundaries

Tactic Analysis currently reports demand and structure from explicit policy weights and
saved positions.

It does **not** include:

- Best XI, unique-player assignment or role-depth backups;
- Tactical Fit, Overall Suitability, Role Health, traits, form, morale or injury;
- recruitment recommendations or transfer targets;
- opposition-specific conclusions such as weakness against a low block;
- team-instruction style labels;
- persisted analysis snapshots or last-analysed dates;
- physical/work-rate profile counts (attribute categories are not on
  `AttributeDefinition` yet);
- comparison of two tactics.

Those concerns must be introduced explicitly in later increments. Later Tactical Fit or
recruitment work should consume `TacticAnalysis` rather than recalculating weights in a
second UI.
