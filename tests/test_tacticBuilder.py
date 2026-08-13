"""Tests for building football object-model tactics from structured DB data."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from fmsat.core.builder.tacticBuilder import TacticBuilder
from fmsat.core.detection import ScreenType
from fmsat.database import (
    Database,
    ImportSession,
    StructuredFormationSlot,
    ScreenshotDerivedTacticDefinition,
    StructuredTeamInstruction,
    Tactic,
)


def testBuilderLoadsStructuredTacticIntoObjectModel(tmp_path) -> None:
    """Builder should map persisted structured slots into a Tactic object."""

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    imported = database.tacticImportSave(
        "/captures/formation.png",
        ScreenType.TACTIC_FORMATION,
        "High Press",
    )

    with Session(database.engine) as session, session.begin():
        tactic = session.scalar(select(Tactic).where(Tactic.normalizedName == "high press"))
        sourceImport = session.get(ImportSession, imported.id)
        assert tactic is not None
        assert sourceImport is not None

        slots = [
            StructuredFormationSlot(
                slotId=f"in-{index + 1}",
                phase="inPossession",
                position=position,
                role=role,
                duty="support",
                x=0.1 * index,
                y=0.5,
                observedRole="",
                confidence=0.95,
                sourceImportSession=sourceImport,
                validationState="confirmed",
            )
            for index, (position, role) in enumerate(
                [
                    ("GK", "goalkeeper"),
                    ("DC", "centreBack"),
                    ("DC", "centreBack"),
                    ("DC", "centreBack"),
                    ("WBL", "wingBack"),
                    ("WBR", "wingBack"),
                    ("MC", "deepLyingPlaymaker"),
                    ("MC", "centralMidfielder"),
                    ("AML", "winger"),
                    ("AMR", "winger"),
                    ("ST", "centreForward"),
                ]
            )
        ] + [
            StructuredFormationSlot(
                slotId=f"out-{index + 1}",
                phase="outOfPossession",
                position=position,
                role=role,
                duty="support",
                x=0.1 * index,
                y=0.4,
                observedRole="",
                confidence=0.95,
                sourceImportSession=sourceImport,
                validationState="confirmed",
            )
            for index, (position, role) in enumerate(
                [
                    ("GK", "goalkeeper"),
                    ("DL", "wingBack"),
                    ("DC", "centreBack"),
                    ("DC", "ballPlayingCentreBack"),
                    ("DR", "wingBack"),
                    ("ML", "winger"),
                    ("MC", "halfBack"),
                    ("MC", "deepLyingPlaymaker"),
                    ("MR", "winger"),
                    ("AMC", "attackingMidfielder"),
                    ("ST", "centreForward"),
                ]
            )
        ]

        tactic.structuredDefinition = ScreenshotDerivedTacticDefinition(
            confirmed=True,
            complete=True,
            tacticMetadata={
                "inPossessionName": "3-4-2-1",
                "outOfPossessionName": "4-4-1-1",
            },
            slots=slots,
            instructions=[
                StructuredTeamInstruction(
                    phase="inPossession",
                    category="attackingWidth",
                    canonicalValue="stayWider",
                    displayValue="Stay Wider",
                    confidence=0.9,
                    sourceImportSession=sourceImport,
                    validationState="confirmed",
                ),
                StructuredTeamInstruction(
                    phase="outOfPossession",
                    category="attackingWidth",
                    canonicalValue="sitNarrower",
                    displayValue="Sit Narrower",
                    confidence=0.87,
                    sourceImportSession=sourceImport,
                    validationState="confirmed",
                ),
                StructuredTeamInstruction(
                    phase="transition",
                    category="possessionLost",
                    canonicalValue="counterPress",
                    displayValue="Counter-Press",
                    confidence=0.92,
                    sourceImportSession=sourceImport,
                    validationState="confirmed",
                ),
            ],
        )

    builder = TacticBuilder(database.engine)
    result = builder.tacticBuild("High Press")

    assert result.tactic is not None
    assert result.complete is True
    assert result.confirmed is True
    assert result.tactic.name == "High Press"
    assert result.tactic.inPossession.name == "3-4-2-1"
    assert result.tactic.outOfPossession.name == "4-4-1-1"
    assert len(result.tactic.inPossession.positions) == 11
    assert len(result.tactic.outOfPossession.positions) == 11
    inPossessionInstruction = next(iter(result.tactic.inPossession.instructions.keys()))
    outOfPossessionInstruction = next(iter(result.tactic.outOfPossession.instructions.keys()))
    assert inPossessionInstruction is outOfPossessionInstruction
    assert not result.issues


def testBuilderReportsMissingStructuredDefinition(tmp_path) -> None:
    """Builder should report missing extraction instead of raising."""

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    database.tacticImportSave(
        "/captures/formation.png",
        ScreenType.TACTIC_FORMATION,
        "High Press",
    )

    builder = TacticBuilder(database.engine)
    result = builder.tacticBuild("High Press")

    assert result.tactic is None
    assert result.complete is False
    assert result.confirmed is False
    assert any(issue.code == "missingStructuredDefinition" for issue in result.issues)


def testBuilderOrdersPositionsBySemanticPositionIdentity(tmp_path) -> None:
    """Builder should order positions by PositionIdentity rather than slot ID."""

    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    imported = database.tacticImportSave(
        "/captures/formation.png",
        ScreenType.TACTIC_FORMATION,
        "Ordered Shape",
    )

    with Session(database.engine) as session, session.begin():
        tactic = session.scalar(select(Tactic).where(Tactic.normalizedName == "ordered shape"))
        sourceImport = session.get(ImportSession, imported.id)
        assert tactic is not None
        assert sourceImport is not None

        # Deliberately scramble slot IDs to ensure semantic ordering is applied.
        tactic.structuredDefinition = ScreenshotDerivedTacticDefinition(
            confirmed=False,
            complete=False,
            tacticMetadata={},
            slots=[
                StructuredFormationSlot(
                    slotId="slot-z",
                    phase="formation",
                    position="ST",
                    role="centreForward",
                    duty="attack",
                    x=0.5,
                    y=0.1,
                    observedRole="",
                    confidence=0.9,
                    sourceImportSession=sourceImport,
                    validationState="confirmed",
                ),
                StructuredFormationSlot(
                    slotId="slot-a",
                    phase="formation",
                    position="GK",
                    role="goalkeeper",
                    duty="defend",
                    x=0.5,
                    y=0.9,
                    observedRole="",
                    confidence=0.9,
                    sourceImportSession=sourceImport,
                    validationState="confirmed",
                ),
                StructuredFormationSlot(
                    slotId="slot-m",
                    phase="formation",
                    position="DC",
                    role="centreBack",
                    duty="defend",
                    x=0.5,
                    y=0.7,
                    observedRole="",
                    confidence=0.9,
                    sourceImportSession=sourceImport,
                    validationState="confirmed",
                ),
            ],
            instructions=[],
        )

    builder = TacticBuilder(database.engine)
    result = builder.tacticBuild("Ordered Shape")

    assert result.tactic is not None
    assert [position.identity.value for position in result.tactic.inPossession.positions] == [
        "GK",
        "DC",
        "ST",
    ]
