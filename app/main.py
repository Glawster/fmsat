"""FMSAT desktop application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from fmsat.core.logUtils import getApplicationLogDir, getLogger
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMessageBox

from fmsat.app.roleAssessmentWeightEditor import RoleAssessmentWeightEditor
from fmsat.app.styles import styleSheetLoad
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
from fmsat.core.roleAssessmentIntegrity import roleAssessmentIntegrityCheck
from fmsat.core.roleAssessmentPolicy import RoleAssessmentPolicyService
from fmsat.core.roleKnowledge import RoleKnowledgeService
from fmsat.core.screenshotStore import ScreenshotStore
from fmsat.core.services import ScreenshotImportService
from fmsat.core.validation import PlayerValidator
from fmsat.database import Database, DatabaseError

logger = getLogger()


def _weightsViewConfigure(
    window: MainWindow,
    policyService: RoleAssessmentPolicyService,
    config: Configuration,
    tacticVocabulary: TacticVocabulary,
    roleKnowledgeService: RoleKnowledgeService,
    squadParser: SquadAttributesParser,
    roleProfileParser: RoleProfileParser,
) -> QAction:
    """Create and position View -> Weights in the application shell."""

    def attributesChanged(updated) -> None:  # type: ignore[no-untyped-def]
        """Apply header activation changes to subsequent capture and UI construction."""

        config.attributes = tuple(updated)
        active = tuple(attribute for attribute in updated if attribute.active)
        squadParser.attributes = active
        roleProfileParser.attributes = active
        window.attributes = active
        window.squadDetailView.attributes = active
        window.statusBar().showMessage(
            "Attribute participation updated. Existing captured values are retained; "
            "reassess or capture fresh evidence where required.",
            10000,
        )

    def weightsShow() -> None:
        try:
            currentAttributes = config.attributeService.definitionsLoad()
        except ConfigurationError:
            currentAttributes = config.attributes
        dialog = RoleAssessmentWeightEditor(
            policyService,
            roles=tacticVocabulary.roles,
            attributes=currentAttributes,
            roleKnowledge=roleKnowledgeService,
            attributeService=config.attributeService,
            roleOpen=window.roleShow,
            attributesChanged=attributesChanged,
            parent=window,
        )
        dialog.exec()

    action = QAction("Weights", window)
    action.triggered.connect(weightsShow)

    # Prefer the menu object owned by the shell itself. This also avoids creating
    # short-lived PySide wrappers for a QMenu that is already owned by MainWindow.
    viewMenu = getattr(window, "viewMenu", None)
    if viewMenu is None:
        for menuAction in window.menuBar().actions():
            candidate = menuAction.menu()
            if candidate is not None and candidate.title().replace("&", "").casefold() == "view":
                viewMenu = candidate
                break
    if viewMenu is None:
        raise RuntimeError("Main window has no View menu")

    # Menu order is deliberately owned here by the application shell, not by
    # the weights feature. Keep Weights with the data views, immediately before Settings.
    viewMenu.insertAction(window.settingsAction, action)
    window.weightsAction = action
    return action


def main() -> int:
    """Create dependencies, initialize storage, and start the Qt event loop."""

    projectRoot = Path(__file__).parents[2]
    logger.doing("starting fmsat desktop application")
    logger.value("application log directory", getApplicationLogDir())
    logger.value("project root", projectRoot)
    application = QApplication(sys.argv)
    application.setApplicationName("FMSAT")
    application.setOrganizationName("FMSAT")
    application.setStyleSheet(styleSheetLoad())
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
        # Attribute activation controls whether an FM attribute participates in normal
        # capture/presentation. Inactive definitions remain configured so role policy is
        # retained and can be re-enabled from View -> Weights.
        squadParser = SquadAttributesParser(ocr, config.regions, config.activeAttributes)
        tacticParser = TacticParser(ocr, config.regions)
        tacticVocabulary = TacticVocabulary()
        roleProfileParser = RoleProfileParser(ocr, tacticVocabulary, config.activeAttributes)
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
        roleKnowledgeService = RoleKnowledgeService(
            dataPaths.directory / "knowledge" / "roles",
            tacticVocabulary,
            {attribute.name for attribute in config.attributes},
            config.roleAssessmentWeights(),
            config.roleAssessmentSettings(),
        )
        roleVocabularyGaps = tacticVocabulary.canonicalRoleDefinitionGaps(
            roleKnowledgeService.definitionsList()
        )
        if roleVocabularyGaps:
            logger.warning(
                "ocr-confirmed role definitions absent from tacticalVocabulary.yaml: "
                f"{', '.join(roleVocabularyGaps)}"
            )
        else:
            logger.info("ocr-confirmed role definitions are represented in tacticalVocabulary.yaml")
        window = MainWindow(
            service,
            database,
            config.activeAttributes,
            PlayerValidator(config.confidenceThreshold()),
            TacticScreenshotPlanner.fromMapping(config.screens.get("workflow", {})),
            ScreenshotStore(dataPaths.screenshots),
            roleKnowledgeService,
            tacticVocabulary,
        )

        policyService = RoleAssessmentPolicyService(
            config.directory / "roleAssessment.yaml",
            set(tacticVocabulary.roles),
            {attribute.name for attribute in config.attributes},
        )
        _weightsViewConfigure(
            window,
            policyService,
            config,
            tacticVocabulary,
            roleKnowledgeService,
            squadParser,
            roleProfileParser,
        )

        integrity = roleAssessmentIntegrityCheck(tacticVocabulary, roleKnowledgeService)
        integrityText = integrity.text()
        window.statusHistory.insert(0, integrityText)
        logger.multiline(integrityText)
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