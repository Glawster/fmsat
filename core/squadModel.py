"""Editable squad object-model generation, loading, and persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fmsat.database.models import (
    ImportSession,
    ObjectModelPlayer,
    ObjectModelPlayerAttribute,
    ObjectModelSquad,
    Player,
    Squad,
    SquadScreenshot,
)
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, selectinload


@dataclass(frozen=True, slots=True)
class SquadModelPlayer:
    """One editable player detached from SQLAlchemy persistence."""

    name: str
    positions: str
    ca: str
    pa: str
    confidence: float | None
    attributes: tuple[tuple[str, int | None], ...]
    sourceImportSessionId: int | None = None
    validationState: str = "extracted"


@dataclass(frozen=True, slots=True)
class SquadModel:
    """Current editable squad facts used by assessment and presentation."""

    name: str
    players: tuple[SquadModelPlayer, ...]
    generatedAt: datetime
    updatedAt: datetime
    evidenceSuperseded: bool
    regenerationRequired: bool = False


class SquadModelService:
    """Keep screenshot evidence separate from the editable current squad model."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    ## model

    def modelLoad(self, squadName: str, *, create: bool = True) -> SquadModel | None:
        """Load a squad model, optionally generating its first model from OCR evidence."""

        cleanName = squadName.strip()
        if not cleanName:
            return None
        with Session(self.engine) as session:
            stored = self._storedLoad(session, cleanName)
            if stored is not None:
                return self._modelDetach(stored)
        if not create:
            return None
        return self._modelGenerate(cleanName)

    def modelSave(self, model: SquadModel) -> SquadModel:
        """Persist user-edited values and mark their screenshot evidence superseded."""

        cleanName = model.name.strip()
        if not cleanName:
            raise ValueError("Squad name is required")
        now = datetime.now()
        with Session(self.engine) as session, session.begin():
            source = session.scalar(
                select(Squad)
                .where(Squad.normalizedName == cleanName.casefold())
                .options(selectinload(Squad.screenshots))
            )
            stored = self._storedLoad(session, cleanName)
            if stored is None:
                stored = ObjectModelSquad(
                    name=cleanName,
                    normalizedName=cleanName.casefold(),
                    sourceSquad=source,
                    generatedAt=model.generatedAt,
                )
                session.add(stored)
            else:
                stored.players.clear()
                session.flush()
            stored.name = cleanName
            stored.sourceSquad = source
            stored.updatedAt = now
            stored.players.extend(
                self._playerStore(player, manual=True) for player in model.players
            )

            # Supersession does not delete or rewrite imports. It records that
            # the editable model is now authoritative over the captured values.
            if source is not None:
                for capture in source.screenshots:
                    capture.supersededAt = now
            session.flush()
            result = self._modelDetach(stored)
        return result

    ## generation

    def _modelGenerate(self, squadName: str) -> SquadModel | None:
        """Create the first editable model from each player's newest OCR snapshot."""

        now = datetime.now()
        with Session(self.engine) as session, session.begin():
            source = session.scalar(
                select(Squad)
                .where(Squad.normalizedName == squadName.casefold())
                .options(
                    selectinload(Squad.screenshots)
                    .selectinload(SquadScreenshot.importSession)
                    .selectinload(ImportSession.players)
                    .selectinload(Player.attributes)
                )
            )
            if source is None:
                return None

            latest: dict[str, Player] = {}
            players = (
                player
                for capture in sorted(
                    source.screenshots,
                    key=lambda item: (item.importSession.date, item.importSession.id),
                    reverse=True,
                )
                for player in sorted(
                    capture.importSession.players,
                    key=lambda item: item.id,
                    reverse=True,
                )
            )
            for player in players:
                latest.setdefault(player.name.strip().casefold(), player)

            stored = ObjectModelSquad(
                name=source.name,
                normalizedName=source.normalizedName,
                sourceSquad=source,
                generatedAt=now,
                updatedAt=now,
            )
            for player in sorted(latest.values(), key=lambda item: item.name.casefold()):
                stored.players.append(
                    ObjectModelPlayer(
                        name=player.name,
                        normalizedName=player.name.strip().casefold(),
                        positions=player.positions,
                        ca=player.ca,
                        pa=player.pa,
                        confidence=player.confidence,
                        sourceImportSessionId=player.importSessionId,
                        validationState="extracted",
                        attributes=[
                            ObjectModelPlayerAttribute(
                                attributeName=attribute.attributeName,
                                attributeValue=attribute.attributeValue,
                                validationState="extracted",
                            )
                            for attribute in sorted(
                                player.attributes,
                                key=lambda item: item.attributeName,
                            )
                        ],
                    )
                )
            session.add(stored)
            session.flush()
            return self._modelDetach(stored)

    ## persistence mapping

    @staticmethod
    def _modelDetach(stored: ObjectModelSquad) -> SquadModel:
        """Copy one eager-loaded row graph into framework-independent values."""

        sourceImportIds = (
            [
                capture.importSessionId
                for capture in stored.sourceSquad.screenshots
                if capture.supersededAt is None
            ]
            if stored.sourceSquad is not None
            else []
        )
        modelImportIds = [
            player.sourceImportSessionId
            for player in stored.players
            if player.sourceImportSessionId is not None
        ]
        return SquadModel(
            name=stored.name,
            players=tuple(
                SquadModelPlayer(
                    name=player.name,
                    positions=player.positions,
                    ca=player.ca,
                    pa=player.pa,
                    confidence=player.confidence,
                    sourceImportSessionId=player.sourceImportSessionId,
                    validationState=player.validationState,
                    attributes=tuple(
                        (attribute.attributeName, attribute.attributeValue)
                        for attribute in sorted(
                            player.attributes,
                            key=lambda item: item.attributeName,
                        )
                    ),
                )
                for player in sorted(stored.players, key=lambda item: item.name.casefold())
            ),
            generatedAt=stored.generatedAt,
            updatedAt=stored.updatedAt,
            evidenceSuperseded=bool(
                stored.sourceSquad
                and stored.sourceSquad.screenshots
                and all(
                    capture.supersededAt is not None
                    for capture in stored.sourceSquad.screenshots
                )
            ),
            regenerationRequired=bool(
                sourceImportIds
                and (
                    not modelImportIds
                    or max(sourceImportIds) > max(modelImportIds)
                )
            ),
        )

    @staticmethod
    def _playerStore(player: SquadModelPlayer, *, manual: bool) -> ObjectModelPlayer:
        """Map one detached player into editable object-model persistence."""

        state = "corrected" if manual else player.validationState
        return ObjectModelPlayer(
            name=player.name.strip(),
            normalizedName=player.name.strip().casefold(),
            positions=player.positions.strip(),
            ca=player.ca.strip(),
            pa=player.pa.strip(),
            confidence=player.confidence,
            sourceImportSessionId=player.sourceImportSessionId,
            validationState=state,
            attributes=[
                ObjectModelPlayerAttribute(
                    attributeName=name,
                    attributeValue=value,
                    validationState=state,
                )
                for name, value in sorted(player.attributes)
            ],
        )

    @staticmethod
    def _storedLoad(session: Session, squadName: str) -> ObjectModelSquad | None:
        """Load one complete squad-model row graph inside the caller's session."""

        return session.scalar(
            select(ObjectModelSquad)
            .where(ObjectModelSquad.normalizedName == squadName.casefold())
            .options(
                selectinload(ObjectModelSquad.sourceSquad).selectinload(Squad.screenshots),
                selectinload(ObjectModelSquad.players).selectinload(
                    ObjectModelPlayer.attributes
                ),
            )
        )
