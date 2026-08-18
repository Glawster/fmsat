# Qt Designer workflow

FMSAT uses Qt Designer for static PySide6 layouts. Behaviour, signal wiring, service
calls, and dynamic widget population remain in Python view classes under `app/`.

The decision record is [ADR-001](../project/adr/001-qtDesignerUiAuthoring.md).

## Layout

| Path | Purpose |
| --- | --- |
| `app/ui/*.ui` | Designer source files edited visually |
| `app/ui/generated/ui_*.py` | Generated Python produced by `pyside6-uic` |
| `app/*.py` | View classes that call `setupUi()` and own behaviour |

Generated modules are committed so a normal editable install does not require Designer
or UIC at runtime.

## Editing a layout

1. Activate the Conda environment: `conda activate fmsat`
2. Open the `.ui` file in Designer: `pyside6-designer app/ui/<name>.ui`
3. Set widget `objectName` values in snake_case so they match project GUI naming rules
   and existing `.qss` selectors.
4. Regenerate Python:

```bash
python3 scripts/uiCompile.py
```

5. Wire signals and populate dynamic content in the matching Python view class.

Use `--check` in CI or pre-commit to fail when generated files are stale:

```bash
python3 scripts/uiCompile.py --check
```

## View class pattern

```python
class ExampleDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.ui = Ui_ExampleDialog()
        self.ui.setupUi(self)
        self.saveButton = self.ui.save_button
        self.saveButton.clicked.connect(self._save)
```

Keep aliases such as `self.saveButton = self.ui.save_button` when tests or callers
expect camelCase attribute names on the view instance.

## What belongs in Designer

- Dialog and panel shells
- Labels, buttons, tab containers, scroll areas, spacers
- Static form layouts

Keep these in Python:

- Custom-painted widgets such as `PitchWidget`
- Tables and lists whose columns or rows depend on runtime data
- OCR, import, database, and assessment workflows
- Long `.qss` styling (use `app/fmsat.qss` or dedicated `.qss` files)

Promote reusable custom widgets in Designer when a static layout needs them. Point the
promotion header at the existing import path, for example `fmsat.app.tacticPitchWidget.PitchWidget`.

## Incremental migration order

1. Small dialogs and utility windows
2. Medium management views with mostly static chrome
3. Partial sub-layouts extracted from large views such as `window.py`

Do not attempt to move an entire dynamic view into a single `.ui` file when most of
its structure is built from runtime models.
