# 006 — Structured tactic extraction

## Status

In Progress

## Objective

Convert a stored tactic's Formation, In Possession and Out of Possession
screenshots into typed, reviewable, correctable and persistent tactical data.
The resulting structured tactic must be trustworthy enough for later player
suitability and recruitment analysis, but those analyses are not part of this
requirement.

## Tactical domain model

1. Represent the three tactical phases explicitly: Formation, In Possession and
   Out of Possession.
2. Represent every visible formation slot with a stable slot identifier,
   tactical phase, canonical position, canonical role, duty, normalized pitch
   coordinates, optional displayed player, extraction confidence, source import
   session and validation state.
3. Preserve useful original OCR text alongside canonical values so corrections
   and extraction issues remain explainable.
4. Represent each team instruction with its phase, category, canonical value,
   display value, confidence, source import and validation state.
5. Represent a structured tactic with its identity, name, phase-specific slots,
   instructions, extraction issues, completeness and confirmation state.
6. Keep typed tactical domain objects separate from SQLAlchemy persistence
   models and Qt widgets.

## Canonical vocabulary

1. Define positions, roles, duties and team instructions in reusable YAML
   configuration rather than scattering display strings through code.
2. Support aliases and known OCR variants while preserving the observed text.
3. Support canonical duties `DEFEND`, `SUPPORT`, `ATTACK`, `AUTOMATIC` and
   `NONE`.
4. Include the positions and roles visible in supported FM26 fixtures, including
   goalkeeper, defensive, defensive-midfield, midfield, attacking-midfield and
   striker variants.
5. Each role definition must provide a code, display name, abbreviations,
   allowed positions and supported duties.
6. Unknown aliases must create review issues rather than crashes or invented
   tactical meaning.

The initial canonical position vocabulary must include:

`GK`, `DR`, `DCR`, `DC`, `DCL`, `DL`, `WBR`, `DMCR`, `DM`, `DMCL`, `WBL`,
`MR`, `MCR`, `MC`, `MCL`, `ML`, `AMR`, `AMCR`, `AMC`, `AMCL`, `AML`, `STCR`,
`STC` and `STCL`.

The initial role vocabulary must include observed FM26 identities for:

- Ball-Playing Goalkeeper and Sweeper Keeper;
- Full-Back, Wing-Back, Centre-Back and Ball-Playing Centre-Back;
- Deep-Lying Playmaker, Box-to-Box Midfielder, Defensive Midfielder and
  Pressing Defensive Midfielder;
- Wide Midfielder, Winger, Inside Forward and Attacking Midfielder; and
- Complete Forward, Target Forward, Channel Forward and Tracking Centre
  Forward.

Use the actual FM26 display names and abbreviations confirmed by fixtures. The
vocabulary must not infer attribute weights or behavior that is not observable
from those fixtures.

## Formation extraction

1. Extend the existing tactic parser while preserving Phase 2 tactic-name
   extraction and public behavior.
2. Use screen-specific parsers with shared reusable components where useful.
3. Locate the pitch through normalized, configurable regions.
4. Detect player or role tiles using computer vision before applying focused
   OCR where practical; do not infer the formation from unrestricted whole-pitch
   text order.
5. Extract the visible role abbreviation and displayed player name when
   available, normalize role and duty, and calculate component-level confidence.
6. Store tile centres as coordinates normalized between zero and one.
7. Classify coordinates into canonical position codes using configurable pitch
   zones that distinguish depth, width, centre and half-space variants without
   hardcoding one formation.
8. Preserve phase-specific positions because a slot may move between In
   Possession and Out of Possession.
9. Link slots across phases by displayed player, shirt number when available,
   relative ordering and spatial proximity in descending order of reliability.
10. Retain unmatched phase slots and create an issue when a cross-phase link is
    uncertain; never silently manufacture a match.

## Role knowledge gaps

1. After extracting and normalizing formation roles, compare every detected
   role and position pairing with the validated role knowledge base defined by
   requirement 010.
2. Represent a missing role definition as an explicit knowledge gap attached to
   the relevant tactic slot; do not discard the slot or invent role semantics.
3. Prompt the user for a Football Manager role-profile screenshot for each
   distinct missing role and position pairing, without requesting the same
   evidence once per duplicated tactic slot.
4. Tell the role-profile workflow which position, role name and abbreviation
   were observed on the tactic screen so it can validate the submitted evidence.
5. A missing role definition may be saved in a structured tactic draft but must
   remain visible as an unresolved issue until the definition is supplied or the
   detected role is corrected.

## Team-instruction extraction

1. Parse the labelled cards in the In Possession and Out of Possession screens.
2. For each configured category, detect its region, extract the selected value,
   normalize it through aliases, retain original OCR text and confidence, and
   report missing or ambiguous values.
3. Support at least the supplied In Possession categories: passing directness,
   tempo, time wasting, attacking transition, attacking width, play for set
   pieces, creative freedom, build-up strategy, goal kicks, goalkeeper
   distribution, supporting runs, dribbling, progress through, pass reception,
   patience, shots from distance, crossing style and goalkeeper distribution
   speed.
4. Support at least the supplied Out of Possession categories: line of
   engagement, defensive line, trigger press, defensive transition, tackling,
   cross engagement, pressing trap, short goalkeeper distribution and defensive
   line behaviour.
5. Do not use values from sample tactics as defaults.

## Review and correction

1. Enable **Review Structured Tactic** after all three required tactic captures
   are stored.
2. Add a PySide6 review workflow without replacing the existing main window.
3. Present Formation, In Possession, Out of Possession, Instructions and Issues
   views, or an equivalently clear organization.
4. Display slots on a simple pitch at their normalized coordinates with player,
   position, role, duty, confidence and validation state.
5. Allow position, role, duty and linked player to be corrected using controlled
   values from canonical configuration.
6. Display instructions with phase, category, detected value, confidence and
   status, and allow configured-value correction.
7. List unknown aliases, missing or duplicate slots, unrecognized instruction
   values, low confidence, uncertain links and incomplete coverage as issues.
8. Highlight low-confidence component values rather than relying on a single
   tactic-level confidence.
9. Provide **Save Draft** and **Confirm Structured Tactic** actions.
10. Allow incomplete drafts to be saved. Block confirmation for serious
    unresolved errors and require acknowledgement for permitted warnings.
11. Provide a direct action from each missing-role issue to submit and review a
    role-profile screenshot as defined by requirement 010.

## Validation

Validation must be independent of the UI and classify findings as error,
warning or information. At minimum validate:

1. one visible goalkeeper and eleven total slots for a complete first-team phase;
2. unique stable slot identifiers;
3. recognized position, role and duty codes;
4. role compatibility with the selected position;
5. normalized coordinates between zero and one;
6. required instruction categories having a value or explicit unresolved issue;
7. source imports belonging to the correct tactic; and
8. Formation, In Possession and Out of Possession data not being mixed.

## Persistence and compatibility

1. Extend the SQLAlchemy schema without deleting or recreating existing user
   databases.
2. Store one current structured definition per tactic while retaining historical
   screenshot imports.
3. Allow one re-imported phase to replace or supersede only that phase's current
   extracted data.
4. Persist source import links, extracted values, manual corrections, validation
   state, issues, draft state and confirmation state.
5. Distinguish extracted, manually corrected, confirmed and unresolved data.
6. Existing Phase 2 databases must open safely and acquire missing tables using
   the smallest maintainable schema-upgrade strategy.
7. Preserve all Phase 2 tactic, squad, relationship, screenshot and integrated
   `.fmf` parser workflows and public commands.

## Services, diagnostics and logging

1. Keep extraction, validation, persistence and UI orchestration separate; Qt
   must not perform OCR or direct SQLAlchemy queries.
2. Use shared application services and a repository/database boundary for both
   desktop and command-line workflows.
3. Provide diagnostic commands to extract, show and validate a structured tactic
   where practical, including JSON output for machine-readable inspection.
4. Do not break existing `fmsat parser ...` commands or the repository's
   `app function --argument` CLI convention.
5. Log parser selection, configured regions, tile and category counts,
   normalization failures, confidence warnings, validation results, persistence
   updates and stage durations without logging image data.

## Acceptance criteria

1. A tactic with all three screenshots produces a reviewable structured draft.
2. Eleven phase-specific slots are extracted where visible, each with normalized
   coordinates, position, role, duty, source and component confidence.
3. Supported team-instruction cards produce canonical values with source and
   confidence.
4. Unknown and uncertain values become explicit issues rather than guesses.
5. The user can correct slots and instructions, save a draft and later reload it.
6. Serious unresolved validation errors block confirmation.
7. Confirmed structured tactics and manual corrections survive restart.
8. Re-extracting one phase leaves other phases and historical imports intact.
9. Existing Phase 2 databases and workflows continue to work without data loss.
10. Automated tests cover vocabulary, pitch zones, formation extraction,
    instruction extraction, phase linking, persistence, services and review
    behavior without requiring live OCR downloads.
11. Diagnostic output is available through the established CLI architecture.
12. Ruff, Black and the complete applicable automated test suite pass.
13. User and architecture documentation accurately describe the delivered
    workflow, schema upgrade, configuration, limitations and future consumers.
14. A tactic containing a role absent from the knowledge base prompts once for
    suitable evidence and can resolve the issue after a verified role profile is
    confirmed.

## Out of scope

- Player-role suitability or attribute weighting.
- Best-position, starter, backup or squad-depth recommendations.
- Recruitment priorities, transfer filters or tactical advice.
- Match analysis, result analysis or report generation.
- Football Manager UI automation, save-file reading or game modification.

## Delivery notes

- Implement incrementally: vocabulary and domain model, normalization and
  validation, persistence, extraction, services and CLI, review UI, then
  documentation.
- Prefer small controlled crops or synthetic fixtures over personal
  full-resolution screenshots.
- Reuse requirement 005's formation-row palette and role-icon component in the
  structured review UI when that component is implemented.
