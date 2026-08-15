"""FMSAT desktop application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from fmsat.core.logUtils import getApplicationLogDir, getLogger
from PySide6.QtWidgets import QApplication, QMessageBox

from fmsat.app.window import MainWindow
from fmsat.core.config import Configuration, ConfigurationError
from fmsat.core.dataPaths import PersistentDataError, persistentDataPrepare
from fmsat.core.detection import KeywordScreenDetector, ScreenType
from fmsat.core.images import ImagePreprocessor, PreprocessingOptions
from fmsat.core.ocr import PaddleOcrEngine
from fmsat.core.parser import (
    RoleProfileParser,
    SquadAttributesParser,
    TacticParser,
    TacticVocabulary,
)
from fmsat.core.requirements import TacticScreenshotPlanner
from fmsat.core.roleKnowledge import RoleKnowledgeService
from fmsat.core.screenshotStore import ScreenshotStore
from fmsat.core.services import ScreenshotImportService
from fmsat.core.validation import PlayerValidator
from fmsat.database import Database, DatabaseError

logger = getLogger()


def main() -> int:
    """Create dependencies, initialize storage, and start the Qt event loop."""

    projectRoot = Path(__file__).parents[2]
    logger.doing("starting fmsat desktop application")
    logger.value("application log directory", getApplicationLogDir())
    logger.value("project root", projectRoot)
    application = QApplication(sys.argv)
    application.setApplicationName("FMSAT")
    application.setOrganizationName("FMSAT")
    try:
        dataPaths = persistentDataPrepare(projectRoot)
        logger.value("persistent data directory", dataPaths.directory)
        logger.value("database", dataPaths.database)
        config = Configuration()
        ocr = PaddleOcrEngine()
        detection = config.screens.get("detection", {})
        keywordGroups = {
            ScreenType.TACTIC_FORMATION: detection.get("tacticFormation", {}).get("keywords", []),
            ScreenType.TACTIC_IN_POSSESSION: detection.get("tacticInPossession", {}).get(
                "keywords", []
            ),
            ScreenType.TACTIC_OUT_OF_POSSESSION: detection.get("tacticOutOfPossession", {}).get(
                "keywords", []
            ),
            ScreenType.ROLE_PROFILE: detection.get("roleProfile", {}).get("keywords", []),
            ScreenType.SQUAD_ATTRIBUTES: detection.get("squadAttributes", {}).get("keywords", []),
        }
        detector = KeywordScreenDetector(
            ocr, keywordGroups, float(detection.get("minimum_confidence", 0.55))
        )
        preprocessor = ImagePreprocessor(
            PreprocessingOptions.fromMapping(config.screens.get("preprocessing", {}))
        )
        # Screenshot OCR matches Football Manager's canonical attribute headings.
        # FMSAT abbreviations remain presentation-only labels in the Players tab.
        squadParser = SquadAttributesParser(ocr, config.regions, config.attributes)
        tacticParser = TacticParser(ocr, config.regions)
        tacticVocabulary = TacticVocabulary()
        roleProfileParser = RoleProfileParser(ocr, tacticVocabulary, config.attributes)
        service = ScreenshotImportService(
            preprocessor,
            detector,
            squadParser,
            tacticParser,
            roleProfileParser,
        )
        database = Database(dataPaths.database)
        database.initialize()
        logger.done("database initialized")
        window = MainWindow(
            service,
            database,
            config.attributes,
            PlayerValidator(config.confidenceThreshold()),
            TacticScreenshotPlanner.fromMapping(config.screens.get("workflow", {})),
            ScreenshotStore(dataPaths.screenshots),
            RoleKnowledgeService(
                dataPaths.directory / "knowledge" / "roles",
                tacticVocabulary,
                {attribute.name for attribute in config.attributes},
                config.roleAssessmentWeights(),
                config.roleAssessmentSettings(),
            ),
            tacticVocabulary,
        )
    except (ConfigurationError, DatabaseError, OSError, PersistentDataError) as exc:
        logger.exception("Application startup failed")
        QMessageBox.critical(None, "FMSAT startup failed", str(exc))
        return 1
    window.show()
    logger.done("fmsat desktop window shown")
    exitCode = application.exec()
    logger.value("fmsat desktop exit code", exitCode)
    return exitCode


if __name__ == "__main__":
    raise SystemExit(main())
