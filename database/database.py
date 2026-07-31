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

from .models import AttributeSnapshot, Base, ImportSession, Player, Tactic, TacticScreenshot

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
        """Persist a confirmed import and all rows in one transaction."""

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
                importSession.capture = TacticScreenshot(
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
