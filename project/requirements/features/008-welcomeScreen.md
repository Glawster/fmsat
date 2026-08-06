# 008 — Welcome screen

## Status

Backlog

## Objective

Replace the empty startup view with a useful welcome screen that immediately
shows the tactics and squads currently stored in FMSAT.

## Required behavior

1. Show the welcome screen when FMSAT starts and no task-specific view is open.
2. Present separate, clearly labelled summaries of stored tactics and squads.
3. Show each stored tactic and squad once, using its current saved name.
4. Include useful summary information already available locally, such as a
   tactic Formation thumbnail and squad player count, without requiring a new
   OCR operation.
5. Provide a clear empty state for tactics, squads, or both, with direct actions
   to start the corresponding import.
6. Refresh the welcome screen after an import, rename, update, or deletion.
7. Allow a displayed tactic or squad to open its existing management/detail
   view without duplicating that workflow.
8. Keep startup responsive by using bounded thumbnails and loading only the
   information needed for the visible summaries.

## Acceptance criteria

1. Starting FMSAT displays all stored tactics and squads without opening the
   Database window.
2. An empty database produces helpful import actions instead of blank panes.
3. Adding or deleting a tactic or squad updates the welcome screen during the
   same application session.
4. Selecting an item opens the appropriate existing view.
5. Closing the main application also closes any view opened from the welcome
   screen.
6. UI tests cover populated, partially populated, and empty states.

## Out of scope

- Replacing the full tactic and squad management screens.
- Editing OCR data directly on the welcome screen.
- Remote synchronization, cloud data, or online news content.
- Automatically starting an import when FMSAT opens.

## Delivery notes

- Reuse the existing database queries, persisted Formation thumbnails and
  window-lifecycle handling.
- Treat this as a low-interaction overview: avoid success dialogs and other
  acknowledgement steps.
