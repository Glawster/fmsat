"""FMSAT desktop application entry point."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from fmsat.app.window import MainWindow
from fmsat.core.config import Configuration, ConfigurationError
from fmsat.core.detection import KeywordScreenDetector
from fmsat.core.images import ImagePreprocessor, PreprocessingOptions
from fmsat.core.ocr import PaddleOcrEngine
from fmsat.core.parser import SquadAttributesParser
from fmsat.core.requirements import TacticScreenshotPlanner
from fmsat.core.services import ScreenshotImportService
from fmsat.core.validation import PlayerValidator
from fmsat.database import Database, DatabaseError
from fmsat.loggingConfig import loggingConfigure

logger = logging.getLogger(__name__)


def main() -> int:
    """Create dependencies, initialize storage, and start the Qt event loop."""

    projectRoot = Path(__file__).parents[2]
    loggingConfigure(projectRoot / "logs")
    application = QApplication(sys.argv)
    application.setApplicationName("FMSAT")
    application.setOrganizationName("FMSAT")
    try:
        config = Configuration()
        ocr = PaddleOcrEngine()
        detection = config.screens.get("detection", {})
        detector = KeywordScreenDetector(
            ocr,
            detection.get("squadAttributes", {}).get("keywords", []),
            float(detection.get("minimum_confidence", 0.55)),
        )
        preprocessor = ImagePreprocessor(
            PreprocessingOptions.fromMapping(config.screens.get("preprocessing", {}))
        )
        parser = SquadAttributesParser(ocr, config.regions, config.attributes)
        service = ScreenshotImportService(preprocessor, detector, parser)
        database = Database(projectRoot / "data" / "fmsat.sqlite3")
        database.initialize()
        window = MainWindow(
            service,
            database,
            config.attributes,
            PlayerValidator(config.confidenceThreshold()),
            TacticScreenshotPlanner.fromMapping(config.screens.get("workflow", {})),
        )
    except (ConfigurationError, DatabaseError, OSError) as exc:
        logger.exception("Application startup failed")
        QMessageBox.critical(None, "FMSAT startup failed", str(exc))
        return 1
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
