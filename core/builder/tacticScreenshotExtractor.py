"""Create structured tactic data from already-saved tactic screenshot captures."""

from __future__ import annotations

from dataclasses import dataclass

from fmsat.core.detection import ScreenType
from fmsat.core.ocr import OcrEngine, PaddleOcrEngine
from fmsat.database.models import (
    ScreenshotDerivedTacticDefinition,
    StructuredTacticIssue,
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
    Unsupported extraction coverage is recorded as unresolved issues rather
    than being filled with formation templates or neutral instruction defaults.
    """

    def __init__(self, engine: Engine, ocr: OcrEngine | None = None) -> None:
        self.engine = engine
        self.metadataExtractor = TacticMetadataExtractor(ocr or PaddleOcrEngine())

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

            # Slot and team-instruction extraction is not implemented yet, so
            # screenshot coverage alone cannot make the definition complete.
            complete = False
            metadata, metadataIssues = self._metadataExtract(byType)

            if tactic.structuredDefinition is None:
                definition = ScreenshotDerivedTacticDefinition(
                    confirmed=False,
                    complete=complete,
                    tacticMetadata={
                        "source": "storedScreenshots",
                        **metadata,
                    },
                )
                tactic.structuredDefinition = definition
            else:
                definition = tactic.structuredDefinition
                definition.confirmed = False
                definition.complete = complete
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
            self._coverageIssuesBuild(definition, byType)

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

    def _coverageIssuesBuild(
        self,
        definition: ScreenshotDerivedTacticDefinition,
        byType: dict[ScreenType, TacticScreenshot],
    ) -> None:
        """Record absent screenshots and unsupported extraction as unresolved."""

        for phase, screenType in (
            ("formation", ScreenType.TACTIC_FORMATION),
            ("inPossession", ScreenType.TACTIC_IN_POSSESSION),
            ("outOfPossession", ScreenType.TACTIC_OUT_OF_POSSESSION),
        ):
            if screenType not in byType:
                definition.issues.append(
                    StructuredTacticIssue(
                        code="missingScreenshot",
                        message=f"{phase} screenshot is missing",
                    )
                )
            definition.issues.append(
                StructuredTacticIssue(
                    code="formationSlotExtractionUnresolved",
                    message=(
                        f"{phase} slot extraction is unresolved because its screenshot is missing"
                        if screenType not in byType
                        else f"{phase} slot extraction is not yet available"
                    ),
                )
            )

        for phase, screenType in (
            ("inPossession", ScreenType.TACTIC_IN_POSSESSION),
            ("outOfPossession", ScreenType.TACTIC_OUT_OF_POSSESSION),
        ):
            definition.issues.append(
                StructuredTacticIssue(
                    code="teamInstructionExtractionUnresolved",
                    message=(
                        f"{phase} team-instruction extraction is unresolved because its "
                        "screenshot is missing"
                        if screenType not in byType
                        else f"{phase} team-instruction extraction is not yet available"
                    ),
                )
            )
