# 001 — Football Manager file transfer

## Status

Backlog

## Objective

Add an FMSAT command which transfers selected Football Manager 26 custom files
from Andy-PC to TV-PC. The computers do not need to remain available at the
same time for every workflow, and routine updates should avoid retransferring
the full player face pack.

## Source and destination

The expected Football Manager document root on both computers is:

```text
/mnt/games/SteamLibrary/steamapps/compatdata/3551340/pfx/drive_c/users/steamuser/Documents/Sports Interactive/Football Manager 26
```

The source root, destination root and SSH target must remain configurable.
The final TV-PC SSH host and user are intentionally unresolved until delivery.

## Included files

1. Copy `tactics/` recursively.
2. Copy `filters/` recursively.
3. Copy root-level `graphics/players/*.png` headshots.
4. Copy `graphics/players/config.xml`.
5. Do not copy `graphics/players/originals/` or unrelated Football Manager data.

The current Andy-PC player payload is approximately 251,000 files and 15 GB,
so the implementation must be suitable for a large initial transfer and small
incremental updates.

## Required behavior

1. Use `rsync` over SSH as the primary transfer mechanism.
2. Transfer only new or changed files after the initial synchronization.
3. Never delete destination files merely because they are absent at the source.
4. Show an itemized dry-run by default.
5. Require explicit confirmation before transferring files.
6. Preserve paths, modification times and file contents.
7. Check that required source directories and `rsync` are available before use.
8. Report an unavailable TV-PC clearly without changing local files.
9. Quote paths safely, including the spaces in the Football Manager path.
10. Keep transfer orchestration outside the Qt UI so it can be tested and used
    non-interactively.

## Optional offline archive

An optional small archive may contain tactics, filters and `config.xml` for use
while TV-PC is offline. The multi-gigabyte headshot collection should not be
included in that archive by default; headshots should use incremental `rsync`.

## Proposed interface

```text
fmsat files sync [--target HOST] [--source-root PATH] [--destination-root PATH]
                 [--confirm]
fmsat files capture [--archive PATH] [--source-root PATH]
fmsat files release ARCHIVE [--destination-root PATH] [--confirm]
```

Command names may be refined when implemented, but dry-run and confirmation
semantics must remain explicit.

## Acceptance criteria

1. A dry-run lists the files that would be transferred without modifying TV-PC.
2. A confirmed initial run transfers every included file.
3. A later confirmed run transfers only additions and changes.
4. Nested player originals and unrelated files are demonstrably excluded.
5. No destination file is deleted by the synchronization workflow.
6. Paths and SSH target can be overridden without code changes.
7. Unit tests validate command construction, inclusion rules, dry-run behavior,
   confirmation and error reporting without requiring a live TV-PC.
8. A manual integration check against TV-PC is recorded before completion.

## Out of scope

- Continuous background synchronization.
- Synchronizing saves, editor data, matches or screenshots.
- Starting or waking TV-PC automatically.
- Removing stale destination headshots.

## Delivery notes

- Prefer an FMSAT core service plus a CLI dispatcher command.
- Do not make the Qt application or OCR dependencies necessary for the sync CLI.
- Confirm the SSH target and authentication method before implementation.
