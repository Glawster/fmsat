# 009 — Tactic detail management

## Status

In Progress

## Objective

Provide a dedicated tactic screen that presents the persisted football object
model rather than a collection of screenshots. The screen must let the user
inspect the tactic's overview, phase-specific shape, team instructions and
future generated analysis while preserving screenshots as source evidence and
the screenshot-derived definition as the intermediate extraction layer.

This requirement consumes the structured extraction defined by requirement 006
and complements the tactic-list workflow delivered by requirement 003.

## Data flow and authority

The tactic workflow has four distinct layers:

1. screenshot imports are immutable source evidence;
2. `ScreenshotDerivedTacticDefinition` records the current extracted values,
   confidence, review state, issues and source provenance;
3. the football object model is generated from the screenshot-derived
   definition and is the primary representation used by the tactic screen; and
4. UI models adapt the football object model for display without becoming a
   source of tactical data.

Re-importing a screenshot must not silently alter the existing football object
model. It makes the screenshot-derived data and object model older than the
latest evidence until the user regenerates the model. The existing model remains
viewable, but the UI must identify it as requiring regeneration.

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
- evidence-updated date;
- model-generated date;
- formation;
- mentality;
- status;
- last-analysed date;
- notes;
- current version; and
- the number and names of assigned squads.

Display a clean vector-style pitch reconstructed from the current football
object model. Do not display a Formation screenshot as the main diagram. The
pitch must use the model's slot coordinates, positions, roles, duties and
instructions and remain useful when no player is assigned.

Show whether the model is current relative to its screenshot evidence. At
minimum distinguish **Current**, **Regeneration required**, **Processing
required**, **Incomplete evidence** and **Review required**. When regeneration
is required, show both the latest evidence date and the model generation date.

Provide a compact summary derived only from explicit tactic data, such as
mentality and enabled or selected instructions. Do not present inferred tactical
labels as imported facts.

## Shape tab

1. Present separate **In Possession** and **Out of Possession** formations.
2. Draw both formations on clean vector-style pitches from the football object
   model.
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
7. Keep the football object model suitable for redrawing formations, comparing
   revisions, analysing spacing and later calculating role suitability without
   reopening screenshots.
8. Preserve each slot's canonical position and role together with its duty,
   stable slot ID, coordinates, optional player, confidence, source import and
   validation state when generating, persisting and loading the football object
   model.

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
2. Retain `ScreenshotDerivedTacticDefinition` as the evidence-linked extraction
   layer between screenshots and the football object model.
3. The football object model is the primary representation used by the tactic
   screen.
4. Every extracted formation slot and instruction must remain traceable to its
   source import where requirement 006 provides that provenance.
5. Replacing or superseding a screenshot-derived phase must not silently delete
   its historical screenshot evidence.
6. Store when screenshot-derived extraction last ran and which screenshot
   imports it used.
7. Store when the football object model was generated and the exact
   screenshot-derived generation or source identity used to build it.
8. Do not require image OCR merely to open or redraw an existing football object
   model.

## Version history

1. Give every tactic an immutable sequence of revisions.
2. The first generated football object model creates the initial revision.
3. Importing a modified screenshot preserves the existing model revision and
   marks it as requiring regeneration.
4. Regenerating from changed screenshot-derived data creates a new model
   revision rather than overwriting the earlier revision.
5. Regenerating from unchanged screenshot-derived data must not create a
   duplicate revision.
6. Each revision must retain its creation time, optional note, source screenshot
   imports, screenshot-derived source identity, object-model formations,
   instructions, metadata and squad assignments as applicable at that revision.
7. Identify one revision as current without deleting prior revisions.
8. Allow the user to inspect the revision list and select an earlier revision in
   read-only form.
9. Produce a structured comparison between any two revisions that can identify
   metadata, slot, role, duty, coordinate and instruction changes.
10. Use factual change descriptions such as “AML changed from IF (Attack) to W
   (Support)” rather than generated tactical conclusions.
11. Do not claim that one revision performed better until match-result evidence
    and a separate analysis requirement support that conclusion.

## Persistence and compatibility

1. Preserve the separation between screenshot evidence,
   `ScreenshotDerivedTacticDefinition` and the generated football object model.
2. Store typed object-model metadata, phase formations, instructions, revision
   identity, generation date and screenshot-derived source identity.
3. Preserve existing tactics that have screenshots but no confirmed
   screenshot-derived extraction or generated object model; show an
   incomplete-data state and a route to process or regenerate where supported.
4. Upgrade existing databases without deleting or recreating user data.
5. Keep historical revisions and screenshot imports intact when the current
   revision changes.
6. Preserve all existing tactic list, welcome screen, import, squad and CLI
   workflows.
7. Do not replace the current football object model when regeneration produces
   incomplete or unresolved evidence. Retain the attempted extraction and its
   issues for review while continuing to display the existing saved model.

## Acceptance criteria

1. Opening a stored tactic displays Overview, Shape, Instructions and Analysis
   tabs for that tactic.
2. Overview displays stored metadata, assigned-squad information and a vector
   formation reconstructed from the football object model without showing the
   source screenshot as the tactic.
3. Shape displays distinct In Possession and Out of Possession pitches using
   stored coordinates, positions, roles, duties and optional players.
4. Instructions displays every captured instruction under a meaningful canonical
   name and the correct Build Up, Attack, Transition or Defence group.
5. Missing and unresolved values remain explicit and are never filled by
   inference or sample defaults.
6. The generated football object model round-trips canonical position, role,
   duty, slot ID, coordinates, optional player, confidence, source import and
   validation state without evidence loss.
7. Opening or switching tabs performs no OCR.
8. The Analysis tab has a useful empty state and does not misrepresent generated
   conclusions as imported data.
9. Assigned squads and player mappings are persisted independently of OCR.
10. A changed screenshot import marks the current model as requiring
   regeneration; regeneration creates a new immutable revision only when the
   screenshot-derived data changed.
11. Earlier revisions remain inspectable and two revisions can be compared using
    structured factual changes.
12. Existing tactics without a football object model remain accessible with a
    safe incomplete-data or processing-required state.
13. The UI displays evidence-updated and model-generated dates and identifies
    whether the current model was built from the latest screenshot-derived data.
14. Automated tests cover populated, partial and missing data; both formation
    phases; instruction grouping; squad assignment; revision creation and
    deduplication; freshness detection; revision comparison; and database
    migration.
15. Ruff, Black and the complete applicable automated test suite pass.

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

- Implement after or alongside the screenshot-derived data supplied by
  requirement 006.
- Reuse the formation visual components from requirement 005 where suitable.
- Keep pitch rendering independent of screenshots and OCR.
- Treat version comparison as a comparison of typed domain objects, not images.
