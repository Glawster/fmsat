"""Rebuild squad object-model data from retained screenshot evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from fmsat.core.detection import ScreenType
from fmsat.core.logUtils import getLogger
from fmsat.core.services import ScreenshotImportService, squadCapturesMerge
from fmsat.core.squadModel import SquadModel, SquadModelService
from fmsat.database.models import (
    ObjectModelPlayer,
    ObjectModelPlayerAttribute,
    ObjectModelPlayerTrait,
    ObjectModelSquad,
    Squad,
    SquadScreenshot,
)
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, selectinload

logger = getLogger()


@dataclass(frozen=True, slots=True)
class SquadRegenerationResult:
    """Outcome and evidence counts for one screenshot-driven rebuild."""

    model: SquadModel
    screenshots: int
    players: int


class SquadScreenshotRegenerator:
    """Mirror tactic regeneration by rerunning current OCR over saved squad captures."""

    def __init__(self, engine: Engine, importService: ScreenshotImportService) -> None:
        self.engine = engine
        self.importService = importService

    def regenerate(self, squadName: str) -> SquadRegenerationResult:
        """Re-OCR every retained squad screenshot and replace derived model facts."""

        cleanName = squadName.strip()
        if not cleanName:
            raise ValueError("Squad name is required")
        logger.doing(f"regenerating squad model from saved screenshots: {cleanName}")
        captures = self._capturesLoad(cleanName)
        if not captures:
            raise ValueError(f"No saved squad screenshots exist for {cleanName}")
        logger.value("squad regeneration screenshots", len(captures))

        merged = None
        for index, (_importId, filename) in enumerate(captures, start=1):
            logger.info(
                "squad regeneration OCR %d/%d: %s",
                index,
                len(captures),
                filename,
            )
            path = Path(filename)
            if not path.exists():
                raise ValueError(f"Saved squad screenshot is missing: {filename}")
            result = self.importService.fileImport(path, ScreenType.SQUAD_ATTRIBUTES)
            merged = result if merged is None else squadCapturesMerge(merged, result)

        if merged is None or not merged.players:
            raise ValueError("Squad regeneration produced no player rows")
        logger.value("squad regeneration OCR players", len(merged.players))
        if merged.mergeConflicts:
            logger.warning(
                "squad regeneration found %d complementary-view conflicts; newest retained",
                len(merged.mergeConflicts),
            )

        self._modelReplace(cleanName, merged.players, max(item[0] for item in captures))
        model = SquadModelService(self.engine).modelLoad(cleanName, create=False)
        if model is None:
            raise ValueError("Regenerated squad model could not be reloaded")
        if model.regenerationRequired:
            raise ValueError(
                "Squad regeneration completed but the rebuilt model is still stale"
            )
        logger.done(f"squad screenshot regeneration finished for {cleanName}")
        return SquadRegenerationResult(model, len(captures), len(merged.players))

    def _capturesLoad(self, squadName: str) -> tuple[tuple[int, str], ...]:
        with Session(self.engine) as session:
            squad = session.scalar(
                select(Squad)
                .where(Squad.normalizedName == squadName.casefold())
                .options(
                    selectinload(Squad.screenshots).selectinload(
                        SquadScreenshot.importSession
                    )
                )
            )
            if squad is None:
                return ()
            return tuple(
                (capture.importSessionId, capture.importSession.imageFilename)
                for capture in sorted(
                    squad.screenshots,
                    key=lambda item: item.importSessionId,
                )
            )

    def _modelReplace(self, squadName: str, players, sourceImportSessionId: int) -> None:
        now = datetime.now()
        with Session(self.engine) as session, session.begin():
            source = session.scalar(
                select(Squad)
                .where(Squad.normalizedName == squadName.casefold())
                .options(selectinload(Squad.screenshots))
            )
            if source is None:
                raise ValueError(f"Squad evidence does not exist: {squadName}")
            stored = session.scalar(
                select(ObjectModelSquad)
                .where(ObjectModelSquad.normalizedName == squadName.casefold())
                .options(
                    selectinload(ObjectModelSquad.players).selectinload(
                        ObjectModelPlayer.traits
                    )
                )
            )
            if stored is None:
                stored = ObjectModelSquad(
                    name=source.name,
                    normalizedName=source.normalizedName,
                    sourceSquad=source,
                    generatedAt=now,
                    updatedAt=now,
                )
                session.add(stored)
                traitsByPlayer = {}
            else:
                traitsByPlayer = {
                    player.normalizedName: tuple(
                        trait.traitName for trait in player.traits
                    )
                    for player in stored.players
                }
                stored.players.clear()
                session.flush()
                stored.generatedAt = now
                stored.updatedAt = now
                stored.sourceSquad = source

            for extracted in players:
                normalizedName = extracted.name.strip().casefold()
                stored.players.append(
                    ObjectModelPlayer(
                        name=extracted.name.strip(),
                        normalizedName=normalizedName,
                        positions=extracted.positions.strip(),
                        ca=extracted.ca.strip(),
                        pa=extracted.pa.strip(),
                        confidence=extracted.confidence,
                        sourceImportSessionId=sourceImportSessionId,
                        validationState="extracted",
                        attributes=[
                            ObjectModelPlayerAttribute(
                                attributeName=name,
                                attributeValue=value,
                                validationState="extracted",
                            )
                            for name, value in sorted(extracted.attributes.items())
                        ],
                        traits=[
                            ObjectModelPlayerTrait(
                                traitName=trait,
                                validationState="corrected",
                            )
                            for trait in traitsByPlayer.get(normalizedName, ())
                        ],
                    )
                )
            for capture in source.screenshots:
                capture.supersededAt = now
