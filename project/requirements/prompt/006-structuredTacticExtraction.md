# Implementation prompt — Requirement 006

## Project

Football Manager Squad Assessment Tool — FMSAT

- Repository: `Glawster/myHandbook`
- Base branch: `fmsat/phase2`
- New branch: `fmsat/phase3-structured-tactics`
- Working directory: `fmsat/`

## Objective

Extend Phase 2 so Formation, In Possession and Out of Possession screenshots are
converted into typed, editable and persistent tactical data. Do not calculate
player suitability, squad depth, recruitment needs or tactical advice. Later
analysis must consume the trustworthy structured tactic delivered here.

## Inspect before changing code

Read the current branch and inspect at minimum:

- `fmsat/README.md`
- `fmsat/app/`
- `fmsat/core/config.py`
- `fmsat/core/detection.py`
- `fmsat/core/services.py`
- `fmsat/core/parser/tactic.py`
- `fmsat/core/parser/squadAttributes.py`
- `fmsat/database/models.py`
- `fmsat/database/database.py`
- `fmsat/config/`
- `fmsat/tests/`
- `pyproject.toml`
- `fmsatEnvironment.yml`

Preserve camelCase project-owned Python names, dependency injection,
configuration-driven parsing, replaceable OCR, normalized coordinates,
SQLAlchemy/SQLite, rotating logging, mocked OCR tests and the existing UI and
database workflow. Extend the current architecture; do not create a parallel
application.

## Delivery boundary

Input is a stored tactic with Formation, In Possession and Out of Possession
captures. Output is a validated structured tactic that can be reviewed,
corrected, saved as a draft, confirmed and loaded by future analysis engines.

Implement requirement
[`006-structuredTacticExtraction.md`](../features/006-structuredTacticExtraction.md)
in full, including:

1. typed tactical domain models separate from Qt and SQLAlchemy;
2. YAML-driven positions, roles, duties, team instructions and parsing regions;
3. focused formation-tile detection and OCR with normalized pitch coordinates;
4. configurable pitch-zone classification;
5. best-effort, issue-producing cross-phase slot linking;
6. card-based In Possession and Out of Possession instruction extraction;
7. independent validation with error, warning and information severity;
8. backward-compatible SQLAlchemy persistence and safe schema upgrades;
9. extraction, validation and repository services shared by UI and CLI;
10. a structured tactic review and correction workflow;
11. draft and confirmation behavior;
12. diagnostic extract, show and validate CLI operations where practical;
13. component-level confidence and useful stage logging; and
14. updated user and architecture documentation.

## Domain guidance

Suggested core package:

```text
fmsat/core/tactics/
    __init__.py
    models.py
    normalisation.py
    validation.py
```

Use typed models equivalent to `TacticalPhase`, `FormationSlot`,
`TeamInstruction`, `StructuredTactic` and `ExtractionIssue`. Stable slot IDs are
local to one structured tactic. Store coordinates normalized to zero through
one, never only screen pixels. Preserve original OCR text where it explains a
normalization or correction.

Suggested configuration:

```text
fmsat/config/positions.yaml
fmsat/config/roles.yaml
fmsat/config/teamInstructions.yaml
fmsat/config/tacticRegions.yaml
```

Role definitions must contain code, display name, abbreviations, allowed
positions and supported duties. Use observed FM26 names and abbreviations; do
not invent tactical semantics or attribute weights.

## Parsing guidance

Refactor the existing `TacticParser` carefully so tactic-name extraction remains
compatible. Add screen-specific parsers that share focused OCR and computer
vision components. Detect role tiles before OCR instead of interpreting one
unrestricted whole-pitch text stream.

Classify normalized tile centres using configurable pitch zones capable of left,
right, central and half-space variants at each depth. Link slots across phases
by displayed player, shirt number, relative order and then spatial proximity.
When evidence is insufficient, retain separate phase slots and emit an issue.

Parse instruction cards by configured category region. Normalize selected
values through aliases, preserve observed text and confidence, and create issues
for missing, ambiguous or unknown values. Never default to values from the
sample tactic.

## Persistence and review

Keep historical imports. One tactic has one current structured definition, and
re-importing one phase must not erase other phases. Persist manual corrections,
source imports, issues and draft/confirmed state. Existing Phase 2 databases
must open without destructive recreation.

Enable **Review Structured Tactic** only when all required captures exist. Show
phase pitches, instructions and issues. Populate canonical edits from
configuration-controlled choices. Allow incomplete drafts; block confirmation
only for serious unresolved errors and require acknowledgement where warnings
are permitted.

Use requirement 005's six-band row palette and abbreviation role icon in player
and formation views when available. Keep the assigned tactical role separate
from each player's imported natural position.

## Tests

Do not require live OCR downloads. Use mocked OCR, small controlled crops or
synthetic fixtures. Cover:

- vocabulary aliases, normalization and unknown values;
- pitch-zone centres and boundaries;
- tile crops, multiple slots, names, roles, confidence and malformed geometry;
- every supported instruction category and value state;
- exact, shirt-number, spatial and uncertain phase links;
- new and Phase 2 databases, phase replacement, history, corrections and state;
- completed and incomplete review entry, edits, draft saves and confirmation
  blocking; and
- shared application-service and CLI behavior.

## Documentation

Update `fmsat/README.md` and `fmsat/documentation/architecture.md`. Document the
workflow, structured model, configuration, supported vocabulary, corrections,
confirmation, schema upgrade, diagnostics, limitations and future analysis
boundary.

## Definition of done

Do not claim completion until all requirement 006 acceptance criteria are met,
existing Phase 2 behavior remains compatible, no tests depend on uncommitted
local screenshots, and these checks pass:

```bash
pytest
ruff check fmsat
black --check fmsat
```

Work incrementally in this order unless the inspected architecture justifies a
documented adjustment: vocabulary and models; normalization and validation;
persistence; formation and instruction extraction; services; diagnostics;
review UI; tests and fixtures; documentation.

## Explicit non-goals

Do not implement player-role scores, best-position advice, squad-depth ranking,
recruitment recommendations, transfer filters, match analysis, PDF reports,
Football Manager UI automation, save-file reading or game modification.
