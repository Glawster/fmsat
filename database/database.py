"""Transactional database gateway."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import create_engine as createEngine
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from fmsat.core.detection import ScreenType
from fmsat.core.parser import ExtractedPlayer

from .models import (
    AttributeSnapshot,
    Base,
    ImportSession,
    Player,
    Squad,
    SquadScreenshot,
    SquadTacticApplication,
    Tactic,
    TacticScreenshot,
)

logger = logging.getLogger(__name__)


class DatabaseError(RuntimeError):
    """Raised when a database operation cannot be completed."""


class Database:
    """Owns SQLite initialization and atomic import persistence."""

    def __init__(self, path: Path) -> None:
        self.path = path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            self.engine = createEngine(f"sqlite:///{path}", future=True)
            self._sessionFactory = sessionmaker(self.engine, expire_on_commit=False)
        except (OSError, SQLAlchemyError) as exc:
            raise DatabaseError(f"Unable to initialize database: {exc}") from exc

    def initialize(self) -> None:
        """Create tables that do not yet exist."""

        try:
            Base.metadata.create_all(self.engine)
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to create database tables: {exc}") from exc

    def importSave(
        self,
        imageFilename: str,
        screenType: ScreenType,
        extractedPlayers: list[ExtractedPlayer],
        tacticName: str,
    ) -> ImportSession:
        """Persist a legacy tactic-linked squad import.

        New callers should use ``squadImportSave`` so squads remain independent
        from tactics.
        """

        try:
            with self._sessionFactory.begin() as session:
                cleanName = tacticName.strip()
                if not cleanName:
                    raise DatabaseError("A tactic name is required")
                normalizedName = cleanName.casefold()
                tactic = session.scalar(
                    select(Tactic).where(Tactic.normalizedName == normalizedName)
                )
                if tactic is None:
                    tactic = Tactic(name=cleanName, normalizedName=normalizedName)
                    session.add(tactic)
                importSession = ImportSession(
                    imageFilename=imageFilename,
                    screenType=screenType.value,
                )
                session.add(importSession)
                importSession.tacticCapture = TacticScreenshot(
                    tactic=tactic,
                    screenType=screenType.value,
                )
                for extracted in extractedPlayers:
                    player = Player(
                        name=extracted.name.strip(),
                        positions=extracted.positions.strip(),
                        ca=extracted.ca.strip(),
                        pa=extracted.pa.strip(),
                        confidence=extracted.confidence,
                    )
                    player.attributes.extend(
                        AttributeSnapshot(attributeName=name, attributeValue=value)
                        for name, value in extracted.attributes.items()
                    )
                    importSession.players.append(player)
            logger.info(
                "Saved import session %s with %d players",
                importSession.id,
                len(extractedPlayers),
            )
            return importSession
        except SQLAlchemyError as exc:
            logger.exception("Database write failed")
            raise DatabaseError(f"Unable to save import: {exc}") from exc

    def tacticImportSave(
        self,
        imageFilename: str,
        screenType: ScreenType,
        tacticName: str,
    ) -> ImportSession:
        """Persist one confirmed tactic screenshot."""

        tacticTypes = {
            ScreenType.TACTIC_FORMATION,
            ScreenType.TACTIC_IN_POSSESSION,
            ScreenType.TACTIC_OUT_OF_POSSESSION,
        }
        if screenType not in tacticTypes:
            raise DatabaseError(f"Not a tactic screenshot type: {screenType.value}")
        try:
            with self._sessionFactory.begin() as session:
                cleanName = tacticName.strip()
                if not cleanName:
                    raise DatabaseError("A tactic name is required")
                normalizedName = cleanName.casefold()
                tactic = session.scalar(
                    select(Tactic).where(Tactic.normalizedName == normalizedName)
                )
                if tactic is None:
                    tactic = Tactic(name=cleanName, normalizedName=normalizedName)
                    session.add(tactic)
                importSession = ImportSession(
                    imageFilename=imageFilename,
                    screenType=screenType.value,
                )
                importSession.tacticCapture = TacticScreenshot(
                    tactic=tactic,
                    screenType=screenType.value,
                )
                session.add(importSession)
            return importSession
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to save tactic import: {exc}") from exc

    def squadImportSave(
        self,
        imageFilename: str,
        extractedPlayers: list[ExtractedPlayer],
        squadName: str,
    ) -> ImportSession:
        """Persist a confirmed squad import independently of any tactic."""

        try:
            with self._sessionFactory.begin() as session:
                cleanName = squadName.strip()
                if not cleanName:
                    raise DatabaseError("A squad name is required")
                normalizedName = cleanName.casefold()
                squad = session.scalar(select(Squad).where(Squad.normalizedName == normalizedName))
                if squad is None:
                    squad = Squad(name=cleanName, normalizedName=normalizedName)
                    session.add(squad)
                importSession = ImportSession(
                    imageFilename=imageFilename,
                    screenType=ScreenType.SQUAD_ATTRIBUTES.value,
                )
                importSession.squadCapture = SquadScreenshot(squad=squad)
                for extracted in extractedPlayers:
                    player = Player(
                        name=extracted.name.strip(),
                        positions=extracted.positions.strip(),
                        ca=extracted.ca.strip(),
                        pa=extracted.pa.strip(),
                        confidence=extracted.confidence,
                    )
                    player.attributes.extend(
                        AttributeSnapshot(attributeName=name, attributeValue=value)
                        for name, value in extracted.attributes.items()
                    )
                    importSession.players.append(player)
                session.add(importSession)
            return importSession
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to save squad import: {exc}") from exc

    def screenTypesForTactic(self, tacticName: str) -> set[ScreenType]:
        """Return screen types previously confirmed for a tactic."""

        normalizedName = tacticName.strip().casefold()
        try:
            with Session(self.engine) as session:
                values = session.scalars(
                    select(TacticScreenshot.screenType)
                    .join(Tactic)
                    .where(Tactic.normalizedName == normalizedName)
                ).all()
            return {ScreenType(value) for value in values if value in ScreenType._value2member_map_}
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to inspect tactic screenshots: {exc}") from exc

    def tacticsList(self) -> list[str]:
        """Return recognised tactic names alphabetically."""

        try:
            with Session(self.engine) as session:
                return list(session.scalars(select(Tactic.name).order_by(Tactic.name)).all())
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to list tactics: {exc}") from exc

    def squadsList(self) -> list[str]:
        """Return recognised squad names alphabetically."""

        try:
            with Session(self.engine) as session:
                return list(session.scalars(select(Squad.name).order_by(Squad.name)).all())
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to list squads: {exc}") from exc

    def playerNamesForSquad(self, squadName: str) -> set[str]:
        """Return player names previously confirmed for a squad."""

        normalizedName = squadName.strip().casefold()
        try:
            with Session(self.engine) as session:
                names = session.scalars(
                    select(Player.name)
                    .join(ImportSession, Player.importSessionId == ImportSession.id)
                    .join(
                        SquadScreenshot,
                        SquadScreenshot.importSessionId == ImportSession.id,
                    )
                    .join(Squad, SquadScreenshot.squadId == Squad.id)
                    .where(Squad.normalizedName == normalizedName)
                ).all()
            return set(names)
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to inspect squad players: {exc}") from exc

    def tacticApplyToSquad(
        self,
        squadName: str,
        tacticName: str,
    ) -> SquadTacticApplication:
        """Create or return a deliberate squad-to-tactic application."""

        try:
            with self._sessionFactory.begin() as session:
                squad = session.scalar(
                    select(Squad).where(Squad.normalizedName == squadName.strip().casefold())
                )
                if squad is None:
                    raise DatabaseError(f"Unknown squad: {squadName}")
                tactic = session.scalar(
                    select(Tactic).where(Tactic.normalizedName == tacticName.strip().casefold())
                )
                if tactic is None:
                    raise DatabaseError(f"Unknown tactic: {tacticName}")
                application = session.scalar(
                    select(SquadTacticApplication).where(
                        SquadTacticApplication.squadId == squad.id,
                        SquadTacticApplication.tacticId == tactic.id,
                    )
                )
                if application is None:
                    application = SquadTacticApplication(squad=squad, tactic=tactic)
                    session.add(application)
            return application
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to apply tactic to squad: {exc}") from exc

    def playersList(self) -> list[Player]:
        """Return stored players newest first for the Players view."""

        try:
            with Session(self.engine) as session:
                return list(
                    session.scalars(
                        select(Player).order_by(Player.dateImported.desc(), Player.name)
                    ).all()
                )
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to list players: {exc}") from exc
