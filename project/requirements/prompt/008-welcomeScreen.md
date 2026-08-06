# Codex task — Implement requirement 008: Welcome screen and workspace dashboard

Work in the existing FMSAT repository.

Create and use a feature branch following the repository's branch naming
convention. A suitable name is:

`feature/008-welcome-screen`

Read the repository documentation and coding standards before making changes.
Read the updated requirement document for requirement 008 in full and treat it
as the source of truth.

## Goal

Replace the current startup player-attribute table with a dedicated welcome
screen that:

- presents major application operations as clear on-screen actions;
- lists stored tactics and squads in separate sections;
- provides useful import actions for empty states;
- opens existing tactic and squad views;
- refreshes after relevant data changes;
- never displays editable player data on the welcome screen.

Do not redesign unrelated screens and do not implement future analysis,
recruitment, or reporting features.

## First step — inspect and report

Before editing code, inspect the repository and identify:

1. the main window and current startup widget;
2. the editable squad/player table currently shown at startup;
3. existing menu and toolbar actions for:
   - Import Tactic
   - Import Squad
   - Apply Tactic to Squad
   - Database
   - Players
   - Settings
4. existing tactic and squad models, repositories, services, and queries;
5. existing tactic and squad management/detail views;
6. current application signal/event patterns;
7. existing formation-thumbnail persistence and loading;
8. window ownership and shutdown behaviour;
9. current UI test framework and fixtures;
10. the project's styling, icon, logging, and dependency conventions.

Briefly state the implementation plan before modifying files. Do not ask for
confirmation unless a genuinely blocking ambiguity remains after inspecting the
code.

## Required implementation

### 1. Dedicated welcome view

Create a dedicated Qt welcome widget or page and make it the default content
shown when the application starts and no task-specific view is active.

The old editable player attribute grid must not appear on the welcome screen.
It must remain available only inside its proper squad import/review workflow.

Follow the repository's existing architecture and naming patterns. Do not create
an unnecessary parallel navigation framework.

### 2. Two-pane layout

Implement a responsive two-pane desktop layout.

#### Left pane: major operations

Provide clearly labelled controls for currently implemented operations:

- Import Tactic
- Import Squad
- Apply Tactic to Squad
- Open Database
- Open Players
- Open Settings

Reuse the same QAction, command, service, controller, or application method used
by the existing menu/toolbar item. Do not duplicate import or navigation logic.

Where a listed operation is not implemented, hide it or disable it with a useful
tooltip. Do not create placeholder dialogs.

#### Right pane: stored tactics and squads

Create separate labelled sections for:

- Tactics
- Squads

Each section must display its item count and bounded summary cards or rows.

The right pane should scroll when necessary without making the quick-actions
panel disappear.

### 3. Tactic summaries

Show each stored tactic once using its current saved name.

Where data already exists, show:

- tactic name;
- formation name or shape;
- a bounded formation thumbnail;
- last imported or updated date;
- linked squad count, only if already supported.

Do not run OCR or parse screenshots to create the summary.

Handle missing formation names, missing thumbnails, invalid image paths, and
incomplete optional metadata with neutral placeholders.

Opening a tactic must reuse the existing tactic detail/management view.

Do not add prominent one-click delete actions to cards unless that interaction
already exists consistently elsewhere in the application.

### 4. Squad summaries

Show each stored squad once using its current saved name.

Where data already exists, show:

- squad name;
- player count;
- last imported or updated date;
- linked tactic name, only if already supported.

Use an efficient count query. Do not load full player attribute records just to
calculate the player count.

Opening a squad must reuse the existing squad detail/management view.

Do not display the full player list or editable attributes on this screen.

### 5. Empty and partial states

Implement all states:

- no tactics and no squads;
- tactics only;
- squads only;
- tactics and squads.

An empty section must explain that no items exist and offer the corresponding
existing import action.

The fully empty screen should welcome the user and offer both first-import
actions. It must not look like a failed or unfinished load.

### 6. Refresh behaviour

Refresh welcome summaries during the same application session after successful:

- tactic import;
- squad import;
- tactic rename;
- squad rename;
- tactic update;
- squad update;
- tactic deletion;
- squad deletion;
- tactic/squad link changes, where supported.

Prefer the repository's existing signal/event approach. If none exists, add one
small, central application-level notification mechanism rather than directly
coupling every child window to the welcome widget.

Avoid refresh loops and duplicate signal connections.

### 7. Navigation and lifecycle

- Existing menu and toolbar actions must continue to work.
- Welcome-screen actions must route through those same commands.
- Opening an item must not create duplicate management workflows.
- Returning from or closing a child view must leave the welcome screen
  available.
- Child windows opened from the welcome screen must have correct Qt ownership.
- Closing the main application must close all child views it owns.
- Do not introduce orphan windows or hidden processes.

### 8. Performance

- Do not run OCR when opening or refreshing the welcome view.
- Use bounded thumbnail sizes and preserve aspect ratios.
- Load only fields needed for summaries.
- Keep database queries bounded and avoid N+1 queries where practical.
- Do not block the GUI thread with slow image or database work.
- If asynchronous loading is warranted by the existing architecture, provide a
  simple loading state and ensure results are applied safely on the GUI thread.
- Cache only where it is safe and invalidate caches after relevant changes.

### 9. Accessibility and UX

- Use visible text labels, not icon-only controls.
- Preserve logical keyboard tab order.
- Provide visible focus states.
- Add meaningful accessible names.
- Do not rely on colour alone.
- Use useful tooltips for disabled actions.
- Ensure cards remain understandable without thumbnails.
- Follow existing theme, spacing, font, and scaling conventions.
- Avoid routine success dialogs.

### 10. Error handling and logging

- One broken thumbnail must not prevent the screen loading.
- Incomplete optional metadata must not crash rendering.
- A database read error should produce a useful, non-destructive error state.
- Use the existing logger.
- Do not silently swallow unexpected exceptions.
- Do not hide duplicate rows by applying arbitrary UI deduplication; correct the
  underlying query or report the model problem.

## Architecture guidance

Use the project's existing architecture. A possible decomposition is:

- `WelcomeView`
- `WelcomeViewModel` or `WelcomeService`
- `QuickActionsPanel`
- `TacticSummarySection`
- `SquadSummarySection`
- reusable summary-card widgets
- reusable empty-state widget

These names are illustrative, not mandatory.

The welcome view must not contain OCR, parsing, raw SQL, or persistence logic.
Use the existing repository/service layer.

Keep paths platform-independent and preserve Linux and future Windows support.

## Tests

Add or update automated tests for at least:

- empty database;
- tactics only;
- squads only;
- fully populated state;
- player attribute grid absent from startup;
- tactic summary opens the existing tactic view;
- squad summary opens the existing squad view;
- quick actions reuse existing commands;
- import triggers refresh;
- rename triggers refresh;
- deletion triggers refresh;
- missing thumbnail uses placeholder;
- incomplete optional metadata is tolerated;
- application close closes child views.

Use the repository's existing Qt testing tools and fixtures. Prefer behavioural
tests over implementation-detail tests.

Mock OCR because the welcome screen must not invoke it.

Run the complete relevant test suite, linting, formatting, and type checks
required by the repository.

## Documentation

Update documentation where needed to reflect:

- the new startup screen;
- the major actions available;
- the tactic and squad summaries;
- empty-state behaviour;
- any new internal event/signal used for refresh.

Keep requirement 008 marked consistently with the project's workflow once the
implementation is complete.

## Constraints

Do not:

- remove the editable squad review table from its import workflow;
- alter OCR extraction behaviour;
- add tactical-fit scoring;
- add squad-depth analysis;
- add recruitment recommendations;
- add online content or cloud synchronisation;
- introduce a new database source of truth;
- rewrite unrelated navigation;
- add placeholder buttons that do nothing;
- make broad refactors unrelated to requirement 008.

## Completion report

When finished, provide:

1. a concise summary of the user-visible change;
2. the main files added or changed;
3. architecture decisions;
4. database/query changes, if any;
5. tests added and their results;
6. lint/type-check results;
7. any remaining limitations;
8. manual verification steps;
9. the exact branch name and final commit hash.

Do not claim a test or check passed unless it was actually run.
