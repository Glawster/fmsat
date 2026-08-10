"""FMSAT desktop application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from fmsat.core.logUtils import getLogger
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
    application = QApplication(sys.argv)
    application.setApplicationName("FMSAT")
    application.setOrganizationName("FMSAT")
    try:
        dataPaths = persistentDataPrepare(projectRoot)
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
            ),
            tacticVocabulary,
        )
    except (ConfigurationError, DatabaseError, OSError, PersistentDataError) as exc:
        logger.exception("Application startup failed")
        QMessageBox.critical(None, "FMSAT startup failed", str(exc))
        return 1
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
