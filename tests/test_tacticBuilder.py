"""Tests for building football object-model tactics from structured DB data."""

from __future__ import annotations

from unittest.mock import Mock

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
from fmsat.football.roleIdentity import RoleIdentity
from fmsat.tactics.positionFamily import PositionFamily
from fmsat.tactics.positionIdentity import PositionIdentity


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
                    ("DL", "fullBack"),
                    ("DC", "centreBack"),
                    ("DC", "ballPlayingCentreBack"),
                    ("DR", "fullBack"),
                    ("ML", "winger"),
                    ("DM", "halfBack"),
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
            # Legacy shape-name metadata is deliberately ignored by the builder.
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
    assert result.tactic.inPossession.name == "High Press IP"
    assert result.tactic.outOfPossession.name == "High Press OOP"
    assert len(result.tactic.inPossession.positions) == 11
    assert len(result.tactic.outOfPossession.positions) == 11
    firstPosition = result.tactic.inPossession.positions[0]
    assert firstPosition.slotId == "in-1"
    assert firstPosition.duty == "support"
    assert firstPosition.x == 0.0
    assert firstPosition.y == 0.5
    assert firstPosition.confidence == 0.95
    assert firstPosition.sourceImportSessionId == imported.id
    assert firstPosition.validationState == "confirmed"
    assert firstPosition.family is PositionFamily.GK
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


def testBuilderPreservesPositionWhenDutyIsNotShown() -> None:
    """A missing duty remains None and is not an extraction failure or default."""

    builder = TacticBuilder(Mock())
    issues = []
    slot = StructuredFormationSlot(
        slotId="slot-01",
        phase="inPossession",
        position="ST",
        role="centreForward",
        duty=None,
        x=0.5,
        y=0.1,
        observedRole="CFD",
        displayedPlayer="Example Forward",
        confidence=0.9,
        validationState="extracted",
    )

    position = builder._positionBuild(slot, "inPossession", issues, {}, {})

    assert position is not None
    assert position.duty is None
    assert position.roleProfile.name == "Observed role"
    assert position.validationState == "extracted"
    assert position.player is None
    assert position.family is PositionFamily.STC
    assert issues == []


def testBuilderRejectsKnownRoleAtIncompatiblePositionFamily() -> None:
    builder = TacticBuilder(Mock())
    issues = []
    slot = StructuredFormationSlot(
        slotId="gk-01",
        phase="outOfPossession",
        position="DC",
        role="sweeperKeeper",
        duty=None,
        x=0.5,
        y=0.88,
        observedRole="SK",
        confidence=0.95,
        validationState="extracted",
    )

    position = builder._positionBuild(slot, "outOfPossession", issues, {}, {})

    assert position is None
    assert [issue.code for issue in issues] == ["incompatibleRolePosition"]
    assert "supported position families: GK" in issues[0].message


def testBuilderMapsCanonicalLateralPositionsToDomainIdentities() -> None:
    builder = TacticBuilder(Mock())

    assert builder._positionIdentityParse("STC") is PositionIdentity.ST
    assert builder._positionIdentityParse("DCL") is PositionIdentity.DC
    assert builder._positionIdentityParse("DCR") is PositionIdentity.DC
    assert builder._positionIdentityParse("DMCL") is PositionIdentity.DM
    assert builder._positionIdentityParse("DMCR") is PositionIdentity.DM


def testBuilderMapsKnownFullBackRoleToSharedWideDefenderIdentity() -> None:
    builder = TacticBuilder(Mock())

    assert builder._roleIdentityParse("fullBack", "FB") is RoleIdentity.WB


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

        tactic.structuredDefinition = ScreenshotDerivedTacticDefinition(
            confirmed=False,
            complete=False,
            tacticMetadata={},
            slots=[
                StructuredFormationSlot(
                    slotId=f"{phase}-{slotId}",
                    phase=phase,
                    position=position,
                    role=role,
                    duty=duty,
                    x=0.5,
                    y=y,
                    observedRole="",
                    confidence=0.9,
                    sourceImportSession=sourceImport,
                    validationState="confirmed",
                )
                for phase in ("inPossession", "outOfPossession")
                for slotId, position, role, duty, y in (
                    ("slot-z", "ST", "centreForward", "attack", 0.1),
                    ("slot-a", "GK", "goalkeeper", "defend", 0.9),
                    ("slot-m", "DC", "centreBack", "defend", 0.7),
                )
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
