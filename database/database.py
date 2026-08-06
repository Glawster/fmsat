"""Transactional database gateway."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import create_engine as createEngine
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload, sessionmaker

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
from .records import DeletionRecord, SquadPlayerRecord, SquadRecord, TacticRecord

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

    def squadImportPairSave(
        self,
        imageFilenames: list[str],
        extractedPlayers: list[ExtractedPlayer],
        squadName: str,
    ) -> ImportSession:
        """Compatibility wrapper for a two-image squad capture batch."""

        if len(imageFilenames) != 2:
            raise DatabaseError("A paired squad import requires exactly two screenshots")
        return self.squadImportBatchSave(imageFilenames, extractedPlayers, squadName)

    def squadImportBatchSave(
        self,
        imageFilenames: list[str],
        extractedPlayers: list[ExtractedPlayer],
        squadName: str,
    ) -> ImportSession:
        """Persist all capture pages and one merged squad player snapshot."""

        if len(imageFilenames) < 2:
            raise DatabaseError("A squad capture batch requires at least two screenshots")
        try:
            with self._sessionFactory.begin() as session:
                cleanName = squadName.strip()
                if not cleanName:
                    raise DatabaseError("A squad name is required")
                normalizedName = cleanName.casefold()
                squad = session.scalar(
                    select(Squad).where(Squad.normalizedName == normalizedName)
                )
                if squad is None:
                    squad = Squad(name=cleanName, normalizedName=normalizedName)
                    session.add(squad)
                importSessions = [
                    ImportSession(
                        imageFilename=filename,
                        screenType=ScreenType.SQUAD_ATTRIBUTES.value,
                        squadCapture=SquadScreenshot(squad=squad),
                    )
                    for filename in imageFilenames
                ]
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
                    importSessions[0].players.append(player)
                session.add_all(importSessions)
            return importSessions[0]
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to save squad capture batch: {exc}") from exc

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

    def tacticRecords(self) -> list[TacticRecord]:
        """Return tactic-management records with latest Formation images."""

        try:
            with Session(self.engine) as session:
                tactics = session.scalars(
                    select(Tactic)
                    .options(
                        selectinload(Tactic.screenshots).selectinload(
                            TacticScreenshot.importSession
                        )
                    )
                    .order_by(Tactic.name)
                ).all()
                records = []
                for tactic in tactics:
                    formations = [
                        screenshot.importSession
                        for screenshot in tactic.screenshots
                        if screenshot.screenType == ScreenType.TACTIC_FORMATION.value
                    ]
                    latest = (
                        max(formations, key=lambda item: (item.date, item.id))
                        if formations
                        else None
                    )
                    records.append(
                        TacticRecord(
                            tactic.name,
                            len(tactic.screenshots),
                            latest.imageFilename if latest else None,
                        )
                    )
                return records
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to list tactic records: {exc}") from exc

    def squadsList(self) -> list[str]:
        """Return recognised squad names alphabetically."""

        try:
            with Session(self.engine) as session:
                return list(session.scalars(select(Squad.name).order_by(Squad.name)).all())
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to list squads: {exc}") from exc

    def squadRecords(self) -> list[SquadRecord]:
        """Return squad-management records with capture and player counts."""

        try:
            with Session(self.engine) as session:
                squads = session.scalars(
                    select(Squad)
                    .options(
                        selectinload(Squad.screenshots)
                        .selectinload(SquadScreenshot.importSession)
                        .selectinload(ImportSession.players)
                    )
                    .order_by(Squad.name)
                ).all()
                return [
                    SquadRecord(
                        squad.name,
                        len(squad.screenshots),
                        sum(
                            len(screenshot.importSession.players)
                            for screenshot in squad.screenshots
                        ),
                    )
                    for squad in squads
                ]
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to list squad records: {exc}") from exc

    def squadPlayerRecords(self, squadName: str) -> list[SquadPlayerRecord]:
        """Return stored players and their source screenshots for one squad."""

        normalizedName = squadName.strip().casefold()
        try:
            with Session(self.engine) as session:
                rows = session.execute(
                    select(Player, ImportSession)
                    .join(ImportSession, Player.importSessionId == ImportSession.id)
                    .join(
                        SquadScreenshot,
                        SquadScreenshot.importSessionId == ImportSession.id,
                    )
                    .join(Squad, SquadScreenshot.squadId == Squad.id)
                    .where(Squad.normalizedName == normalizedName)
                    .order_by(Player.name, ImportSession.date.desc())
                ).all()
                return [
                    SquadPlayerRecord(
                        player.name,
                        player.positions,
                        player.ca,
                        player.pa,
                        player.confidence,
                        importSession.date,
                        importSession.imageFilename,
                    )
                    for player, importSession in rows
                ]
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to list squad players: {exc}") from exc

    def tacticsDelete(self, tacticNames: list[str]) -> DeletionRecord:
        """Delete selected tactics and their owned import sessions atomically."""

        normalizedNames = {name.strip().casefold() for name in tacticNames if name.strip()}
        try:
            with self._sessionFactory.begin() as session:
                tactics = session.scalars(
                    select(Tactic)
                    .where(Tactic.normalizedName.in_(normalizedNames))
                    .options(
                        selectinload(Tactic.screenshots).selectinload(
                            TacticScreenshot.importSession
                        )
                    )
                ).all()
                imports = [
                    screenshot.importSession
                    for tactic in tactics
                    for screenshot in tactic.screenshots
                ]
                paths = tuple(item.imageFilename for item in imports)
                for tactic in tactics:
                    session.delete(tactic)
                session.flush()
                for importSession in imports:
                    session.delete(importSession)
            return DeletionRecord(len(tactics), paths)
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to delete tactics: {exc}") from exc

    def squadsDelete(self, squadNames: list[str]) -> DeletionRecord:
        """Delete selected squads and their owned import sessions atomically."""

        normalizedNames = {name.strip().casefold() for name in squadNames if name.strip()}
        try:
            with self._sessionFactory.begin() as session:
                squads = session.scalars(
                    select(Squad)
                    .where(Squad.normalizedName.in_(normalizedNames))
                    .options(
                        selectinload(Squad.screenshots).selectinload(
                            SquadScreenshot.importSession
                        )
                    )
                ).all()
                imports = [
                    screenshot.importSession
                    for squad in squads
                    for screenshot in squad.screenshots
                ]
                paths = tuple(item.imageFilename for item in imports)
                for squad in squads:
                    session.delete(squad)
                session.flush()
                for importSession in imports:
                    session.delete(importSession)
            return DeletionRecord(len(squads), paths)
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Unable to delete squads: {exc}") from exc

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
