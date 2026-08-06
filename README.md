# Football Manager Squad Assessment Tool

FMSAT is a local desktop application that imports a tactic and extracts structured player
data from Football Manager screenshots. It does not modify Football Manager, automate it,
or read save files.

The package also absorbs the repository's earlier `.fmf` parser. Those inspection and
comparison commands are available under `fmsat parser`, while `fmsat` launches the desktop
application.

## Documentation

- [Architecture](documentation/architecture.md)
- [Sample screenshot guidance](documentation/sampleScreenshots.md)
- [Football Manager file transfer requirement](project/requirements/features/001-footballManagerFileTransfer.md)

## Workspace and import workflow

1. Launch FMSAT. The workspace shows the stored tactics and squads, with
   **Import Tactic** and **Import Squad** actions at the top left.
2. Select **Import Tactic** (`Ctrl+T`).
3. Import the Formation screenshot. FMSAT extracts the tactic name and asks you to confirm
   or correct it.
4. Select **Import Tactic** again for the In Possession screenshot, then once more for the
   Out of Possession screenshot. FMSAT tracks the next missing capture for each tactic.
5. Select **Import Squad** (`Ctrl+I`) and name or select the squad independently. When
   creating a new squad, FMSAT first asks for a Club Information screenshot showing the
   club badge. This image is retained for the squad's workspace card and is not sent to OCR.
6. Copy each requested Squad Attributes screenshot to the clipboard and return to FMSAT.
   Capture as many player pages or attribute views as needed, then finish the import.
7. Review the spreadsheet-style squad result. Missing, corrected, or low-confidence values
   are highlighted.
8. Correct any cell and select **Save Confirmed Data** (`Ctrl+S`) from the File menu.
9. Confirmed imports are stored in `data/fmsat.sqlite3` at the repository root.

The main toolbar remains deliberately limited to the two import actions. The File and View
menus provide the remaining application commands. Selecting **Open** on a tactic or squad
workspace row opens the corresponding focused editor with that record selected. Use
**Apply Tactic to Squad** from the tactic editor and **Clean Up Data** from the squad editor.

When a tactic already has all three tactic screenshots, FMSAT offers to import an updated
Formation screenshot while retaining the previous import history. Squads are stored
independently rather than owned by a tactic, allowing the same squad to be assessed against
multiple tactics. Applying a tactic creates a reusable many-to-many pairing; it does not
move the squad or prevent another tactic from being applied.

The workspace refreshes during the current session after imports and editor changes. A
missing or unreadable badge or Formation image produces a neutral placeholder rather than
hiding the stored record.

An applied pairing is not yet an automatic suitability rating. A defensible calculated
score requires formation positions, roles and team instructions to be extracted into typed
data rather than inferred from screenshot presence alone.

## Requirements and installation

- Python 3.12 or newer
- A desktop environment supported by PySide6
- PaddleOCR and its platform-specific PaddlePaddle runtime

### Conda installation

From the repository root, create and activate the supplied Conda environment:

```bash
conda env create -f fmsatEnvironment.yml
conda activate fmsat
```

The environment installs FMSAT in editable mode with its development and optional `.fmf`
compression dependencies. After changing `fmsatEnvironment.yml` or `pyproject.toml`, update
it with:

```bash
conda env update -f fmsatEnvironment.yml --prune
```

### Standard Python installation

If Conda is unavailable, create a standard virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,compression]"
```

PaddleOCR may require installing the appropriate CPU or GPU `paddlepaddle` build for your
platform after activating the environment. Follow the official PaddlePaddle installation
selector because its command depends on the operating system, processor and CUDA version.
OCR models are downloaded by PaddleOCR on first use.

## Running

```bash
fmsat
```

Alternatively:

```bash
python -m fmsat.app.main
```

To inspect or compare `.fmf` files with the integrated parser toolkit:

```bash
fmsat parser --help
```

Logs rotate at 5 MB and are kept in `logs/application.log` at the repository root.

## Configuration

- `config/screens.yaml` — detection, validation threshold and preprocessing
- `config/regions.yaml` — normalized tactic-name, table and column coordinates
- `config/attributes.yaml` — ordered visible attribute definitions

Coordinates are normalized from zero to one, allowing the same configuration to scale to
different screenshot resolutions. The initial tactic-name region targets the default FM26
skin and must be checked against a representative screenshot. Football Manager skins and
custom views can move names and columns, so tune these YAML files without changing parser
code.

## Project structure

```text
fmsat/
├── app/                 PySide6 entry point and main window
├── cli.py               Integrated .fmf inspection command line
├── config/              Screen, region and attribute YAML
├── core/
│   ├── images/          Composable OpenCV preprocessing
│   ├── ocr/             Replaceable OCR interface and Paddle adapter
│   ├── parser/          Squad Attributes parser and extracted models
│   └── validation/      Confidence and value validation
├── database/            SQLAlchemy models and SQLite gateway
├── documentation/       Design and screenshot documentation
├── parser.py            Existing .fmf parsing implementation
├── samples/             Controlled .fmf samples and local screenshots
└── tests/               Unit tests with mocked OCR
```

## Testing and code quality

From the repository root:

```bash
pytest
ruff check fmsat
black --check fmsat
```

OCR is mocked in unit tests; test execution does not download models.

## Error handling and privacy

Unsupported screens, missing clipboard images, OCR failures and database errors are shown as desktop
messages and written to the rotating log. All screenshots and extracted records stay on
the local machine. The application makes no changes to Football Manager.

## Roadmap

Phase 1 is deliberately extraction-only. The interfaces and historical snapshots provide
a foundation for additional screen parsers and later tactical, role-suitability, squad
depth, recruitment and reporting phases, none of which are implemented here.
