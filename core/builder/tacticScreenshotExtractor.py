"""Create structured tactic data from already-saved tactic screenshot captures."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2

from fmsat.core.config import Configuration
from fmsat.core.detection import ScreenType
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


@dataclass(frozen=True, slots=True)
class TacticScreenshotExtractResult:
    """Outcome of processing one tactic's stored screenshot captures."""

    tacticName: str
    screenshotCount: int
    structuredCreated: bool
    complete: bool
    message: str


class TacticScreenshotExtractor:
    """Extract structured tactic rows from existing persisted screenshot records.

    Only values directly observed by an implemented extractor are persisted.
    Missing or ambiguous extraction coverage is recorded as unresolved issues
    rather than being filled with formation templates or neutral defaults.
    """

    def __init__(self, engine: Engine, ocr: OcrEngine | None = None) -> None:
        self.engine = engine
        self.ocr = ocr or PaddleOcrEngine()
        configuration = Configuration().tacticExtraction
        vocabulary = TacticVocabulary()
        self.metadataExtractor = TacticMetadataExtractor(self.ocr)
        self.formationExtractor = TacticFormationExtractor(
            self.ocr, vocabulary, configuration
        )
        self.instructionExtractor = TacticInstructionExtractor(
            self.ocr, vocabulary, configuration
        )

    ## tactic

    def tacticExtract(self, tacticName: str) -> TacticScreenshotExtractResult:
        """Create or replace one tactic's structured rows from saved captures."""

        cleanName = tacticName.strip()
        if not cleanName:
            return TacticScreenshotExtractResult(
                tacticName=tacticName,
                screenshotCount=0,
                structuredCreated=False,
                complete=False,
                message="Tactic name is empty",
            )

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
                return TacticScreenshotExtractResult(
                    tacticName=cleanName,
                    screenshotCount=0,
                    structuredCreated=False,
                    complete=False,
                    message="Tactic was not found",
                )

            screenshots = list(tactic.screenshots)
            if not screenshots:
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

            metadata, metadataIssues = self._metadataExtract(byType)

            if tactic.structuredDefinition is None:
                definition = ScreenshotDerivedTacticDefinition(
                    confirmed=False,
                    complete=False,
                    tacticMetadata={
                        "source": "storedScreenshots",
                        **metadata,
                    },
                )
                tactic.structuredDefinition = definition
            else:
                definition = tactic.structuredDefinition
                definition.confirmed = False
                definition.complete = False
                definition.tacticMetadata = {
                    "source": "storedScreenshots",
                    **metadata,
                }
                # Clear persisted child rows and flush orphan deletions before
                # re-adding replacement rows with the same unique keys.
                definition.slots.clear()
                definition.instructions.clear()
                definition.issues.clear()
                session.flush()

            for message in metadataIssues:
                definition.issues.append(
                    StructuredTacticIssue(
                        code="metadataExtractionIncomplete",
                        message=message,
                    )
                )
            self._formationBuild(definition, byType)
            self._instructionsBuild(definition, byType)
            complete = self._completeCalculate(definition)
            definition.complete = complete

        return TacticScreenshotExtractResult(
            tacticName=cleanName,
            screenshotCount=len(screenshots),
            structuredCreated=True,
            complete=complete,
            message="Observed tactic data extracted with unresolved coverage",
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
        for slot in result.slots:
            definition.slots.append(StructuredFormationSlot(
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
            ))
        for issue in result.issues:
            self._issueAdd(definition, issue.code, issue.message, issue.observedText)

    def _instructionsBuild(
        self,
        definition: ScreenshotDerivedTacticDefinition,
        byType: dict[ScreenType, TacticScreenshot],
    ) -> None:
        """Extract only visually selected values from each instruction capture."""

        for phase, screenType in (
            (TacticalPhase.IN_POSSESSION, ScreenType.TACTIC_IN_POSSESSION),
            (TacticalPhase.OUT_OF_POSSESSION, ScreenType.TACTIC_OUT_OF_POSSESSION),
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
                continue
            result = self.instructionExtractor.instructionsExtract(
                image, phase, screenshot.importSession.imageFilename
            )
            for instruction in result.instructions:
                definition.instructions.append(StructuredTeamInstruction(
                    phase=instruction.phase.value,
                    category=instruction.category,
                    canonicalValue=instruction.value,
                    displayValue=instruction.displayValue,
                    confidence=instruction.confidence,
                    sourceImportSession=screenshot.importSession,
                    validationState=instruction.validationState.value,
                ))
            for issue in result.issues:
                self._issueAdd(definition, issue.code, issue.message, issue.observedText)

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
            "unresolvedRole",
            "unresolvedDuty",
            "ambiguousPhaseLink",
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
    def _issueAdd(definition, code: str, message: str, observedText: str | None = None) -> None:
        definition.issues.append(StructuredTacticIssue(
            code=code, message=message, observedText=observedText
        ))
