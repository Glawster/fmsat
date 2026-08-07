# Source prompt — requirement 010

Create a requirement covering position, attribute and role definitions as a
validated, versioned tactical knowledge base. Keep this knowledge independent
from players, individual tactics, persistence and UI code, while providing a UI
screen where the configured values can be viewed and adjusted.

The knowledge base should have four distinct layers:

1. stable attribute and position vocabulary;
2. generic role definitions;
3. tactic-specific modifiers; and
4. player assessments produced from those definitions, the selected tactic and
   imported player data.

Generic role definitions must not absorb tactical context. Generated player
assessments must not become canonical definitions.

Organize the knowledge base along these lines:

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
├── tactics/
│   └── modifiers.yaml
└── calculations/
    └── scoring.yaml
```

## Attribute definitions

Create one master `attributes.yaml` containing all supported outfield and
goalkeeper attributes. Each attribute needs a permanent camel-case identifier,
Football Manager display name, display abbreviation and category such as
technical, mental, physical or goalkeeping.

Attribute identity must remain stable even if labels change. Attribute
definitions must not contain role-specific weights. Duplicate, incomplete or
unknown attributes must produce validation errors rather than being silently
created.

For example:

```yaml
attributes:
  crossing:
    id: crossing
    abbreviation: Cro
    displayName: Crossing
    category: technical
  dribbling:
    id: dribbling
    abbreviation: Dri
    displayName: Dribbling
    category: technical
  pace:
    id: pace
    abbreviation: Pac
    displayName: Pace
    category: physical
```

## Position definitions

Define positions independently from roles. Each position needs a stable
identifier compatible with structured tactic extraction, a display name, pitch
area, tactical line and explicit list of supported role identifiers.

Position and role definitions must reference one another consistently. Cover
the canonical central and side-specific positions supported by FMSAT. Keep
tactic coordinates and individual player familiarity outside these definitions.

For example:

```yaml
id: DM
displayName: Defensive Midfielder
area: centre
line: defensiveMidfield
supports:
  - halfBack
  - deepLyingPlaymaker
  - ballWinningMidfielder
  - segundoVolante
```

Only define roles that exist in Football Manager 2026. Do not introduce roles
from older editions or invented aliases; for example, do not add Anchor if it is
not an FM26-defined role.

## Role definitions

Give every canonical role its own definition containing:

- a stable identifier;
- display name and supported abbreviations;
- supported positions and duties;
- a factual description;
- integer attribute weights;
- essential, important and useful attribute groups; and
- optional hard minimums.

Use a documented integer weight scale, initially `0`–`5`, rather than
percentages. Allow explicit duty-specific overrides without modifying the base
role at runtime. Every referenced attribute must exist in the master attribute
list, and one attribute must not occupy multiple importance groups for the same
role and duty.

For example:

```yaml
id: halfBack
displayName: Half Back
abbreviations:
  - HB
positions:
  - DM
duties:
  - DEFEND
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

Minimums are hard suitability rules. A player must not score highly as a Target
Man when required attributes such as Heading, Jumping Reach or Strength are
below configured thresholds. Scoring configuration must define the resulting
cap or penalty. Position compatibility must be scored separately so excellent
attributes do not make an unsupported position naturally suitable.

Preferred foot and player traits may be supported later, but only when source
data and explicit scoring behavior exist. Missing information must never have a
hidden effect.

## Tactical modifiers

Keep tactical requirements separate from generic role files. A modifier must
identify the exact structured tactic instruction and value that activates it,
its applicable positions, roles, duties or units, attribute-weight adjustments
and an explanation.

For example, higher tempo may add weight to Pace, Acceleration and Decisions for
a Half Back. A higher defensive line may add weight to Acceleration, Pace and
Positioning for centre-back roles. These adjustments must not rewrite the
generic role.

Define deterministic behavior for combining modifiers, bounding weights,
resolving conflicts and ordering adjustments. Missing, unknown or unresolved
tactic instructions must not activate modifiers. Every applied modifier must be
visible in the assessment explanation.

## Scoring and assessment

Keep calculation policy in `calculations/scoring.yaml`. Define attribute and
weight scales, normalization, rounding, missing-data behavior, output scale,
minimum penalties and position-familiarity effects.

For a specific player, role, duty and tactic, produce separate:

- Generic Role Fit;
- Tactical Fit;
- Position Familiarity; and
- Overall Suitability.

The assessment must be deterministic and produce a reproducible trace containing
source attributes, base weights, tactical adjustments, minimum outcomes,
missing inputs, component scores and final rounding. Missing attributes must be
reported as incomplete rather than silently treated as zero or average.

Use essential, important and useful groups with configured thresholds to explain
strengths and weaknesses. Explain the effect of tactic modifiers separately from
generic role fit. Retain the knowledge-base and scoring-configuration identity
with every generated assessment so historical results remain reproducible.

Expose deficient essential and important attributes as structured inputs for
later training recommendations, but do not prescribe training schedules or
claim development outcomes here.

Candidate ranking, comparisons, Role Health and the wider role-assessment UI
remain covered by requirement 007.

## Validation and interface

Provide typed domain objects and one non-UI loader. Validate YAML structure,
identifiers, enumerations, numeric ranges, cross-references, bidirectional
position-role mappings and modifier targets. Load a complete internally
consistent knowledge version atomically rather than partially accepting invalid
configuration.

Add a diagnostic command that validates the bundled knowledge base and reports
its version or content identity. Log loading and validation failures without
logging personal player data.

Provide a UI screen where attribute, position, role, modifier and scoring values
can be inspected and adjusted. Changes must pass the same validation rules and
must create a traceable configuration version rather than silently changing the
meaning of historical assessments.

Automated tests must cover loading, validation, references, weights, importance
groups, minimums, position compatibility, modifier activation and composition,
missing data, deterministic scoring and explanation traces.
