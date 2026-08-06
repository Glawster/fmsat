# 003 — Tactic list management

## Status

In Progress

## Objective

Add a visual tactic-management screen where stored tactics can be recognised
from their Formation screenshots, selected individually or in groups, and
managed without repeatedly using single-item dialogs.

## Required behavior

1. Display every stored tactic in a dedicated tactic-list screen.
2. Show the tactic name and a small thumbnail derived from its latest Formation
   screenshot.
3. Show a clear placeholder when a tactic does not yet have a Formation image.
4. Preserve a suitable local image or generated thumbnail when a clipboard or
   file screenshot is confirmed so it remains available after FMSAT restarts.
5. Put a checkbox on every tactic entry for multi-selection.
6. Provide select-all and clear-selection controls.
7. Show the number of selected tactics and disable bulk actions when nothing is
   selected.
8. Provide a **Delete selected** action which lists or counts the affected
   tactics and requires explicit confirmation.
9. Delete only the checked tactics. Leave unchecked tactics and all squads
   intact.
10. Remove each deleted tactic's captures, stored thumbnails and squad-tactic
    applications without leaving orphaned database records or image files.
11. Refresh the list immediately after capture, update or deletion.
12. Keep the selection model suitable for additional bulk actions later without
    defining those actions as part of this requirement.

## Acceptance criteria

1. The list presents each stored tactic once with its name and latest Formation
   thumbnail or a placeholder.
2. Checkbox, select-all and clear-selection behavior is covered by UI tests.
3. Deletion cannot start with no selected tactics.
4. Cancelling deletion changes neither the database nor stored images.
5. Confirming deletion removes all and only the checked tactics and their
   tactic-owned relationships and files.
6. Squads and unchecked tactics remain available after a bulk deletion.
7. Restarting FMSAT retains the thumbnails for tactics that were not deleted.

## Out of scope

- Editing tactic instructions directly in FMSAT.
- Deleting squads or player history from the tactic-list screen.
- Cloud-hosted thumbnails or tactic synchronization.
- Bulk actions other than deletion.

## Delivery notes

- Generate bounded thumbnails rather than loading full-resolution screenshots
  for every visible list item.
- Keep original captures and thumbnails local, consistent with FMSAT's privacy
  model.
- Define transactional database and file-cleanup behavior before implementing
  bulk deletion.

## Completion evidence

Revalidated on 2026-08-07. The implementation provides managed Formation
images, full-width tactic listing, checkbox selection, guarded bulk deletion,
transactional database ownership cleanup and live refresh of an open tactic
editor after tactic changes.

Requirement-focused database and Qt coverage now verifies checkbox toggling,
select-all, clear-selection, selection counts, disabled deletion, no-selection
guarding, cancellation, managed-file cleanup, checked-only multi-delete,
preservation of unchecked tactics and squads, relationship cleanup and
Formation-image persistence across a database restart. The focused suite passes
with 39 tests and `git diff --check` passes.

The requirement remains In Progress because repository-wide verification is not
fully green: the complete suite has 127 passing tests and two existing
naming-policy failures; Ruff reports 30 existing issues and Black reports 16
existing files requiring formatting. Those broader merge-era cleanup items are
not caused by requirement 003 and are not being hidden by this evidence.
