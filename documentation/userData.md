# User Data

FMSAT stores all user-generated information outside the repository.

This allows the application to be upgraded without risking user data.

## Default location

Linux

```text
~/.local/state/fmsat/
```

If `XDG_STATE_HOME` is defined, FMSAT instead uses

```text
$XDG_STATE_HOME/fmsat/
```

---

## Directory layout

```text
fmsat/
├── fmsat.sqlite3
├── screenshots/
├── knowledge/
│   ├── roles/
│   └── requirements/
└── logs/
    └── application.log
```

---

## Database

Contains

- tactics
- squads
- imported players
- relationships
- import history

---

## Screenshots

Contains

- retained import screenshots
- club badges
- evidence images

These are retained to allow review and future reprocessing.

---

## Knowledge

Contains user-confirmed role definitions.

Bundled definitions are never modified.

User definitions override bundled definitions when validated.

---

## Logs

Application logging is stored alongside other application state.

The desktop log records startup paths, tactic-processing stages, screenshot
coverage, OCR candidate counts, selected-instruction scores, unresolved issues,
integrity-gate decisions and object-model persistence. Daily files use the name
`fmsat-YYYY-MM-DD.log` under `~/.local/state/fmsat/` on Linux.

Logs are rotated automatically.

Image data is never written to the logs.

---

## Migration

When upgrading from older versions that stored data inside the repository,
FMSAT automatically copies

``` text
data/fmsat.sqlite3
data/screenshots/
```

to the XDG state directory.

The original files are left untouched as a recovery copy.
