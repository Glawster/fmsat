# 009 — Tactic detail management

## Status

Backlog

## Objective

Provide a dedicated tactic screen that presents a stored tactic as structured,
usable data rather than as a collection of screenshots. The screen must let the
user inspect the tactic's overview, phase-specific shape, team instructions and
future generated analysis while preserving the screenshots as evidence of the
import rather than the tactic's primary representation.

This requirement consumes the structured extraction defined by requirement 006
and complements the tactic-list workflow delivered by requirement 003.

## Navigation and layout

1. Opening a tactic from the welcome screen or tactic list must open its
   dedicated tactic screen.
2. Show the tactic's saved name prominently.
3. Provide four tabs in this order: **Overview**, **Shape**, **Instructions**
   and **Analysis**.
4. Preserve the selected tactic and refresh the screen when its current revision
   changes.
5. Reuse application services and repositories; widgets must not perform OCR or
   direct persistence work.
6. Missing optional values must have clear neutral placeholders and must not
   prevent the rest of the tactic being displayed.

## Overview tab

Show a concise landing page for the selected tactic. Where captured or otherwise
stored explicitly, display:

- name;
- created date;
- last-updated date;
- formation;
- mentality;
- status;
- last-analysed date;
- notes;
- current version; and
- the number and names of assigned squads.

Display a clean vector-style pitch reconstructed from the current structured
formation. Do not display a Formation screenshot as the main diagram. The pitch
must use stored slot coordinates, positions, roles and duties and remain useful
when no player is assigned.

Provide a compact summary derived only from explicit tactic data, such as
mentality and enabled or selected instructions. Do not present inferred tactical
labels as imported facts.

## Shape tab

1. Present separate **In Possession** and **Out of Possession** formations.
2. Draw both formations on clean vector-style pitches from structured data.
3. For every visible slot, retain and display as appropriate:
   - stable slot identity;
   - normalized pitch coordinates;
   - canonical position;
   - role;
   - duty; and
   - optional assigned player.
4. A position may differ between phases; do not force the In Possession and Out
   of Possession codes or coordinates to match.
5. Use the canonical roles, duties and position vocabulary established by
   requirement 006.
6. Do not infer a missing role, duty, position, coordinate or player assignment.
7. Keep the stored representation suitable for redrawing formations, comparing
   revisions, analysing spacing and later calculating role suitability without
   reopening screenshots.

An illustrative slot representation is:

```yaml
ipFormation:
  AML:
    role: IF
    duty: ATTACK
    x: 0.18
    y: 0.34
    assignedPlayer: null
```

Coordinates must follow the normalized convention from requirement 006 rather
than introducing a second coordinate scale.

## Instructions tab

Capture and display every visible team instruction individually using meaningful
canonical names and explicit values. Do not use positional flags such as
`instruction7: true`, and do not add an instruction that was not visible in the
source evidence.

Organize instructions into these user-facing groups:

### Build Up

- Passing Directness
- Tempo
- Patience
- Goal Kicks
- Goalkeeper Distribution

### Attack

- Attacking Width
- Creative Freedom
- Dribbling
- Supporting Runs
- Crossing
- Shots
- Set Pieces

### Transition

- Counter
- Counter Press
- Distribution Speed

### Defence

- Line of Engagement
- Defensive Line
- Trigger Press
- Pressing Trap
- Tackling
- Cross Engagement
- Defensive Behaviour
- Short Distribution

1. Store each instruction under a stable canonical key with a typed canonical
   value and a display value where useful.
2. Boolean instructions must distinguish `true`, `false` and not captured.
3. Enumerated instructions must use the configured vocabulary and retain unknown
   or unresolved values explicitly.
4. Preserve the instruction's tactical phase, category and source evidence as
   defined by requirement 006.
5. The interface may show a balanced, standard or off value only when that value
   was visible or is explicitly represented by Football Manager; absence is not
   a default.

An illustrative representation is:

```yaml
instructions:
  passingDirectness: standard
  tempo: higher
  attackingWidth: narrow
  counterAttack: true
  counterPress: true
```

## Analysis tab

1. Provide an Analysis tab even when no analysis has yet been generated.
2. Show a useful empty state that explains analysis is generated rather than
   imported.
3. Keep imported and user-entered facts visually and structurally distinct from
   generated analysis.
4. The later analysis model may contain system summaries, style labels,
   aggression, risk, player-role needs and role suitability, but this requirement
   does not define the algorithms or scores that produce them.
5. Never present generated labels such as High Press, Narrow Build or Counter
   Attack as source-captured facts unless the source explicitly displayed them.

## Squad assignment

1. Model squad use as a relationship from tactic revision to assigned squad and
   then to optional player-slot mappings.
2. Squad assignment must use existing stored squads and explicit user actions;
   it must not be determined by OCR.
3. Show assigned squads on the Overview tab and provide a route to the existing
   assignment workflow where available.
4. A player mapping must identify the formation slot or stable cross-phase slot
   it applies to.
5. Updating a squad assignment must not alter the tactic's imported formation or
   instructions.

## Screenshot provenance

1. Retain screenshots and their import records as evidence for extracted values.
2. The structured tactic model is the primary representation used by the tactic
   screen.
3. Every extracted formation slot and instruction must remain traceable to its
   source import where requirement 006 provides that provenance.
4. Replacing or superseding a structured phase must not silently delete its
   historical screenshot evidence.
5. Do not require image OCR merely to open or redraw an already structured
   tactic.

## Version history

1. Give every tactic an immutable sequence of revisions.
2. The first structured import creates the initial revision.
3. Importing a modified version of an existing tactic must create a new revision
   rather than overwrite an earlier revision.
4. Unchanged re-imports must not create duplicate revisions.
5. Each revision must retain its creation time, optional note, source imports,
   structured formations, instructions, metadata and squad assignments as
   applicable at that revision.
6. Identify one revision as current without deleting prior revisions.
7. Allow the user to inspect the revision list and select an earlier revision in
   read-only form.
8. Produce a structured comparison between any two revisions that can identify
   metadata, slot, role, duty, coordinate and instruction changes.
9. Use factual change descriptions such as “AML changed from IF (Attack) to W
   (Support)” rather than generated tactical conclusions.
10. Do not claim that one revision performed better until match-result evidence
    and a separate analysis requirement support that conclusion.

## Persistence and compatibility

1. Extend the existing tactic and structured-tactic persistence model rather
   than creating a parallel source of truth.
2. Store typed metadata, phase formations, instructions, revision identity and
   source links.
3. Preserve existing tactics that have screenshots but no confirmed structured
   extraction; show an incomplete-data state and a route to review or extract
   where supported.
4. Upgrade existing databases without deleting or recreating user data.
5. Keep historical revisions and screenshot imports intact when the current
   revision changes.
6. Preserve all existing tactic list, welcome screen, import, squad and CLI
   workflows.

## Acceptance criteria

1. Opening a stored tactic displays Overview, Shape, Instructions and Analysis
   tabs for that tactic.
2. Overview displays stored metadata, assigned-squad information and a vector
   formation reconstructed without showing the source screenshot as the tactic.
3. Shape displays distinct In Possession and Out of Possession pitches using
   stored coordinates, positions, roles, duties and optional players.
4. Instructions displays every captured instruction under a meaningful canonical
   name and the correct Build Up, Attack, Transition or Defence group.
5. Missing and unresolved values remain explicit and are never filled by
   inference or sample defaults.
6. Opening or switching tabs performs no OCR.
7. The Analysis tab has a useful empty state and does not misrepresent generated
   conclusions as imported data.
8. Assigned squads and player mappings are persisted independently of OCR.
9. A changed import creates a new immutable revision, while an unchanged import
   does not create a duplicate revision.
10. Earlier revisions remain inspectable and two revisions can be compared using
    structured factual changes.
11. Existing tactics without structured data remain accessible with a safe
    incomplete-data state.
12. Automated tests cover populated, partial and missing data; both formation
    phases; instruction grouping; squad assignment; revision creation and
    deduplication; revision comparison; and database migration.
13. Ruff, Black and the complete applicable automated test suite pass.

## Out of scope

- Defining or implementing tactical-analysis algorithms or role-suitability
  scores.
- Inferring any tactic value that is not visible in source evidence or explicitly
  entered by the user.
- Match-result ingestion or claims about which revision performs best.
- Set-piece routine detail, opposition instructions or individual player
  instructions beyond reserving them for later requirements.
- Football Manager automation or using screenshots as the runtime tactic model.

## Delivery notes

- Implement after or alongside the structured data supplied by requirement 006.
- Reuse the formation visual components from requirement 005 where suitable.
- Keep pitch rendering independent of screenshots and OCR.
- Treat version comparison as a comparison of typed domain objects, not images.
