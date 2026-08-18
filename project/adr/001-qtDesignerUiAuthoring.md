# ADR-001: Qt Designer UI authoring

## Status

Accepted

## Context

FMSAT builds its PySide6 desktop interface programmatically in Python. Layout code
now spans many large view modules, which makes visual structure harder to review and
change. The project already separates Qt orchestration from `core/` business logic and
uses external `.qss` styling for several views.

## Decision Drivers

- Layout structure should be visible without reading hundreds of lines of widget code.
- Core logic must remain testable without a Qt event loop.
- Existing GUI naming, pytest-qt, and packaging conventions must keep working.
- Migration must be incremental; large dynamic views cannot move entirely into Designer.

## Considered Options

1. Continue authoring all layouts in Python.
2. Load `.ui` files at runtime with `QUiLoader`.
3. Compile `.ui` files to Python with `pyside6-uic` at build or commit time.

## Decision Outcome

Use compile-time `pyside6-uic` generation.

- Store Designer source files under `app/ui/`.
- Commit generated Python modules under `app/ui/generated/`.
- Keep behaviour, signal wiring, service calls, and dynamic widget population in Python
  view classes under `app/`.
- Use Qt Designer only for static layout shells; custom-painted widgets and data-driven
  tables remain Python components promoted or inserted at runtime.

### Consequences

- Positive: Generated widgets remain importable, typed, and reachable from pytest-qt
  tests. No runtime dependency on shipping raw `.ui` assets.
- Positive: Incremental migration can start with small dialogs and windows.
- Negative: Contributors must regenerate UI Python when `.ui` files change.
- Negative: Large views such as `window.py` will only partially move to Designer.
