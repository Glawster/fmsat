"""SQLAlchemy models for extracted player history."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
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
    tacticCapture: Mapped[TacticScreenshot | None] = relationship(back_populates="importSession")
    squadCapture: Mapped[SquadScreenshot | None] = relationship(back_populates="importSession")
    clubCapture: Mapped[SquadClubScreenshot | None] = relationship(back_populates="importSession")


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
    squadApplications: Mapped[list[SquadTacticApplication]] = relationship(
        back_populates="tactic", cascade="all, delete-orphan"
    )
    structuredDefinition: Mapped[StructuredTacticDefinition | None] = relationship(
        back_populates="tactic",
        cascade="all, delete-orphan",
        single_parent=True,
        uselist=False,
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
    importSession: Mapped[ImportSession] = relationship(back_populates="tacticCapture")


class StructuredTacticDefinition(Base):
    """The current persistent structured definition for one tactic."""

    __tablename__ = "structured_tactic_definitions"

    id: Mapped[int] = mappedColumn(primary_key=True)
    tacticId: Mapped[int] = mappedColumn(
        "tactic_id", ForeignKey("tactics.id"), unique=True, nullable=False, index=True
    )
    confirmed: Mapped[bool] = mappedColumn(Boolean, default=False, nullable=False)
    complete: Mapped[bool] = mappedColumn(Boolean, default=False, nullable=False)
    tacticMetadata: Mapped[dict[str, str]] = mappedColumn(
        "metadata", JSON, default=dict, nullable=False
    )
    tactic: Mapped[Tactic] = relationship(back_populates="structuredDefinition")
    slots: Mapped[list[StructuredFormationSlot]] = relationship(
        back_populates="definition", cascade="all, delete-orphan"
    )
    instructions: Mapped[list[StructuredTeamInstruction]] = relationship(
        back_populates="definition", cascade="all, delete-orphan"
    )
    issues: Mapped[list[StructuredTacticIssue]] = relationship(
        back_populates="definition", cascade="all, delete-orphan"
    )


class StructuredFormationSlot(Base):
    """One persisted formation slot for one explicitly identified phase."""

    __tablename__ = "structured_formation_slots"
    __table_args__ = (
        UniqueConstraint("definition_id", "phase", "slot_id"),
        CheckConstraint("x >= 0 AND x <= 1", name="ck_structured_slot_x_normalized"),
        CheckConstraint("y >= 0 AND y <= 1", name="ck_structured_slot_y_normalized"),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_structured_slot_confidence_normalized",
        ),
    )

    id: Mapped[int] = mappedColumn(primary_key=True)
    definitionId: Mapped[int] = mappedColumn(
        "definition_id",
        ForeignKey("structured_tactic_definitions.id"),
        nullable=False,
        index=True,
    )
    slotId: Mapped[str] = mappedColumn("slot_id", String(100), nullable=False)
    phase: Mapped[str] = mappedColumn(String(32), nullable=False, index=True)
    position: Mapped[str | None] = mappedColumn(String(16))
    role: Mapped[str | None] = mappedColumn(String(100))
    duty: Mapped[str | None] = mappedColumn(String(32))
    x: Mapped[float] = mappedColumn(Float, nullable=False)
    y: Mapped[float] = mappedColumn(Float, nullable=False)
    observedRole: Mapped[str] = mappedColumn("observed_role", Text, default="", nullable=False)
    displayedPlayer: Mapped[str | None] = mappedColumn("displayed_player", String(255))
    confidence: Mapped[float] = mappedColumn(Float, default=0.0, nullable=False)
    sourceImportSessionId: Mapped[int | None] = mappedColumn(
        "source_import_session_id", ForeignKey("import_sessions.id"), index=True
    )
    validationState: Mapped[str] = mappedColumn("validation_state", String(32), nullable=False)
    definition: Mapped[StructuredTacticDefinition] = relationship(back_populates="slots")
    sourceImportSession: Mapped[ImportSession | None] = relationship()


class StructuredTeamInstruction(Base):
    """One canonical instruction with its displayed evidence and provenance."""

    __tablename__ = "structured_team_instructions"
    __table_args__ = (
        UniqueConstraint("definition_id", "phase", "category"),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_structured_instruction_confidence_normalized",
        ),
    )

    id: Mapped[int] = mappedColumn(primary_key=True)
    definitionId: Mapped[int] = mappedColumn(
        "definition_id",
        ForeignKey("structured_tactic_definitions.id"),
        nullable=False,
        index=True,
    )
    phase: Mapped[str] = mappedColumn(String(32), nullable=False, index=True)
    category: Mapped[str] = mappedColumn(String(100), nullable=False)
    canonicalValue: Mapped[str | bool | None] = mappedColumn("canonical_value", JSON)
    displayValue: Mapped[str] = mappedColumn("display_value", Text, nullable=False)
    confidence: Mapped[float] = mappedColumn(Float, default=0.0, nullable=False)
    sourceImportSessionId: Mapped[int | None] = mappedColumn(
        "source_import_session_id", ForeignKey("import_sessions.id"), index=True
    )
    validationState: Mapped[str] = mappedColumn("validation_state", String(32), nullable=False)
    definition: Mapped[StructuredTacticDefinition] = relationship(back_populates="instructions")
    sourceImportSession: Mapped[ImportSession | None] = relationship()


class StructuredTacticIssue(Base):
    """One persisted extraction or validation issue for a structured tactic."""

    __tablename__ = "structured_tactic_issues"

    id: Mapped[int] = mappedColumn(primary_key=True)
    definitionId: Mapped[int] = mappedColumn(
        "definition_id",
        ForeignKey("structured_tactic_definitions.id"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mappedColumn(String(100), nullable=False)
    message: Mapped[str] = mappedColumn(Text, nullable=False)
    observedText: Mapped[str | None] = mappedColumn("observed_text", Text)
    definition: Mapped[StructuredTacticDefinition] = relationship(back_populates="issues")


class Squad(Base):
    """A named playing squad that can be assessed against multiple tactics."""

    __tablename__ = "squads"

    id: Mapped[int] = mappedColumn(primary_key=True)
    name: Mapped[str] = mappedColumn(String(255), nullable=False)
    normalizedName: Mapped[str] = mappedColumn(
        "normalized_name", String(255), unique=True, nullable=False
    )
    screenshots: Mapped[list[SquadScreenshot]] = relationship(
        back_populates="squad", cascade="all, delete-orphan"
    )
    clubScreenshots: Mapped[list[SquadClubScreenshot]] = relationship(
        back_populates="squad", cascade="all, delete-orphan"
    )
    tacticApplications: Mapped[list[SquadTacticApplication]] = relationship(
        back_populates="squad", cascade="all, delete-orphan"
    )


class SquadScreenshot(Base):
    """Links a Squad Attributes import to its independently named squad."""

    __tablename__ = "squad_screenshots"

    id: Mapped[int] = mappedColumn(primary_key=True)
    squadId: Mapped[int] = mappedColumn(
        "squad_id", ForeignKey("squads.id"), nullable=False, index=True
    )
    importSessionId: Mapped[int] = mappedColumn(
        "import_session_id", ForeignKey("import_sessions.id"), unique=True, nullable=False
    )
    squad: Mapped[Squad] = relationship(back_populates="screenshots")
    importSession: Mapped[ImportSession] = relationship(back_populates="squadCapture")


class SquadClubScreenshot(Base):
    """Links a Club Information badge screenshot to its squad."""

    __tablename__ = "squad_club_screenshots"

    id: Mapped[int] = mappedColumn(primary_key=True)
    squadId: Mapped[int] = mappedColumn(
        "squad_id", ForeignKey("squads.id"), nullable=False, index=True
    )
    importSessionId: Mapped[int] = mappedColumn(
        "import_session_id", ForeignKey("import_sessions.id"), unique=True, nullable=False
    )
    squad: Mapped[Squad] = relationship(back_populates="clubScreenshots")
    importSession: Mapped[ImportSession] = relationship(back_populates="clubCapture")


class SquadTacticApplication(Base):
    """A deliberate pairing of one independently stored squad and tactic."""

    __tablename__ = "squad_tactic_applications"
    __table_args__ = (UniqueConstraint("squad_id", "tactic_id"),)

    id: Mapped[int] = mappedColumn(primary_key=True)
    squadId: Mapped[int] = mappedColumn(
        "squad_id", ForeignKey("squads.id"), nullable=False, index=True
    )
    tacticId: Mapped[int] = mappedColumn(
        "tactic_id", ForeignKey("tactics.id"), nullable=False, index=True
    )
    dateApplied: Mapped[datetime] = mappedColumn(
        "date_applied", DateTime, default=datetime.now, nullable=False
    )
    squad: Mapped[Squad] = relationship(back_populates="tacticApplications")
    tactic: Mapped[Tactic] = relationship(back_populates="squadApplications")


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
