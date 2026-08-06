# 008 — Welcome screen and workspace dashboard

## Status

In progress

## Objective

Replace the current player-data table shown at application startup with a dedicated
welcome screen that acts as the main FMSAT workspace.

The welcome screen must:

- present the application's major operations as clear on-screen actions;
- show the tactics and squads already stored in FMSAT;
- provide useful empty states when no data exists;
- allow the user to open existing tactic and squad management views;
- never show editable player attribute data directly on the welcome screen.

The screen is intended to be a low-interaction overview and navigation hub rather
than another data-management view.

## User outcome

When FMSAT starts, the user should immediately be able to answer:

1. What can I do next?
2. Which tactics are stored?
3. Which squads are stored?
4. Which tactic or squad do I want to open?
5. Do I need to import my first tactic or squad?

## Scope

### Included

- A dedicated startup/welcome view.
- A major-actions panel.
- Separate stored-tactics and stored-squads summaries.
- Empty states with direct import actions.
- Opening existing tactic and squad views.
- Refreshing the summaries during the current application session.
- Lightweight locally available summary metadata.
- UI tests for empty, partial, and populated states.

### Excluded

- Displaying or editing player attributes on the welcome screen.
- Replacing the existing tactic, squad, player, database, or settings views.
- Performing OCR directly inside a tactic or squad summary card.
- Tactical analysis, squad-depth assessment, recruitment recommendations, or
  reporting that is not already implemented.
- Remote synchronisation, cloud storage, online news, or community content.
- Automatically starting an import when FMSAT opens.
- Requiring new database data solely to decorate the welcome screen.

## Layout

Use a responsive two-pane desktop layout.

### Left pane — major operations

Provide clearly labelled action buttons for the application's primary workflows.

Required actions:

- Import Tactic
- Import Squad

The welcome screen and main toolbar must not duplicate editor-specific actions.
`Apply Tactic to Squad` belongs in the tactic editor and `Clean Up Data` belongs
in the squad editor. A File/View menu bar is not required.

Actions that are not yet implemented must either:

- remain hidden; or
- be visibly disabled with a useful tooltip.

Do not add buttons that lead to placeholder or duplicate workflows.

The action panel should remain usable at the application's minimum supported
window size. It may become scrollable where necessary.

### Right pane — stored data

Show two clearly labelled sections:

1. Tactics
2. Squads

Each section must show a count and a collection of bounded summary cards or rows.

The right pane may scroll independently when the number of stored items exceeds
the visible area.

The layout must not reserve space for the old player-attribute table.

## Tactic summaries

Show each stored tactic exactly once using its current saved name.

Display only information already available locally, where present:

- tactic name;
- formation name or shape;
- bounded formation thumbnail;
- last updated or imported date;
- linked squad count, only if that relationship already exists.

A missing thumbnail or formation value must not prevent the tactic being shown.
Use a neutral placeholder where needed.

Selecting or opening a tactic must open the tactic editor with that tactic selected.

A tactic summary must not expose destructive actions as a prominent one-click
control. Any delete or rename operation should remain in the existing management
view unless the application already has a consistent context-menu pattern.

## Squad summaries

Show each stored squad exactly once using its current saved name.

Display only information already available locally, where present:

- squad name;
- player count;
- last updated or imported date;
- linked tactic name, only if that relationship already exists.
- a bounded image captured from the club-information screen.

The squad image must come from a club-information screenshot rather than a
tactic Formation screenshot.

Selecting or opening a squad must open the squad editor with that squad selected.

Do not display the complete player list or any editable player attributes on the
welcome screen.

## Dashboard summary

A small summary area may show locally available totals such as:

- number of stored tactics;
- number of stored squads;
- number of stored players;
- most recent import date.

This summary is optional if it would duplicate the section headings without
adding useful information.

Do not calculate tactical-fit, squad-depth, recruitment, or readiness scores as
part of this requirement.

## Empty states

### No tactics

Show a clear explanation and an `Import Tactic` action.

Suggested wording:

> No tactics have been imported yet.

### No squads

Show a clear explanation and an `Import Squad` action.

Suggested wording:

> No squads have been imported yet.

### Empty database

Show a welcoming introduction and both first-import actions.

The screen must not appear broken or contain a large unexplained blank area.

### Partial state

When one section has data and the other is empty, show the populated section and
the appropriate empty state together.

## Startup and navigation behaviour

1. Show the welcome screen when FMSAT starts and no task-specific view is open.
2. Do not open the Database window automatically.
3. Do not automatically start an import.
4. Opening a tactic or squad must reuse the existing view and window-lifecycle
   handling.
5. Returning from or closing a task-specific view must leave the welcome screen
   available.
6. Closing the main application must close any child view opened from the
   welcome screen.
7. Existing menu and toolbar commands must continue to work.
8. The welcome-screen buttons must invoke the same application services or
   commands as the corresponding menu or toolbar actions rather than duplicating
   business logic.

## Refresh behaviour

Refresh the welcome screen after any successful:

- tactic import;
- squad import;
- tactic rename;
- squad rename;
- tactic update;
- squad update;
- tactic deletion;
- squad deletion;
- tactic-to-squad link change, where applicable.

The refresh must occur during the same application session without requiring an
application restart.

Prefer a central application event, signal, or refresh service over direct
coupling between every child window and the welcome widget.

Avoid unnecessary full database reloads where a bounded refresh is sufficient.

## Performance and responsiveness

- Keep startup responsive.
- Load only the information needed for visible summaries.
- Reuse existing database queries where practical.
- Use bounded thumbnail dimensions.
- Scale thumbnails while preserving aspect ratio.
- Do not run OCR when building or refreshing the welcome screen.
- Do not load full player attribute snapshots merely to obtain a squad count.
- Avoid performing slow database or image work on the GUI thread where it could
  noticeably block startup.
- Display a simple loading state when asynchronous loading is required.
- Handle missing or invalid thumbnail files gracefully.

## Visual and interaction guidance

- Use the application's existing Qt styling and theme conventions.
- Prefer clear text labels over icon-only controls.
- Icons may supplement labels but must not be the sole indication of purpose.
- Maintain sufficient spacing between the actions panel and stored-data panel.
- Ensure keyboard navigation follows a sensible order.
- Provide visible focus states.
- Give interactive cards an obvious hover or selection state.
- Double-click, an `Open` control, or both may open an item; use the interaction
  pattern already established elsewhere in FMSAT.
- Avoid acknowledgement or success dialogs for routine navigation and refreshes.

## Data and architecture requirements

- Reuse existing database models and repositories.
- Reuse persisted formation thumbnails where available.
- Do not create a second source of truth for tactics or squads.
- Keep the welcome-screen widget free of OCR, parsing, and persistence logic.
- Use application services, repositories, view models, or equivalent existing
  architectural layers.
- Keep tactic and squad summary presentation components reusable.
- Keep filesystem path handling platform-independent.
- Preserve compatibility with Linux and future Windows packaging.

A reasonable component structure may include:

- `WelcomeView`
- `WelcomeViewModel` or `WelcomeService`
- `QuickActionsPanel`
- `TacticSummarySection`
- `SquadSummarySection`
- `TacticSummaryCard`
- `SquadSummaryCard`
- `EmptyStateWidget`

These names are illustrative; follow the repository's existing naming and
architectural conventions.

## Error handling

- A failure to load one thumbnail must not prevent other summaries appearing.
- A database read failure must produce a useful non-destructive error state.
- Log unexpected failures through the existing logging system.
- Do not crash when a stored item has incomplete optional metadata.
- Do not silently discard duplicate database rows; fix or report the underlying
  query/model issue if duplicates are encountered.

## Accessibility

- All major actions must be keyboard accessible.
- Controls must have meaningful accessible names.
- Do not rely on colour alone to communicate state.
- Text must remain readable under supported display scaling.
- Tooltips should explain disabled actions.
- Card content should remain understandable when thumbnails are unavailable.

## Acceptance criteria

1. Starting FMSAT displays the dedicated welcome screen rather than the editable
   player-data table.
2. The welcome screen contains clear controls for the currently implemented
   major operations.
3. All stored tactics are shown once using their current names.
4. All stored squads are shown once using their current names.
5. The welcome screen does not display editable player attribute data.
6. An empty database shows helpful `Import Tactic` and `Import Squad` actions.
7. A tactics-only database shows tactics and a squad empty state.
8. A squads-only database shows squads and a tactic empty state.
9. A populated database shows both sections with correct counts.
10. A tactic summary can open the existing tactic management/detail view.
11. A squad summary can open the existing squad management/detail view.
12. Existing toolbar and menu actions continue to operate.
13. Importing, renaming, updating, deleting, or relinking relevant data refreshes
    the welcome screen during the same application session.
14. Missing thumbnails or optional metadata do not crash or hide an item.
15. No OCR operation runs merely to display or refresh the welcome screen.
16. Closing the main application closes views opened from the welcome screen.
17. UI tests cover empty, partially populated, populated, refresh, navigation,
    and missing-thumbnail states.
18. Existing tests continue to pass.

## Suggested UI tests

- `test_welcome_view_empty_database`
- `test_welcome_view_tactics_only`
- `test_welcome_view_squads_only`
- `test_welcome_view_populated`
- `test_welcome_view_does_not_show_player_attribute_grid`
- `test_tactic_card_opens_existing_view`
- `test_squad_card_opens_existing_view`
- `test_import_refreshes_welcome_view`
- `test_rename_refreshes_welcome_view`
- `test_delete_refreshes_welcome_view`
- `test_missing_thumbnail_uses_placeholder`
- `test_main_window_close_closes_child_views`
- `test_quick_actions_reuse_existing_commands`

## Delivery notes

- Inspect the existing repository before choosing component names or introducing
  new abstractions.
- Reuse existing commands, services, database queries, persisted thumbnails, and
  window-lifecycle handling.
- Remove the startup dependency on the current editable squad table without
  removing that table from its proper import/review workflow.
- Keep the implementation focused on requirement 008.
- Do not implement speculative future dashboard analytics.
