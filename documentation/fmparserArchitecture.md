# FMParser Core Architecture

FMParser is an external Football Manager analysis tool. It should analyse exported data and answer football questions about role fit, squad depth, recruitment, development and training.

It is not a save-game editor. The stable interface is a manually exported Football Manager view named `FMParser Core`.

## Design Principles

- Treat Football Manager exports as input data, not as the domain model.
- Keep football concepts independent from FM internals where possible.
- Make role definitions data-driven so new roles can be added without code changes.
- Keep import, domain modelling, analysis and reporting separate.
- Prefer pure functions for scoring and analysis so they are easy to test.
- Preserve raw imported values for auditability, but expose typed domain objects to analysis code.
- Make uncertainty explicit. Missing attributes, unknown positions and invalid rows should become validation results, not silent assumptions.

## Proposed Package Shape

```text
fmparser/
    importer/
        __init__.py
        squad_export.py
        schema.py
        validation.py

    models/
        __init__.py
        attributes.py
        player.py
        squad.py
        positions.py
        roles.py

    analysis/
        __init__.py
        roles/
            __init__.py
            engine.py
            result.py
        recruitment/
            __init__.py
            squad_gaps.py
        training/
            __init__.py
            recommendations.py
        development/
            __init__.py
            retraining.py

    reports/
        __init__.py
        markdown.py
        html.py

    cli.py
    __main__.py

    config/
        roles/
            half_back.yaml
            ball_playing_defender.yaml
```

The existing FMF binary inspection code can remain as a separate capability. If both tools continue to share the package, name boundaries should be clear:

- `fmparser.fmf` for tactic-file inspection and reverse engineering.
- `fmparser.importer`, `fmparser.models`, `fmparser.analysis` for exported squad analysis.

## Data Flow

```text
FMParser Core export
        |
        v
Importer
        |
        v
Validated rows + import diagnostics
        |
        v
Domain model: Squad, Player, attributes, positions
        |
        v
Analysis services: role fit, depth, retraining, training, recruitment
        |
        v
Reports: markdown, HTML, future PDF
```

The importer should be the only layer that knows about exact column names in the exported view. Analysis code should work with domain objects.

## Import Contract

The initial stable export is `FMParser Core`, one row per player.

Required columns:

```text
Player
Age
Position
CA
Crossing
Dribbling
Finishing
First Touch
Heading
Marking
Passing
Tackling
Technique
Acceleration
Agility
Balance
Jumping Reach
Natural Fitness
Pace
Stamina
Strength
Aggression
Anticipation
Bravery
Composure
Concentration
Decisions
Determination
Flair
Leadership
Off The Ball
Positioning
Teamwork
Vision
Work Rate
```

Section labels such as `Identity`, `Technical`, `Physical` and `Mental` are useful in FM view design but should not be required as data fields unless the exported format actually includes them as columns.

Importer responsibilities:

- Detect CSV, TSV or HTML table exports if needed.
- Normalize column names into internal attribute keys.
- Validate required columns.
- Parse integer fields.
- Keep raw row data for traceability.
- Return both a `Squad` and an `ImportReport`.

Example importer API:

```python
result = import_squad_export(path)

squad = result.squad
diagnostics = result.diagnostics
```

## Core Domain Model

### Player

Represents a footballer in the squad export.

```python
@dataclass(frozen=True)
class Player:
    id: PlayerId | None
    name: str
    age: int
    positions: tuple[Position, ...]
    current_ability: int | None
    attributes: AttributeSet
    raw: Mapping[str, str]
```

The player should not contain scoring rules. It is a data object used by analysis services.

### AttributeSet

Represents named attributes and their numeric values.

```python
@dataclass(frozen=True)
class AttributeSet:
    values: Mapping[AttributeKey, int]

    def get(self, key: AttributeKey) -> int | None:
        ...
```

Use canonical snake-case keys internally:

```text
first_touch
jumping_reach
natural_fitness
off_the_ball
work_rate
```

Column display names should live in the importer schema, not throughout the codebase.

### Position

Positions should support both broad tactical areas and FM-style detailed positions.

```python
@dataclass(frozen=True)
class Position:
    code: str
    line: PositionLine
    side: PositionSide | None = None
```

Examples:

```text
GK
DC
DR
DL
DM
MC
AMR
AML
ST
```

The first version can parse positions conservatively from the exported `Position` string. Later versions can add richer natural-position and accomplished-position modelling if that data is exported.

### Squad

Represents a collection of players plus optional metadata about the export.

```python
@dataclass(frozen=True)
class Squad:
    players: tuple[Player, ...]
    source: SquadSource
```

Squad methods should stay query-like and simple:

```python
squad.by_position("DM")
squad.under_age(21)
squad.with_min_attribute("passing", 14)
```

Heavier football reasoning belongs in `analysis/`.

## Role Model

A role is a tactical question expressed as configuration.

```python
@dataclass(frozen=True)
class RoleDefinition:
    key: str
    name: str
    description: str
    position_groups: tuple[str, ...]
    attributes: tuple[WeightedAttribute, ...]
    constraints: tuple[RoleConstraint, ...] = ()
    score: ScoreConfig = ScoreConfig()
```

```python
@dataclass(frozen=True)
class WeightedAttribute:
    key: AttributeKey
    weight: float
```

The role engine should not know about Half Back, Ball Playing Defender or any future role by name. It should load definitions and evaluate them generically.

## Role Configuration

Role definitions should be stored in YAML or JSON. YAML is more readable for football tuning.

Example:

```yaml
key: half_back
name: Half Back
position_groups:
  - DM
description: Screens defence, drops into the back line, recycles possession and protects central spaces.

attributes:
  positioning: 0.25
  passing: 0.20
  decisions: 0.20
  vision: 0.15
  anticipation: 0.10
  work_rate: 0.10

constraints:
  - type: position_match
    preferred:
      - DM
      - DC
```

Validation rules:

- Role keys must be unique.
- Attribute weights must sum to `1.0` after parsing.
- Attribute keys must exist in the known attribute registry.
- Constraint types must be known.
- Missing descriptions are allowed, but missing names are not.

## Role Suitability Engine

Input:

- `Squad`
- `RoleDefinition`
- Optional scoring options

Output:

- Ranked `RoleSuitabilityResult` values.

```python
@dataclass(frozen=True)
class RoleSuitabilityResult:
    player: Player
    role: RoleDefinition
    score: float
    attribute_score: float
    position_score: float
    strengths: tuple[AttributeContribution, ...]
    weaknesses: tuple[AttributeContribution, ...]
    missing_attributes: tuple[AttributeKey, ...]
```

Suggested scoring:

```text
attribute_score = sum((attribute_value / 20) * weight for each weighted attribute)
position_score = 1.0 for natural match, 0.85 for adjacent match, 0.65 for retraining candidate, 0.30 for poor fit
final_score = 100 * attribute_score * position_score
```

The first version can keep position scoring simple. Later versions can support role-specific positional tolerance, retraining likelihood and tactical-system context.

The engine should expose explainable output. A user should see why a player ranked highly or poorly, not just the final score.

## Analysis Modules

### Role Suitability

Answers:

- Which player best suits Half Back?
- Who are the top alternatives?
- Which attributes explain the ranking?
- Which players are good retraining candidates?

Core services:

```python
rank_players_for_role(squad, role)
rank_roles_for_player(player, roles)
compare_players_for_role(players, role)
```

### Squad Depth

Answers:

- Which positions lack depth?
- Where is the second-choice option weak?
- Where is there a high age or low-CA risk?

Inputs should be configurable:

```yaml
depth_requirements:
  DM:
    minimum_players: 2
    roles:
      - half_back
      - defensive_midfielder
  DC:
    minimum_players: 4
    roles:
      - central_defender
      - ball_playing_defender
```

### Recruitment

Answers:

- Which role profiles are missing?
- Which attribute combinations are below squad standard?
- What type of player should be targeted?

Recruitment should consume squad-depth and role-suitability results rather than duplicate their logic.

### Training

Answers:

- Which attributes should be trained for a role?
- Which player has one or two fixable weaknesses?
- Which weaknesses are squad-wide patterns?

Training recommendations should use role deficits:

```text
deficit = target_attribute_level - player_attribute_value
priority = deficit * role_weight * development_context
```

Development context can initially be age-based:

- Under 21: high development upside.
- 21-24: normal development upside.
- 25+: lower attribute-growth expectation.

## Report Layer

Reports should be presentation-only. They should receive already computed analysis results and render them.

Initial report formats:

- Markdown for handbook-friendly output.
- HTML for richer local reports.

Future formats:

- PDF generated from HTML.
- LibreOffice-friendly markdown or document fragments for handbook workflows.

## CLI Boundary

The CLI should orchestrate workflows, not contain football logic.

Example commands:

```text
fmparser squad import squad.csv
fmparser squad roles squad.csv --role half_back
fmparser squad report squad.csv --format markdown
```

The tactic-file workflow should be flag-led so common commands read naturally:

```text
fmparser --tactic tactic.fmf --inspect
fmparser --tactic tactic.fmf --print
fmparser --tactic old.fmf --compare new.fmf
fmparser --tactic tactic.fmf --save
fmparser --inspect
fmparser squad roles squad.csv --role half_back
```

When `--tactic` is omitted, FMParser should use the tactic path stored in
`~/.config/fmparser/config.json`.

## Testing Strategy

Importer tests:

- Accept a minimal valid `FMParser Core` export.
- Reject missing required columns.
- Report invalid numeric values with row and column context.
- Preserve raw row data.

Model tests:

- Parse position strings consistently.
- Normalize attributes into canonical keys.
- Handle missing current ability.

Role engine tests:

- Load valid role configuration.
- Reject invalid weights.
- Reject unknown attributes.
- Rank players by weighted score.
- Apply position suitability modifiers.
- Return strengths, weaknesses and missing attributes.

Analysis tests:

- Detect shallow depth for a configured position.
- Recommend training from role deficits.
- Identify retraining candidates from adjacent positions.

## Versioning The Export Contract

Add an explicit schema version internally even if the FM view name stays stable:

```python
FMParserCoreSchema(version="1.0")
```

Future export views can be added as new schemas:

```text
FMParser Core v1
FMParser Training v1
FMParser Recruitment v1
FMParser Match Analysis v1
```

Each importer schema should define:

- Required columns.
- Optional columns.
- Column aliases.
- Type parsers.
- Domain mapping.

## First Implementation Slice

The first useful non-UI milestone should be:

1. Import `FMParser Core` squad export.
2. Build `Player`, `Squad`, `AttributeSet` and `Position`.
3. Load role definitions from configuration.
4. Score all players for one role.
5. Produce a markdown role-suitability report.
6. Cover importer and role scoring with tests.

That creates the core loop of the tool: exported data in, football question out.
