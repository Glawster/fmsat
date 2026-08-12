"""Create structured tactic data from already-saved tactic screenshot captures."""

from __future__ import annotations

from dataclasses import dataclass

from fmsat.core.detection import ScreenType
from fmsat.core.parser import TacticVocabulary
from fmsat.database.models import (
    StructuredFormationSlot,
    StructuredTacticDefinition,
    StructuredTacticIssue,
    StructuredTeamInstruction,
    Tactic,
    TacticScreenshot,
)
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, selectinload


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

    This implementation intentionally uses deterministic template fallback data
    so existing screenshot-only tactics can be promoted into the structured
    model pipeline without requiring re-capture.
    """

    _FORMATION_TEMPLATE = (
        ("01", "GK", "goalkeeper", "defend", 0.50, 0.90),
        ("02", "WBL", "wingBack", "support", 0.14, 0.66),
        ("03", "DC", "centreBack", "defend", 0.40, 0.74),
        ("04", "DC", "centreBack", "defend", 0.60, 0.74),
        ("05", "WBR", "wingBack", "support", 0.86, 0.66),
        ("06", "DM", "defensiveMidfielder", "defend", 0.50, 0.55),
        ("07", "MC", "centralMidfielder", "support", 0.40, 0.47),
        ("08", "MC", "centralMidfielder", "support", 0.60, 0.47),
        ("09", "AML", "insideForward", "support", 0.22, 0.30),
        ("10", "AMR", "insideForward", "support", 0.78, 0.30),
        ("11", "ST", "centreForward", "attack", 0.50, 0.12),
    )

    _OUT_OF_POSSESSION_TEMPLATE = (
        ("01", "GK", "goalkeeper", "defend", 0.50, 0.91),
        ("02", "DL", "wingBack", "support", 0.18, 0.73),
        ("03", "DC", "centreBack", "defend", 0.40, 0.75),
        ("04", "DC", "centreBack", "defend", 0.60, 0.75),
        ("05", "DR", "wingBack", "support", 0.82, 0.73),
        ("06", "ML", "winger", "support", 0.24, 0.50),
        ("07", "MC", "centralMidfielder", "support", 0.44, 0.52),
        ("08", "MC", "centralMidfielder", "support", 0.56, 0.52),
        ("09", "MR", "winger", "support", 0.76, 0.50),
        ("10", "AMC", "attackingMidfielder", "support", 0.50, 0.34),
        ("11", "ST", "centreForward", "attack", 0.50, 0.14),
    )

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.vocabulary = TacticVocabulary()

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
                        StructuredTacticDefinition.slots
                    ),
                    selectinload(Tactic.structuredDefinition).selectinload(
                        StructuredTacticDefinition.instructions
                    ),
                    selectinload(Tactic.structuredDefinition).selectinload(
                        StructuredTacticDefinition.issues
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

            required = {
                ScreenType.TACTIC_FORMATION,
                ScreenType.TACTIC_IN_POSSESSION,
                ScreenType.TACTIC_OUT_OF_POSSESSION,
            }
            complete = required.issubset(byType.keys())

            if tactic.structuredDefinition is None:
                definition = StructuredTacticDefinition(
                    confirmed=False,
                    complete=complete,
                    tacticMetadata={
                        "inPossessionName": "inPossession",
                        "outOfPossessionName": "outOfPossession",
                        "source": "storedScreenshots",
                    },
                )
                tactic.structuredDefinition = definition
            else:
                definition = tactic.structuredDefinition
                definition.confirmed = False
                definition.complete = complete
                definition.tacticMetadata = {
                    "inPossessionName": "inPossession",
                    "outOfPossessionName": "outOfPossession",
                    "source": "storedScreenshots",
                }
                # Clear persisted child rows and flush orphan deletions before
                # re-adding replacement rows with the same unique keys.
                definition.slots.clear()
                definition.instructions.clear()
                definition.issues.clear()
                session.flush()

            self._slotsBuild(definition, byType)
            self._instructionsBuild(definition, byType)
            definition.issues.append(
                StructuredTacticIssue(
                    code="templateExtraction",
                    message=(
                        "Structured rows were generated from stored captures using "
                        "template fallback extraction."
                    ),
                )
            )

        return TacticScreenshotExtractResult(
            tacticName=cleanName,
            screenshotCount=len(screenshots),
            structuredCreated=True,
            complete=complete,
            message="Structured tactic data generated from stored captures",
        )

    ## instructions

    def _instructionsBuild(
        self,
        definition: StructuredTacticDefinition,
        byType: dict[ScreenType, TacticScreenshot],
    ) -> None:
        """Generate stable fallback in/out-of-possession instruction rows."""

        for phase, screenType in (
            ("inPossession", ScreenType.TACTIC_IN_POSSESSION),
            ("outOfPossession", ScreenType.TACTIC_OUT_OF_POSSESSION),
        ):
            source = byType.get(screenType)
            sourceImport = source.importSession if source is not None else None
            categories = self.vocabulary.instructions.get(phase, {})
            for category, aliases in categories.items():
                canonical = self._defaultCanonicalValue(aliases)
                value = self._canonicalValueParse(canonical)
                definition.instructions.append(
                    StructuredTeamInstruction(
                        phase=phase,
                        category=category,
                        canonicalValue=value,
                        displayValue=str(canonical),
                        confidence=0.30,
                        sourceImportSession=sourceImport,
                        validationState="extracted",
                    )
                )

    @staticmethod
    def _canonicalValueParse(value: str) -> str | bool:
        lowered = value.strip().casefold()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        return value

    @staticmethod
    def _defaultCanonicalValue(aliases: dict[str, str]) -> str:
        """Prefer neutral defaults where possible, otherwise use first canonical."""

        canonicalValues = sorted(set(aliases.values()), key=str.casefold)
        for candidate in canonicalValues:
            if candidate.casefold() == "standard":
                return candidate
        for candidate in canonicalValues:
            if candidate.casefold() == "false":
                return candidate
        return canonicalValues[0] if canonicalValues else "standard"

    ## slots

    def _slotsBuild(
        self,
        definition: StructuredTacticDefinition,
        byType: dict[ScreenType, TacticScreenshot],
    ) -> None:
        """Generate fallback slots for formation and both tactical phases."""

        for phase, screenType, template in (
            ("formation", ScreenType.TACTIC_FORMATION, self._FORMATION_TEMPLATE),
            ("inPossession", ScreenType.TACTIC_IN_POSSESSION, self._FORMATION_TEMPLATE),
            (
                "outOfPossession",
                ScreenType.TACTIC_OUT_OF_POSSESSION,
                self._OUT_OF_POSSESSION_TEMPLATE,
            ),
        ):
            source = byType.get(screenType)
            sourceImport = source.importSession if source is not None else None
            for slotId, position, role, duty, x, y in template:
                definition.slots.append(
                    StructuredFormationSlot(
                        slotId=f"{phase}-{slotId}",
                        phase=phase,
                        position=position,
                        role=role,
                        duty=duty,
                        x=x,
                        y=y,
                        observedRole=role,
                        confidence=0.30,
                        sourceImportSession=sourceImport,
                        validationState="extracted",
                    )
                )
