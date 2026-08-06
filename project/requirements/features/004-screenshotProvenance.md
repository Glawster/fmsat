# 004 — Screenshot provenance and management

## Status

In progress

## Objective

Let the user inspect the screenshot from which a squad player's data was
extracted, so OCR mistakes can be corrected with the original Football Manager
screen visible. Provide a later management workflow for removing obsolete
captures and their old data safely.

## Source screenshot viewer

1. Preserve every confirmed squad screenshot in managed local FMSAT storage,
   including screenshots acquired from the clipboard.
2. Associate each confirmed player snapshot with its source screenshot through
   the existing import session.
3. Add a **Show Screenshot** action to the context menu for a selected player in
   the squad list or review table.
4. Open the source screenshot in a separate, non-modal window so the squad data
   remains visible and editable.
5. Position the viewer beside the main window where the available desktop or a
   second monitor permits, rather than covering the correction table.
6. Scale the image initially to fit while preserving its aspect ratio, with a
   way to inspect readable detail at its original resolution.
7. Provide an explicit **Close** button as well as the normal window close
   control.
8. Show a clear explanation when a legacy import has no retained image or its
   screenshot file is unavailable.
9. Keep screenshots local and validate stored paths before opening them.
10. Give every managed capture a readable, filesystem-safe name containing its
    capture timestamp, owner type and normalized squad or tactic name, screen
    type, and a short collision-resistant identifier.
11. Store managed captures as PNG files and never overwrite an earlier capture,
    even when two captures occur within the same second.

An indicative filename is:

```text
20260805-114500_squad-first-team_squad-attributes_a1b2c3d4.png
```

Names must be derived through a single naming service rather than assembled in
the Qt UI. Unsafe characters and untrusted OCR text must not become path
separators or escape managed screenshot storage.

## Future screenshot removal

1. Add a screenshot-management window listing stored captures by squad, import
   date and screen type.
2. Allow one or more obsolete screenshots to be selected for removal.
3. Preview the affected player snapshots and other dependent records before
   removal.
4. Require explicit confirmation and delete all selected captures and their
   owned data transactionally.
5. Do not remove the squad, unrelated imports, tactic captures or newer player
   data.
6. Remove managed image files only after the database operation succeeds, and
   report any file-cleanup failure without hiding the database result.

## Acceptance criteria

1. Right-clicking a player and choosing **Show Screenshot** opens the correct
   source image in a separate window.
2. The main correction table remains available while the viewer is open.
3. The viewer has a working Close button and preserves image proportions.
4. Clipboard-acquired screenshots remain viewable after restarting FMSAT.
5. Two players from different imports open their respective source images.
6. Missing legacy images produce a helpful message rather than an exception.
7. Viewer behavior is covered by UI tests and screenshot-path lookup is covered
   without requiring OCR.
8. Screenshot removal is delivered only with selection, dependency preview,
   confirmation, transactional database tests and managed-file cleanup tests.
9. Managed screenshot filenames are readable, unique, filesystem-safe and
   reproducible under unit tests with an injected timestamp and identifier.

## Out of scope

- Editing or annotating the source screenshot.
- Removing screenshots directly from the viewer window.
- Opening arbitrary paths not managed or explicitly selected by the user.

## Delivery notes

- Centralize screenshot storage and cleanup outside the Qt UI.
- Use bounded previews for list and viewer startup performance while retaining
  access to the original-resolution image.
- Plan migration behavior for existing import sessions whose image filename is
  `clipboard` and therefore has no recoverable source image.

## Phase 2 delivery evidence

Managed screenshot persistence, readable collision-resistant names, player-to-
capture provenance, the non-modal screenshot viewer, missing-image handling and
safe tactic/squad owner deletion were delivered in Phase 2 and are covered by
database, screenshot-store and UI lifecycle tests. Selective screenshot-level
removal and dependency preview remain future work, so this broader requirement
remains in progress.
