# Additional instructions for FMSAT

## Project context

FMSAT is a Python 3.12 desktop application for importing Football Manager tactics and
player screenshots, retaining their provenance, and producing explainable squad
assessments. It also exposes the repository's `.fmf` inspection tools through the
`fmsat parser` command.

The managed guidance in `agent-instructions.md`, `repositoryLayout.md`, and
`requirementsManagement.md` takes precedence. Do not edit managed files directly.

## Environment

- Use the Conda environment declared in `environment.yml` and named `fmsat`.
- Declare Python package dependencies in `pyproject.toml`.
- Install this project in editable mode through the Conda environment.
- Do not create or commit a repository-local `.venv`.

## Source layout

- `app/` contains PySide6 views and application-specific resources.
- `core/` contains UI-independent domain, parsing, OCR, validation, and persistence
  services.
- `database/` contains SQLAlchemy models and database access.
- `config/` contains packaged YAML configuration and factual role knowledge.
- Root parser modules are retained for compatibility with the integrated `.fmf` toolkit.
- `project/` contains requirements, prompts, ADRs, and delivery records.
- `documentation/` contains maintained product and contributor guidance.

## Development checks

Run the checks relevant to the change from the repository root:

```bash
pytest
ruff check .
black --check .
git diff --check
```

For Markdown or release validation, also follow `howToRelease.md`.

## Application constraints

- Keep business logic testable without a running Qt event loop.
- Keep prototype or demonstration data out of production views.
- Store persistent user data below the platform state directory; do not commit real user
  data or screenshots.
- Preserve source screenshots and imported structure unless an explicit, confirmed
  workflow removes them.
- Treat requirements in `project/requirements/features/` as the source of truth for
  scoped feature work and keep their traceability evidence current.
