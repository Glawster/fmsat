"""Create structured tactic data from already-saved tactic screenshot captures."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import cv2

from fmsat.core.config import Configuration
from fmsat.core.detection import ScreenType
from fmsat.core.logUtils import getLogger
from fmsat.core.ocr import OcrEngine, PaddleOcrEngine
from fmsat.core.parser import (
    TacticalPhase,
    TacticFormationExtractor,
    TacticInstructionExtractor,
    TacticVocabulary,
)
from fmsat.database.models import (
    ScreenshotDerivedTacticDefinition,
    StructuredFormationSlot,
    StructuredTacticIssue,
    StructuredTeamInstruction,
    Tactic,
    TacticScreenshot,
)
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, selectinload

from .tacticMetadataExtractor import TacticMetadataExtractor

logger = getLogger()


@dataclass(frozen=True, slots=True)
class TacticScreenshotExtractResult:
    """Outcome of processing one tactic's stored screenshot captures."""

    tacticName: str
    screenshotCount: int
    structuredCreated: bool
    complete: bool
    message: str
    diagnosticPaths: tuple[str, ...] = ()
    unresolvedRoles: tuple[str, ...] = ()


class TacticScreenshotExtractor:
    """Extract structured tactic rows from existing persisted screenshot records.

    Only values directly observed by an implemented extractor are persisted.
    Missing or ambiguous extraction coverage is recorded as unresolved issues
    rather than being filled with formation templates or neutral defaults.
    """

    def __init__(
        self,
        engine: Engine,
        ocr: OcrEngine | None = None,
        roleDefinitionsProvider: Callable[[], Iterable[object]] | None = None,
    ) -> None:
        self.engine = engine
        self.ocr = ocr or PaddleOcrEngine()
        self.roleDefinitionsProvider = roleDefinitionsProvider
        configuration = Configuration().tacticExtraction
        self.vocabulary = TacticVocabulary()
        self.metadataExtractor = TacticMetadataExtractor(self.ocr)
        self.formationExtractor = TacticFormationExtractor(self.ocr, self.vocabulary, configuration)
        self.instructionExtractor = TacticInstructionExtractor(
            self.ocr, self.vocabulary, configuration
        )

    ## tactic

    def tacticExtract(
        self,
        tacticName: str,
        progressCallback: Callable[[int, int, str], None] | None = None,
    ) -> TacticScreenshotExtractResult:
        """Create or replace one tactic's structured rows from saved captures."""

        cleanName = tacticName.strip()
        logger.doing(f"extracting tactic screenshots for {cleanName or '<empty>'}")
        self._capturedRolesRefresh()
        if not cleanName:
            logger.info("tactic extraction stopped because the name is empty")
            return TacticScreenshotExtractResult(
                tacticName=tacticName,
                screenshotCount=0,
                structuredCreated=False,
                complete=False,
                message="Tactic name is empty",
            )

        diagnosticPaths: list[str] = []
        with Session(self.engine) as session, session.begin():
            tactic = session.scalar(
                select(Tactic)
                .where(Tactic.normalizedName == cleanName.casefold())
                .options(
                    selectinload(Tactic.screenshots).selectinload(TacticScreenshot.importSession),
                    selectinload(Tactic.structuredDefinition).selectinload(
                        ScreenshotDerivedTacticDefinition.slots
                    ),
                    selectinload(Tactic.structuredDefinition).selectinload(
                        ScreenshotDerivedTacticDefinition.instructions
                    ),
                    selectinload(Tactic.structuredDefinition).selectinload(
                        ScreenshotDerivedTacticDefinition.issues
                    ),
                )
            )
            if tactic is None:
                logger.info(f"tactic extraction stopped because {cleanName} was not found")
                return TacticScreenshotExtractResult(
                    tacticName=cleanName,
                    screenshotCount=0,
                    structuredCreated=False,
                    complete=False,
                    message="Tactic was not found",
                )

            screenshots = list(tactic.screenshots)
            logger.value("saved tactic screenshots", len(screenshots))
            if not screenshots:
                logger.info(f"tactic extraction stopped because {tactic.name} has no captures")
                return TacticScreenshotExtractResult(
                    tacticName=tactic.name,
                    screenshotCount=0,
                    structuredCreated=False,
                    complete=False,
                    message="No saved tactic screenshots were found",
                )

            byType: dict[ScreenType, TacticScreenshot] = {}
            for screenshot in sorted(
                screenshots,
                key=lambda row: (row.importSession.date, row.importSession.id),
            ):
                if screenshot.screenType in ScreenType._value2member_map_:
                    byType[ScreenType(screenshot.screenType)] = screenshot

            extractionStages = (
                ("formation metadata", ScreenType.TACTIC_FORMATION),
                ("Formation", ScreenType.TACTIC_FORMATION),
                ("In Possession", ScreenType.TACTIC_IN_POSSESSION),
                ("Out of Possession", ScreenType.TACTIC_OUT_OF_POSSESSION),
            )
            availableStages = tuple(
                (label, screenType)
                for label, screenType in extractionStages
                if screenType in byType
            )
            totalStages = len(availableStages)
            completedStages = 0

            metadata, metadataIssues = self._metadataExtract(byType)
            if ScreenType.TACTIC_FORMATION in byType:
                completedStages += 1
                if progressCallback is not None:
                    progressCallback(
                        completedStages,
                        totalStages,
                        "Extracted saved tactic formation metadata.",
                    )
            logger.value("extracted tactic metadata fields", len(metadata))
            logger.value("tactic metadata issues", len(metadataIssues))

            if tactic.structuredDefinition is None:
                definition = ScreenshotDerivedTacticDefinition(
                    confirmed=False,
                    complete=False,
                    tacticMetadata={"source": "storedScreenshots", **metadata},
                )
                tactic.structuredDefinition = definition
            else:
                definition = tactic.structuredDefinition
                definition.confirmed = False
                definition.complete = False
                definition.tacticMetadata = {"source": "storedScreenshots", **metadata}
                definition.slots.clear()
                definition.instructions.clear()
                definition.issues.clear()
                session.flush()

            for message in metadataIssues:
                definition.issues.append(
                    StructuredTacticIssue(code="metadataExtractionIncomplete", message=message)
                )
            self._formationBuild(definition, byType, diagnosticPaths)
            if ScreenType.TACTIC_FORMATION in byType:
                completedStages += 1
                if progressCallback is not None:
                    progressCallback(
                        completedStages,
                        totalStages,
                        "Extracted Formation evidence.",
                    )
            logger.value("extracted formation slots", len(definition.slots))
            self._instructionsBuild(
                definition,
                byType,
                diagnosticPaths,
                progressCallback,
                completedStages,
                totalStages,
            )
            logger.value("extracted team instructions", len(definition.instructions))
            complete = self._completeCalculate(definition)
            definition.complete = complete
            unresolvedRoles = tuple(
                sorted(
                    {
                        slot.observedRole
                        for slot in definition.slots
                        if slot.observedRole and not slot.role
                    }
                )
            )
            logger.value("tactic extraction issues", len(definition.issues))
            logger.value("tactic extraction complete", complete)

        logger.done(f"tactic screenshot extraction finished for {cleanName}")
        return TacticScreenshotExtractResult(
            tacticName=cleanName,
            screenshotCount=len(screenshots),
            structuredCreated=True,
            complete=complete,
            message="Observed tactic data extracted with unresolved coverage",
            diagnosticPaths=tuple(diagnosticPaths),
            unresolvedRoles=unresolvedRoles,
        )

    def _capturedRolesRefresh(self) -> None:
        """Refresh OCR aliases from confirmed user role definitions."""

        packagedTam = self.vocabulary.roleNormalize("TAM")
        logger.info(
            "role refresh pre-check: "
            f"TAM={packagedTam.value!r} resolved={packagedTam.resolved} "
            f"catalogueRoles={len(self.vocabulary.roles)}"
        )
        if self.roleDefinitionsProvider is None:
            logger.info("role refresh has no captured-role provider")
            return
        try:
            definitions = tuple(self.roleDefinitionsProvider())
        except TypeError:
            logger.warning("captured role provider did not return an iterable")
            return
        for definition in definitions:
            logger.info(
                "captured role definition: "
                f"code={getattr(definition, 'roleCode', None)!r} "
                f"display={getattr(definition, 'displayName', None)!r} "
                f"abbreviations={getattr(definition, 'abbreviations', ())!r}"
            )
        self.vocabulary.capturedRolesAdd(definitions)
        logger.value("captured role definitions available to OCR", len(definitions))
        refreshedTam = self.vocabulary.roleNormalize("TAM")
        logger.info(
            "role refresh post-check: "
            f"TAM={refreshedTam.value!r} resolved={refreshedTam.resolved} "
            f"catalogueRoles={len(self.vocabulary.roles)}"
        )

    ## metadata

    def _metadataExtract(
        self,
        byType: dict[ScreenType, TacticScreenshot],
    ) -> tuple[dict[str, str], tuple[str, ...]]:
        """Extract tactic header values from the latest Formation capture."""

        formation = byType.get(ScreenType.TACTIC_FORMATION)
        if formation is None:
            return {}, ("Formation screenshot is missing",)
        result = self.metadataExtractor.metadataExtract(formation.importSession.imageFilename)
        return result.metadata, result.issues

    ## extraction coverage

    def _formationBuild(
        self,
        definition: ScreenshotDerivedTacticDefinition,
        byType: dict[ScreenType, TacticScreenshot],
        diagnosticPaths: list[str],
    ) -> None:
        """Detect both phase pitches from the Formation capture."""

        screenshot = byType.get(ScreenType.TACTIC_FORMATION)
        if screenshot is None:
            self._issueAdd(definition, "missingScreenshot", "Formation screenshot is missing")
            return
        image = self._imageRead(screenshot.importSession.imageFilename)
        if image is None:
            self._issueAdd(
                definition,
                "formationImageUnavailable",
                "Formation screenshot could not be decoded",
            )
            return
        result = self.formationExtractor.formationExtract(
            image, screenshot.importSession.imageFilename
        )
        diagnosticPath = self._diagnosticSave(
            result.diagnosticImage,
            screenshot.importSession.imageFilename,
            "formation",
        )
        if diagnosticPath:
            diagnosticPaths.append(diagnosticPath)
        logger.value("formation extractor slots", len(result.slots))
        logger.value("formation extractor issues", len(result.issues))
        for slot in result.slots:
            if slot.observedRole or slot.role:
                logger.info(
                    "formation role resolution: "
                    f"phase={slot.phase.value} slot={slot.slotId!r} "
                    f"position={slot.position!r} observed={slot.observedRole!r} "
                    f"canonical={slot.role!r}"
                )
            definition.slots.append(
                StructuredFormationSlot(
                    slotId=slot.slotId,
                    phase=slot.phase.value,
                    position=slot.position,
                    role=slot.role,
                    duty=slot.duty,
                    x=slot.x,
                    y=slot.y,
                    observedRole=slot.observedRole,
                    displayedPlayer=slot.displayedPlayer,
                    confidence=slot.confidence,
                    sourceImportSession=screenshot.importSession,
                    validationState=slot.validationState.value,
                )
            )
        for issue in result.issues:
            # Player names/numbers shown by FM are incidental screenshot
            # evidence, not tactic identity. Duplicate player OCR must never
            # invalidate a tactic or require review; spatial slot linkage is
            # the player-agnostic evidence used by the tactic model.
            if issue.code == "ambiguousPhaseLink":
                logger.info(f"ignoring player-specific phase-link evidence: {issue.message}")
                continue
            self._issueAdd(definition, issue.code, issue.message, issue.observedText)

    def _instructionsBuild(
        self,
        definition: ScreenshotDerivedTacticDefinition,
        byType: dict[ScreenType, TacticScreenshot],
        diagnosticPaths: list[str],
        progressCallback: Callable[[int, int, str], None] | None = None,
        completedStages: int = 0,
        totalStages: int = 0,
    ) -> None:
        """Extract only visually selected values from each instruction capture."""

        for phase, screenType, phaseLabel in (
            (
                TacticalPhase.IN_POSSESSION,
                ScreenType.TACTIC_IN_POSSESSION,
                "In Possession",
            ),
            (
                TacticalPhase.OUT_OF_POSSESSION,
                ScreenType.TACTIC_OUT_OF_POSSESSION,
                "Out Of Possession",
            ),
        ):
            screenshot = byType.get(screenType)
            if screenshot is None:
                self._issueAdd(
                    definition,
                    "missingScreenshot",
                    f"{phase.value} screenshot is missing",
                )
                continue
            image = self._imageRead(screenshot.importSession.imageFilename)
            if image is None:
                self._issueAdd(
                    definition,
                    "instructionImageUnavailable",
                    f"{phase.value} screenshot could not be decoded",
                )
                completedStages += 1
                if progressCallback is not None:
                    progressCallback(
                        completedStages,
                        totalStages,
                        f"Extracted {phaseLabel} evidence.",
                    )
                continue
            result = self.instructionExtractor.instructionsExtract(
                image, phase, screenshot.importSession.imageFilename
            )
            diagnosticPath = self._diagnosticSave(
                result.diagnosticImage,
                screenshot.importSession.imageFilename,
                phase.value,
            )
            if diagnosticPath:
                diagnosticPaths.append(diagnosticPath)
            logger.info(
                f"{phase.value} instruction result: {len(result.instructions)} values, "
                f"{len(result.issues)} issues"
            )
            for instruction in result.instructions:
                definition.instructions.append(
                    StructuredTeamInstruction(
                        phase=instruction.phase.value,
                        category=instruction.category,
                        canonicalValue=instruction.value,
                        displayValue=instruction.displayValue,
                        confidence=instruction.confidence,
                        sourceImportSession=screenshot.importSession,
                        validationState=instruction.validationState.value,
                    )
                )
            for issue in result.issues:
                self._issueAdd(definition, issue.code, issue.message, issue.observedText)
            completedStages += 1
            if progressCallback is not None:
                progressCallback(
                    completedStages,
                    totalStages,
                    f"Extracted {phaseLabel} evidence.",
                )

    @staticmethod
    def _completeCalculate(definition: ScreenshotDerivedTacticDefinition) -> bool:
        phaseCounts = {
            phase: sum(slot.phase == phase for slot in definition.slots)
            for phase in ("inPossession", "outOfPossession")
        }
        blockingCodes = {
            "metadataExtractionIncomplete",
            "missingScreenshot",
            "formationImageUnavailable",
            "instructionImageUnavailable",
            "missingPitchRegion",
            "emptyPitchRegion",
            "missingFormationSlots",
            "formationTileOcrFailed",
            "unresolvedPosition",
            "uncertainPhaseLink",
            "unmatchedPhaseSlot",
            "missingInstructionEvidence",
            "ambiguousInstructionEvidence",
            "unknownInstructionValue",
            "instructionOcrFailed",
            "missingInstructionConfiguration",
            "emptyInstructionRegion",
        }
        return all(count == 11 for count in phaseCounts.values()) and not any(
            issue.code in blockingCodes for issue in definition.issues
        )

    @staticmethod
    def _imageRead(filename: str):
        path = Path(filename).expanduser()
        return cv2.imread(str(path), cv2.IMREAD_COLOR) if path.is_file() else None

    @staticmethod
    def _diagnosticSave(
        image,
        sourceFilename: str,
        phase: str,
    ) -> str | None:
        """Persist the latest annotated OCR reference beside its retained capture."""

        if image is None:
            return None
        source = Path(sourceFilename).expanduser()
        directory = source.parent / "ocr-diagnostics"
        path = directory / f"{source.stem}-{phase}-ocr-zones.png"
        try:
            directory.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(path), image):
                raise OSError("OpenCV did not encode the diagnostic image")
        except (OSError, cv2.error):
            logger.exception(f"unable to save OCR diagnostic image {path}")
            return None
        logger.info(f"saved OCR diagnostic image: {path}")
        return str(path)

    @staticmethod
    def _issueAdd(definition, code: str, message: str, observedText: str | None = None) -> None:
        logger.info(
            f"tactic extraction issue {code}: {message}"
            + (f"; observed={observedText}" if observedText else "")
        )
        definition.issues.append(
            StructuredTacticIssue(code=code, message=message, observedText=observedText)
        )
