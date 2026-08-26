"""Regression tests for the requirement 007 squad presentation refinements."""

from datetime import datetime
from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QMainWindow

from fmsat.app.squadDetailModel import (
    AnalysisFindingDisplay,
    CandidateDisplay,
    PlayerRoleDisplay,
    RoleDisplay,
    SquadDetailModel,
)
from fmsat.app.squadDetailTabOverrides import SquadAnalysisTab, SquadRolesTab
from fmsat.app.squadDetailView import SquadDetailView
from fmsat.core.config import AttributeDefinition
from fmsat.core.squadModel import SquadModel


def _squad() -> SquadModel:
    return SquadModel(
        name="First Team",
        players=(),
        generatedAt=datetime(2026, 8, 15),
        updatedAt=datetime(2026, 8, 15),
        evidenceSuperseded=False,
        regenerationRequired=False,
    )


def _role(code: str, abbreviation: str, positions: str) -> RoleDisplay:
    return RoleDisplay(
        roleCode=code,
        displayName=code.replace("_", " ").title(),
        abbreviation=abbreviation,
        positions=positions,
        phases="In Possession",
        coverage="Best: Example · Backup: Reserve",
        candidates=(),
    )


def testAnalysisDepthShowsEveryRequiredTacticalSlot(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Repeated roles remain separate depth requirements while role identity stays unique."""

    roles = (
        _role("attackingWingBack", "AWB", "WBL, WBR"),
        _role("centreBack", "CB", "DCL, DCR"),
        _role("deepLyingPlaymaker", "DLP", "DMCL"),
        _role("defensiveMidfielder", "DM", "DMCR"),
        _role("insideForward", "IF", "AML"),
        _role("winger", "W", "AMR"),
        _role("channelForward", "CHF", "STC"),
        _role("sweeperKeeper", "SK", "GK, AMC"),
    )
    model = SquadDetailModel(
        squad=_squad(),
        tacticName="High Press",
        availableTactics=("High Press",),
        sourceStatus="Generated from screenshot evidence",
        updated="15 Aug 2026 22:00",
        requiredPositionCount=11,
        roles=roles,
    )
    tab = SquadAnalysisTab(model)
    qtbot.addWidget(tab)

    assert len(model.roles) == 8
    assert tab.depthTable.rowCount() == 11
    assert tab.depthTable.item(0, 0).text().startswith("AWB · WBL")
    assert tab.depthTable.item(1, 0).text().startswith("AWB · WBR")


def testSquadViewBuildsExactlyElevenDepthRowsFromLinkedTacticSlots(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Phase role changes are combined by slot rather than counted as extra players."""

    def position(slotId: str, roleCode: str, canonicalPosition: str) -> SimpleNamespace:
        return SimpleNamespace(
            slotId=slotId,
            canonicalRole=roleCode,
            canonicalPosition=canonicalPosition,
            identity=SimpleNamespace(value=canonicalPosition),
            roleProfile=SimpleNamespace(name=roleCode),
        )

    roleDefinitions = {
        "AWB": _role("AWB", "AWB", "WBL, WBR"),
        "CB": _role("CB", "CB", "DCL, DCR"),
        "DLP": _role("DLP", "DLP", "DMCL"),
        "DM": _role("DM", "DM", "DMCR"),
        "IF": _role("IF", "IF", "AML, AMR"),
        "CHF": _role("CHF", "CHF", "STC"),
        "SK": _role("SK", "SK", "GK, AMC"),
        "BGK": _role("BGK", "BGK", "GK"),
    }
    inRoles = (
        ("01", "SK", "GK"),
        ("02", "CB", "DCL"),
        ("03", "CB", "DCR"),
        ("04", "AWB", "WBL"),
        ("05", "AWB", "WBR"),
        ("06", "DLP", "DMCL"),
        ("07", "DM", "DMCR"),
        ("08", "IF", "AML"),
        ("09", "IF", "AMR"),
        ("10", "CHF", "STC"),
        ("11", "DLP", "AMC"),
    )
    outRoles = tuple(
        (slotId, "BGK" if slotId == "01" else roleCode, canonicalPosition)
        for slotId, roleCode, canonicalPosition in inRoles
    )
    tactic = SimpleNamespace(
        inPossession=SimpleNamespace(positions=tuple(position(*values) for values in inRoles)),
        outOfPossession=SimpleNamespace(positions=tuple(position(*values) for values in outRoles)),
    )

    class FakeLoader:
        def tacticLoad(self, _tacticName: str) -> SimpleNamespace:
            return SimpleNamespace(tactic=tactic)

    window = QMainWindow()
    window.tacticModelLoader = FakeLoader()  # type: ignore[attr-defined]
    view = SquadDetailView(window)
    window.setCentralWidget(view)
    qtbot.addWidget(window)
    view.model = SquadDetailModel(
        squad=_squad(),
        tacticName="High Press",
        availableTactics=("High Press",),
        sourceStatus="Generated from screenshot evidence",
        updated="15 Aug 2026 22:00",
        requiredPositionCount=11,
        roles=tuple(roleDefinitions.values()),
    )

    rows = view._requiredRoleRows()

    assert len(rows) == 11
    assert sum(label.startswith("AWB ·") for label, _coverage in rows) == 2
    assert rows[0][0].startswith("IP SK / OOP BGK · GK")


def testRoleCandidateKeepsSelectedFitSeparateFromBestRoleAndUsesCompactEvidence(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Comparison rows keep selected fit, best role and concise percentage evidence separate."""

    candidate = CandidateDisplay(
        name="Ada Player",
        positions="D (C)",
        score="61.5",
        bestRole="Inside Forward",
        breakdown="concentration: 12 × 3 = 36/60; off_the_ball: 14 × 4 = 56/80",
        available=True,
    )
    role = RoleDisplay(
        roleCode="centreBack",
        displayName="Centre-Back",
        abbreviation="CB",
        positions="DC",
        phases="Out Of Possession",
        coverage="Best: Ada Player · no calculated backup",
        candidates=(candidate,),
    )
    attributes = (
        AttributeDefinition("concentration", "Cnt", 1),
        AttributeDefinition("off_the_ball", "OtB", 2),
    )
    tab = SquadRolesTab((role,), attributes)
    qtbot.addWidget(tab)
    qtbot.wait(1)

    assert tab.candidateTable.item(0, 2).text() == "61.5"
    assert tab.candidateTable.item(0, 3).text() == "Inside Forward"
    assert tab.candidateTable.item(0, 4).text() == "Cnt: 60%, OtB: 70%"
    assert "36/60" in tab.candidateTable.item(0, 4).toolTip()
    assert tab.candidateTable.rowHeight(0) == 28
    assert tab.rolePaneTitle.text() == "Tactic Roles"
    assert tab.candidatePaneTitle.text() == "Candidates for Selected Role"
    assert tab.playerRoleTitle.text() == "Player Role Assessment"
    assert tab.playerPicker.maximumWidth() == 320


def testPlayerPickerDisplaysAndSortsNamesBySurname(qtbot) -> None:  # type: ignore[no-untyped-def]
    candidates = tuple(
        CandidateDisplay(
            name=name,
            positions="D (C)",
            score="60.0",
            bestRole="Centre-Back",
            breakdown="tackling: 12 × 5 = 60/100",
            available=True,
        )
        for name in ("Georgia Stanway", "Ada Player", "N. Eizagirre")
    )
    role = RoleDisplay(
        roleCode="centreBack",
        displayName="Centre-Back",
        abbreviation="CB",
        positions="DC",
        phases="Out Of Possession",
        coverage="Available",
        candidates=candidates,
    )
    tab = SquadRolesTab((role,))
    qtbot.addWidget(tab)

    assert [tab.playerPicker.itemText(index) for index in range(tab.playerPicker.count())] == [
        "Select a player…",
        "Eizagirre, N.",
        "Player, Ada",
        "Stanway, Georgia",
    ]
    assert [tab.playerPicker.itemData(index) for index in range(1, tab.playerPicker.count())] == [
        "N. Eizagirre",
        "Ada Player",
        "Georgia Stanway",
    ]

    tab.playerPicker.setCurrentIndex(2)
    assert tab.playerRoleTable.rowCount() == 1


def testAnalysisBreakdownAndEvidenceRowsStayCompact(qtbot) -> None:  # type: ignore[no-untyped-def]
    model = SquadDetailModel(
        squad=_squad(),
        tacticName="High Press",
        availableTactics=("High Press",),
        sourceStatus="Generated from screenshot evidence",
        updated="15 Aug 2026 22:00",
        requiredPositionCount=0,
        roles=(),
        playerRoles=(
            PlayerRoleDisplay(
                name="Ada Player",
                bestRole="Inside Forward",
                bestScore="72.0",
                bestBreakdown="concentration: 12 × 3 = 36/60; off_the_ball: 14 × 4 = 56/80",
                alternatives="Winger",
            ),
        ),
        findings=(
            AnalysisFindingDisplay(
                "Weak position",
                "Centre-Back",
                "Only one player has sufficient evidence for this role and the explanation is deliberately long.",
            ),
        ),
    )
    attributes = (
        AttributeDefinition("concentration", "Cnt", 1),
        AttributeDefinition("off_the_ball", "OtB", 2),
    )
    tab = SquadAnalysisTab(model, attributes)
    qtbot.addWidget(tab)
    qtbot.wait(1)

    assert tab.playerTable.rowHeight(0) == 28
    assert tab.findingsTable.rowHeight(0) == 28
    assert "Cnt:" in tab.playerTable.item(0, 3).text()
    assert "OtB:" in tab.playerTable.item(0, 3).text()
    assert tab.findingsTable.item(0, 2).toolTip()


def testUnassignedSquadPickerListsSystemTacticsAndPersistsSelection(qtbot) -> None:  # type: ignore[no-untyped-def]
    class FakeDatabase:
        def __init__(self) -> None:
            self.applied: list[tuple[str, str]] = []

        def tacticsList(self) -> list[str]:
            return ["Control", "High Press"]

        def tacticApplyToSquad(self, squadName: str, tacticName: str) -> object:
            self.applied.append((squadName, tacticName))
            return object()

    window = QMainWindow()
    window.database = FakeDatabase()  # type: ignore[attr-defined]
    view = SquadDetailView(window)
    window.setCentralWidget(view)
    qtbot.addWidget(window)
    model = SquadDetailModel(
        squad=_squad(),
        tacticName="No tactic selected",
        availableTactics=(),
        sourceStatus="Generated from screenshot evidence",
        updated="15 Aug 2026 22:00",
        requiredPositionCount=0,
        roles=(),
    )

    view.squadShow("First Team", model)

    assert [view.tacticPicker.itemText(index) for index in range(view.tacticPicker.count())] == [
        "No tactic assigned",
        "Control",
        "High Press",
    ]
    assert view.tacticPicker.styleSheet() == ""
    assert view.tacticPicker.view().styleSheet() == ""
    view.tacticPicker.setCurrentText("High Press")
    assert window.database.applied == [("First Team", "High Press")]  # type: ignore[attr-defined]


def testAssignedTacticCardRequestsTacticWorkspace(qtbot) -> None:  # type: ignore[no-untyped-def]
    window = QMainWindow()
    view = SquadDetailView(window)
    window.setCentralWidget(view)
    qtbot.addWidget(window)
    requested = QSignalSpy(view.tacticRequested)
    model = SquadDetailModel(
        squad=_squad(),
        tacticName="High Press",
        availableTactics=("High Press",),
        sourceStatus="Generated from screenshot evidence",
        updated="15 Aug 2026 22:00",
        requiredPositionCount=0,
        roles=(),
    )

    view.squadShow("First Team", model)
    assert view.tacticCard.objectName() == "factCard"
    qtbot.mouseClick(view.tacticCard, Qt.MouseButton.LeftButton)

    assert requested.count() == 1
    assert requested.at(0) == ["High Press"]
