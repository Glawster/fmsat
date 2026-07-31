# Architecture

FMSAT keeps Qt at the outer edge. `MainWindow` invokes `ScreenshotImportService`, which
coordinates preprocessing, screen detection, OCR and the Squad Attributes parser. The
parser receives an `OcrEngine` interface, so PaddleOCR can be replaced without UI or
database changes.

YAML owns screen regions, preprocessing switches, detection keywords and attribute
definitions. SQLite writes are performed through a transactional SQLAlchemy gateway.
The review table converts OCR output back into core data objects only after user edits.

Phase 1 intentionally reads screenshots only. It neither reads Football Manager save files
nor communicates with or modifies a running Football Manager process.
