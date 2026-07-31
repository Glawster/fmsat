"""SQLAlchemy models for extracted player history."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship
from sqlalchemy.orm import mapped_column as mappedColumn


class Base(DeclarativeBase):
    """Declarative model base."""


class ImportSession(Base):
    """One confirmed screenshot import."""

    __tablename__ = "import_sessions"

    id: Mapped[int] = mappedColumn(primary_key=True)
    date: Mapped[datetime] = mappedColumn(DateTime, default=datetime.now, nullable=False)
    imageFilename: Mapped[str] = mappedColumn("image_filename", String(1024), nullable=False)
    screenType: Mapped[str] = mappedColumn("screen_type", String(64), nullable=False)
    players: Mapped[list[Player]] = relationship(
        back_populates="importSession", cascade="all, delete-orphan"
    )
    capture: Mapped[TacticScreenshot | None] = relationship(back_populates="importSession")


class Tactic(Base):
    """A user-named tactic whose screenshot coverage can be tracked."""

    __tablename__ = "tactics"

    id: Mapped[int] = mappedColumn(primary_key=True)
    name: Mapped[str] = mappedColumn(String(255), nullable=False)
    normalizedName: Mapped[str] = mappedColumn(
        "normalized_name", String(255), unique=True, nullable=False
    )
    screenshots: Mapped[list[TacticScreenshot]] = relationship(
        back_populates="tactic", cascade="all, delete-orphan"
    )


class TacticScreenshot(Base):
    """Links a confirmed import to the tactic and screen it represents."""

    __tablename__ = "tactic_screenshots"

    id: Mapped[int] = mappedColumn(primary_key=True)
    tacticId: Mapped[int] = mappedColumn(
        "tactic_id", ForeignKey("tactics.id"), nullable=False, index=True
    )
    importSessionId: Mapped[int] = mappedColumn(
        "import_session_id", ForeignKey("import_sessions.id"), unique=True, nullable=False
    )
    screenType: Mapped[str] = mappedColumn("screen_type", String(64), nullable=False, index=True)
    tactic: Mapped[Tactic] = relationship(back_populates="screenshots")
    importSession: Mapped[ImportSession] = relationship(back_populates="capture")


class Player(Base):
    """A player as observed in one import session."""

    __tablename__ = "players"

    id: Mapped[int] = mappedColumn(primary_key=True)
    name: Mapped[str] = mappedColumn(String(255), nullable=False, index=True)
    ca: Mapped[str] = mappedColumn(String(32), default="", nullable=False)
    pa: Mapped[str] = mappedColumn(String(32), default="", nullable=False)
    positions: Mapped[str] = mappedColumn(String(255), default="", nullable=False)
    confidence: Mapped[float] = mappedColumn(Float, nullable=False)
    dateImported: Mapped[datetime] = mappedColumn(
        "date_imported", DateTime, default=datetime.now, nullable=False
    )
    importSessionId: Mapped[int] = mappedColumn(
        "import_session_id", ForeignKey("import_sessions.id"), nullable=False, index=True
    )
    importSession: Mapped[ImportSession] = relationship(back_populates="players")
    attributes: Mapped[list[AttributeSnapshot]] = relationship(
        back_populates="player", cascade="all, delete-orphan"
    )


class AttributeSnapshot(Base):
    """A single visible attribute value captured for a player."""

    __tablename__ = "attribute_snapshots"

    id: Mapped[int] = mappedColumn(primary_key=True)
    playerId: Mapped[int] = mappedColumn(
        "player_id", ForeignKey("players.id"), nullable=False, index=True
    )
    attributeName: Mapped[str] = mappedColumn("attribute_name", String(100), nullable=False)
    attributeValue: Mapped[int | None] = mappedColumn("attribute_value", Integer, nullable=True)
    player: Mapped[Player] = relationship(back_populates="attributes")
