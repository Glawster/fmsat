# Football Manager Squad Assessment Tool

FMSAT is a local desktop application that extracts structured player data from Football
Manager screenshots. Phase 1 supports only the **Squad Attributes** screen. It does not
modify Football Manager, automate it, or read save files.

The package also absorbs the repository's earlier `.fmf` parser. Those inspection and
comparison commands remain available as `fmsat-parser`, while `fmsat` launches the desktop
application.

## Documentation

- [Architecture](docs/architecture.md)
- [Sample screenshot guidance](docs/sampleScreenshots.md)

## Phase 1 workflow

1. Launch FMSAT and select **Import Screenshot** (`Ctrl+I`).
2. Select a recognised tactic or enter a new tactic name.
3. FMSAT lists the screenshots still needed and tells you how to prepare the next screen.
4. Copy the screenshot to the clipboard or save it as PNG/JPEG.
5. FMSAT prefers an image already on the clipboard; otherwise it opens a file picker.
6. Review the spreadsheet-style result. Rows below 95% OCR confidence are highlighted.
7. Correct any cell and select **Save Confirmed Data** (`Ctrl+S`).
8. The confirmed import is stored in `data/fmsat.sqlite3` at the repository root.

When a tactic already has every configured screenshot, FMSAT says that no new capture is
needed. Choose **Use Existing** to stop, or **Update Screenshot** to deliberately import a
newer capture while retaining the previous import history.

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
fmsat-parser --help
```

Logs rotate at 5 MB and are kept in `logs/application.log` at the repository root.

## Configuration

- `config/screens.yaml` — detection, validation threshold and preprocessing
- `config/regions.yaml` — normalized table and column coordinates
- `config/attributes.yaml` — ordered visible attribute definitions

Coordinates are normalized from zero to one, allowing the same configuration to scale to
different screenshot resolutions. Football Manager skins and custom views can move
columns, so tune these YAML files against representative screenshots without changing
parser code.

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
├── docs/                Design and screenshot documentation
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

Unsupported screens, missing files, OCR failures and database errors are shown as desktop
messages and written to the rotating log. All screenshots and extracted records stay on
the local machine. The application makes no changes to Football Manager.

## Roadmap

Phase 1 is deliberately extraction-only. The interfaces and historical snapshots provide
a foundation for additional screen parsers and later tactical, role-suitability, squad
depth, recruitment and reporting phases, none of which are implemented here.
