# 010 — Position, attribute and role definitions

## Status

In Progress

## Objective

Create a validated, versioned tactical knowledge base that defines Football
Manager attributes, positions and roles independently from players, tactics and
the user interface. Combine those definitions with separate tactical modifiers
and scoring rules to provide deterministic, explainable inputs for the
role-centric squad assessment in requirement 007.

The knowledge base must distinguish four layers:

1. stable attribute and position vocabulary;
2. factual generic role definitions derived from Football Manager evidence;
3. FMSAT-owned role requirements, scoring policy and tactic-specific modifiers;
4. player assessments produced from the first three layers and player data.

Generic role definitions must not absorb tactical context, and generated player
assessments must not become canonical knowledge.

## Evidence-driven role acquisition

1. Treat Football Manager role-profile screenshots as primary evidence for
   role identity, supported position, abbreviation, factual description,
   behaviours, key attributes and explicit player instructions.
2. Accept the expected position and role observed by requirement 006 and verify
   that the submitted screenshot displays the same position and selected role.
3. Reject a screenshot detected as another screen type, a mismatched role or
   position, an unreadable role profile or evidence missing the information
   required to create a minimally valid definition.
4. Extract a reviewable draft while retaining observed text, component
   confidence, source import and Football Manager version where available.
5. Keep the displayed player's numeric attribute values and role-suitability
   stars as source evidence. They must not become role weights, minimums or
   target values.
6. Require user review and confirmation before creating or replacing any role
   definition YAML. Low-confidence and unknown values must remain visibly
   unresolved rather than being silently accepted.
7. Write confirmed definitions atomically to a user knowledge directory rather
   than modifying packaged bundled files at runtime. Load bundled and confirmed
   user definitions as one validated knowledge graph, rejecting conflicting
   stable identifiers.
8. Record definition provenance, source identity, review state and knowledge
   version without embedding the source screenshot or personal player data in
   the generated role YAML.
9. After a confirmed definition is loaded successfully, notify the structured
   tactic workflow so every matching missing-role issue can be revalidated.
10. Allow a confirmed user definition to be exported for later review and
    promotion into the bundled knowledge base without making that promotion an
    automatic runtime action.

## Knowledge-base layout

Store the bundled definitions in a hierarchy equivalent to:

```text
knowledge/
├── attributes.yaml
├── positions/
│   ├── dc.yaml
│   ├── dm.yaml
│   └── aml.yaml
├── roles/
│   ├── halfBack.yaml
│   ├── deepLyingPlaymaker.yaml
│   └── insideForward.yaml
├── requirements/
│   └── roles/
│       ├── halfBack.yaml
│       └── insideForward.yaml
├── tactics/
│   └── modifiers.yaml
└── calculations/
    └── scoring.yaml
```

The exact package location may follow the implemented FMSAT layout, but these
concerns must remain separate. Configuration must be loadable and testable
without Qt, SQLAlchemy or OCR.

## Attribute definitions

1. Provide one master `attributes.yaml` containing every supported outfield and
   goalkeeper attribute used by imported player data or role definitions.
2. Each attribute must have a stable camel-case identifier, Football Manager
   display name, display abbreviation and category such as technical, mental,
   physical or goalkeeping.
3. Identifiers are permanent interfaces. Changing a label or abbreviation must
   not invalidate historical assessments.
4. Attribute definitions describe identity and presentation only. They must not
   contain role-specific weights.
5. Reject duplicate identifiers and abbreviations, missing required fields and
   unsupported categories with actionable validation errors.
6. Every attribute referenced by a role, minimum, modifier or scoring rule must
   resolve to this master list.
7. Do not silently create an attribute for an unknown reference.

An illustrative definition is:

```yaml
attributes:
  crossing:
    id: crossing
    abbreviation: Cro
    displayName: Crossing
    category: technical
  pace:
    id: pace
    abbreviation: Pac
    displayName: Pace
    category: physical
```

## Position definitions

1. Define canonical positions separately from roles, with one definition per
   position or another equivalently maintainable split.
2. Each position must have a stable identifier compatible with requirement 006,
   display name, pitch area or horizontal channel, tactical line and explicit
   list of supported role identifiers.
3. Position definitions are the authority for which roles can be selected for a
   position. Roles must also declare their supported positions, and validation
   must require both directions to agree.
4. Cover all canonical positions supported by structured tactic extraction,
   including side-specific and central variants where meaningful to FMSAT.
5. Keep pitch coordinates and player position familiarity out of position
   definitions. Coordinates belong to tactic shape; familiarity belongs to
   imported player data.
6. Reject unknown roles, duplicate identifiers and inconsistent position-role
   mappings.

An illustrative definition is:

```yaml
id: DM
displayName: Defensive Midfielder
area: centre
line: defensiveMidfield
supports:
  - defensiveMidfielder
  - deepLyingPlaymaker
  - pressingDefensiveMidfielder
```

## Role definitions

1. Define each canonical role independently in a role file.
2. Each role must contain a stable identifier, display name, abbreviations,
   supported positions, supported duties, factual description, screenshot-backed
   key attributes, behaviours, explicit player instructions and provenance where
   those facts are available.
3. A screenshot-derived role definition must not contain the displayed player's
   attribute values, suitability stars, FMSAT weights or hard minimums.
4. Role definitions may be used to normalize and review a structured tactic
   before a corresponding assessment requirement exists. In that state, player
   scoring for the role must be reported as unavailable.
5. Make sure only roles defined within the supported Football Manager version
   are documented; do not retain roles from earlier versions merely to complete
   a historical list.

An illustrative factual definition is:

```yaml
id: advancedPlaymaker
displayName: Advanced Playmaker
abbreviations:
  - AP
positions:
  - MC
description: >-
  A creative role operating between the opposition midfield and defence.
behaviours:
  - findsSpaceBetweenLines
  - expressive
keyAttributes:
  - offTheBall
  - passing
  - vision
  - decisions
playerInstructions:
  - takeMoreRisks
```

## Role assessment requirements

1. Define FMSAT's assessment policy separately from factual role definitions,
   with one requirement profile per role or another equivalently maintainable
   split.
2. Each profile must reference a known role and define attribute weights,
   importance groups and optional hard minimums.
3. Attribute weights must use a documented integer scale, initially `0`–`5`,
   rather than percentages. A larger value means greater influence on Generic
   Role Fit.
4. Every weighted, grouped or minimum attribute must reference both the master
   attribute vocabulary and, unless explicitly justified, the role's
   screenshot-backed key attributes.
5. Every referenced role must resolve to the factual role vocabulary; a role
   definition may exist without a requirement profile, but a requirement profile
   must never invent a role.
6. Define whether weights and minimums apply to the whole role or vary by duty.
   Duty-specific overrides must be explicit and must not mutate the generic role
   definition at runtime.
7. Essential, important and useful groups drive explanations and presentation;
   they must not introduce hidden numeric weights unless `scoring.yaml` defines
   that relationship explicitly.
8. An attribute must not appear in more than one importance group for the same
   role and duty.
9. Minimums are hard suitability constraints. Failure must apply a documented
   score cap or penalty so unrelated strengths cannot produce an implausibly high
   score.
10. Evaluate position compatibility separately from attribute fit. Strong
    attributes must not make an unsupported position naturally suitable.
11. Optional preferred-foot and player-trait rules may be represented only when
    the corresponding source data and scoring behavior are explicitly supported;
    their absence must have no hidden effect.

An illustrative assessment requirement is:

```yaml
role: halfBack
attributes:
  positioning: 5
  anticipation: 5
  decisions: 5
  concentration: 4
  tackling: 5
  marking: 4
  teamwork: 4
  passing: 4
  firstTouch: 3
  composure: 4
  strength: 2
  pace: 2
essential:
  - positioning
  - anticipation
  - tackling
important:
  - passing
  - teamwork
useful:
  - pace
  - strength
minimums: {}
```

## Tactical modifiers

1. Store tactic-specific requirements separately from generic roles.
2. A modifier must identify its stable ID, the canonical tactic instruction and
   value that activates it, applicable positions, roles, duties or tactical
   units, attribute-weight adjustments and an explanation template.
3. Modifiers adjust requirements for one structured tactic; they must not rewrite
   role definitions.
4. Support additive adjustments such as higher tempo increasing pace,
   acceleration and decisions for a Half Back.
5. Define deterministic rules for combining modifiers, weight bounds, conflicts
   and ordering.
6. Apply a modifier only when the structured tactic contains its exact supporting
   instruction. Missing, unknown or unresolved instructions must not activate it.
7. Modifier targets must resolve to known positions, roles, duties and
   attributes.
8. Every applied modifier must remain visible in the assessment explanation.

An illustrative modifier is:

```yaml
- id: higherTempoHalfBack
  when:
    instruction: tempo
    value: higher
  appliesTo:
    roles:
      - halfBack
  adjustments:
    pace: 1
    acceleration: 1
    decisions: 1
```

A higher defensive line may similarly increase acceleration, pace and
positioning requirements for centre-back roles without changing their generic
role files.

## Scoring definitions

1. Put calculation policy in `calculations/scoring.yaml`, separate from domain
   definitions and executable scoring code.
2. Define the player-attribute scale, weight scale, normalization, rounding,
   missing-data behavior and output scale.
3. Define how Generic Role Fit, Tactical Fit and Position Familiarity contribute
   to Overall Suitability as required by requirement 007.
4. Define how minimum failures cap or penalize scores.
5. Define how imported position-familiarity states affect Position Familiarity.
6. A missing player attribute must be reported as unavailable or incomplete; it
   must not be silently treated as zero or average.
7. Scoring must be deterministic and independent of iteration order.
8. Retain a knowledge and scoring configuration version or content identity with
   every generated assessment so it remains reproducible after definitions
   change.

## Player assessment and explainability

1. The assessment service must accept a player attribute snapshot, position
   familiarity, role and duty, structured tactic and specific knowledge version.
2. Produce Generic Role Fit, Tactical Fit, Position Familiarity and Overall
   Suitability as separate values.
3. Produce a trace containing source values, base weights, tactical adjustments,
   minimum outcomes, missing inputs, component scores and final rounding.
4. Produce strengths and weaknesses from importance groups and player values
   using thresholds from scoring configuration.
5. Explain changes caused by tactical modifiers separately from the base role
   assessment.
6. Preserve enough detail to explain a score decreasing when higher tempo or a
   high defensive line increases requirements.
7. Never infer preferred foot, traits, positions, attributes or tactic
   instructions that were not imported or explicitly entered.
8. UI behavior, candidate ranking, comparisons and Role Health remain owned by
   requirement 007.

## Training recommendation inputs

1. Expose deficient essential and important attributes as structured output that
   later training workflows can consume.
2. Keep each need traceable to role, duty, tactic modifiers, player snapshot and
   configuration version.
3. Do not prescribe a training schedule or claim a development outcome in this
   requirement.

## Validation and loading

1. Provide typed domain objects and a single knowledge-base loader outside the
   UI layer.
2. Validate the complete knowledge graph at startup or first use and fail safely
   with file, field and reference details.
3. Validate YAML structure, identifiers, enumerations, numeric ranges,
   cross-references, bidirectional mappings and modifier targets.
4. Load one internally consistent knowledge version atomically; do not leave the
   application partly using invalid new configuration.
5. Provide a diagnostic command that validates the bundled knowledge base and
   reports its version or content identity.
6. Log loading, version identity and validation failures without logging personal
   player data.
7. Validate screenshot-derived drafts with the same schema and cross-reference
   rules used for bundled definitions before writing or loading them.

## Acceptance criteria

1. One master attribute file defines every referenced attribute using stable
   identifiers, names, abbreviations and categories.
2. Every position has a validated definition with explicit supported roles, and
   every role-position relationship agrees in both directions.
3. Every role has a validated factual definition containing positions, duties,
   description and screenshot-backed key attributes where available.
4. Every assessment-enabled role has a separate validated requirement profile
   containing integer weights and importance groups.
5. Unknown references, duplicates, invalid weights and inconsistent mappings
   produce actionable errors rather than partial or invented definitions.
6. Generic role weights remain unchanged when tactical modifiers are applied.
7. Only explicit structured tactic instructions activate modifiers.
8. Minimum rules prevent unrelated strengths from producing an implausibly high
   role score.
9. Assessments expose separate Generic Role Fit, Tactical Fit, Position
   Familiarity and Overall Suitability values with a reproducible trace.
10. Missing source data is explicit and never silently substituted.
11. Strengths, weaknesses and future training inputs are derived from configured
   definitions and remain explainable.
12. Assessments retain the knowledge and scoring configuration identity used to
   produce them.
13. A non-UI diagnostic command validates the complete bundled knowledge base.
14. Automated tests cover loading, schema validation, cross-references, weights,
   importance groups, minimums, position compatibility, modifier activation and
   composition, missing data, deterministic scoring and explanation traces.
15. Existing tactic extraction and role-centric assessment workflows remain
   compatible.
16. Ruff, Black and the complete applicable automated test suite pass.
17. A verified role-profile screenshot can create a confirmed factual user role YAML,
    while mismatched or incomplete evidence cannot alter the active knowledge
    graph.
18. Displayed player ratings and suitability stars remain provenance evidence
    and never appear as generated attribute weights or minimums.
19. A role without an assessment requirement can be used by the tactic parser
    but produces an explicit unavailable assessment rather than an invented score.

## UI Considerations

1. Show the expected and detected role and position side by side during role
   evidence review.
2. Allow extracted factual fields to be corrected before confirmation, with the
   original observed text and confidence still available.
3. Preview the role definition that will be created and clearly separate
   screenshot-derived facts from FMSAT weighting policy.
4. Provide confirm, replace-screenshot and cancel actions. Cancellation must
   leave the current knowledge graph unchanged.

## Out of scope

- Arbitrary editing of existing knowledge definitions through a general-purpose
  YAML or knowledge editor. Reviewing and correcting a screenshot-derived draft
  before confirmation is in scope.
- Automatically discovering weights from player or match data.
- Claiming that configurable weights reproduce Football Manager's private game
  engine calculations.
- Preferred foot, traits or position familiarity absent from source player data.
- Full training-plan generation or development forecasting.
- Recruitment recommendations, lineup selection or Role Health UI.
- Match-result ingestion and automatic optimization of weights or modifiers.

## Delivery notes

- Establish definitions and validation before implementing scoring consumers.
- Seed only definitions supported by the agreed Football Manager version and
  document their source and review status.
- Treat weights and modifiers as FMSAT's transparent assessment policy, not as
  hidden facts imported from Football Manager.
- Keep identifiers stable and version definition changes so historical results
  remain reproducible.
