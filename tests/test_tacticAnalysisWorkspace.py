"""Tactic Analysis tab presentation for requirement 011."""

from unittest.mock import Mock

from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QLabel, QPushButton, QTableWidget

from fmsat.app.tacticAnalysisDisplay import tacticAnalysisDisplayBuild
from fmsat.app.tacticAnalysisWorkspace import AnalysisTab
from fmsat.app.tacticDetailView import TacticDetailView
from fmsat.app.window import MainWindow
from fmsat.core.config import Configuration
from fmsat.core.parser import TacticVocabulary
from fmsat.core.tacticAnalysis import TacticAnalysisService
from fmsat.football.role import Role
from fmsat.football.roleIdentity import RoleIdentity
from fmsat.football.roleProfile import RoleProfile
from fmsat.tactics.formation import Formation
from fmsat.tactics.position import Position
from fmsat.tactics.positionIdentity import PositionIdentity
from fmsat.tactics.tactic import Tactic


class _Knowledge:
    def __init__(self, weights: dict[str, dict[str, int]]) -> None:
        self.weights = weights

    def weightsLoad(self, roleIdentity: str | int) -> dict[str, int]:
        return dict(self.weights.get(str(roleIdentity), {}))

    def definitionsList(self) -> tuple[object, ...]:
        return ()


def _position(
    slotId: str,
    identity: str,
    roleCode: str | None,
    *,
    footballer: str = "Must not be consumed",
) -> Position:
    return Position(
        identity=PositionIdentity[identity],
        role=Role(RoleIdentity.UNRESOLVED),
        roleProfile=RoleProfile(name="Observed role"),
        slotId=slotId,
        canonicalPosition=identity,
        canonicalRole=roleCode,
        player=footballer,
    )


def _tactic(ip: tuple[Position, ...], oop: tuple[Position, ...] = ()) -> Tactic:
    return Tactic(
        name="High Press",
        inPossession=Formation(name="IP", positions=list(ip)),
        outOfPossession=Formation(name="OOP", positions=list(oop)),
    )


def _analysis(weights: dict[str, dict[str, int]], tactic: Tactic):
    return TacticAnalysisService(
        TacticVocabulary(),
        _Knowledge(weights),  # type: ignore[arg-type]
        Configuration().activeAttributes,
        "fm26-generic-role-fit-v1",
    ).analysisBuild(tactic)


def testAnalysisDisplayMapsFamilyChangeAndUnavailablePhaseDemand() -> None:
    analysis = _analysis(
        {
            "insideForward": {"dribbling": 4, "finishing": 5},
            "trackingWideMidfielder": {},
        },
        _tactic(
            (_position("slot-wide", "AML", "insideForward", footballer="Alpha"),),
            (_position("slot-wide", "ML", "trackingWideMidfielder", footballer="Bravo"),),
        ),
    )
    assert analysis is not None
    display = tacticAnalysisDisplayBuild(analysis)

    assert display.slots[0].position == "AML → ML"
    assert display.slots[0].transition.startswith("Family change")
    assert "Alpha" not in display.slots[0].ipRole
    finishing = next(row for row in display.demand if row.attribute == "Finishing")
    assert finishing.inPossession == "5"
    assert finishing.outOfPossession == "Unavailable"


def testAnalysisTabEmptyShellOmitsPrototypeGenerateButton(qtbot) -> None:  # type: ignore[no-untyped-def]
    tab = AnalysisTab()
    qtbot.addWidget(tab)
    labels = [label.text() for label in tab.findChildren(QLabel)]

    assert "Analysis Is Ready When You Are" in labels
    assert "Generate analysis" not in [button.text() for button in tab.findChildren(QPushButton)]
    assert tab.findChild(QTableWidget, "tacticRoleRequirementsTable") is None


def testAnalysisTabShowsDemandDashboardWithoutSquadContent(qtbot) -> None:  # type: ignore[no-untyped-def]
    analysis = _analysis(
        {
            "insideForward": {"dribbling": 4, "work_rate": 0},
            "trackingAttackingMidfielder": {"work_rate": 5, "stamina": 5},
        },
        _tactic(
            (_position("slot-amc", "AMC", "insideForward", footballer="Freigang, Laura"),),
            (
                _position(
                    "slot-amc",
                    "AMC",
                    "trackingAttackingMidfielder",
                    footballer="Hemp, Lauren",
                ),
            ),
        ),
    )
    tab = AnalysisTab(analysis)
    qtbot.addWidget(tab)

    requirements = tab.findChild(QTableWidget, "tacticRoleRequirementsTable")
    demand = tab.findChild(QTableWidget, "tacticDemandTable")
    observations = tab.findChild(QTableWidget, "tacticObservationsTable")
    texts = [
        requirements.item(row, column).text()
        for row in range(requirements.rowCount())
        for column in range(requirements.columnCount())
    ]
    texts.extend(
        demand.item(row, column).text()
        for row in range(demand.rowCount())
        for column in range(demand.columnCount())
    )
    headers = [
        requirements.horizontalHeaderItem(column).text()
        for column in range(requirements.columnCount())
    ]

    assert requirements is not None and demand is not None and observations is not None
    assert tab.findChild(QPushButton, "reanalyseTacticButton") is None
    assert "Best XI" not in texts
    assert "Selected Player" not in headers
    assert "Primary" not in headers
    assert "Freigang" not in "".join(texts)
    assert "Hemp" not in "".join(texts)
    workRate = next(
        row for row in range(demand.rowCount()) if demand.item(row, 0).text() == "Work Rate"
    )
    assert demand.item(workRate, 1).text() == "5"
    assert demand.item(workRate, 2).text() == "0"
    assert demand.item(workRate, 3).text() == "5"


def testAnalysisTabShowsUnavailableWhenNoCompleteWeights(qtbot) -> None:  # type: ignore[no-untyped-def]
    analysis = _analysis({}, _tactic((_position("slot-one", "AML", None),)))
    tab = AnalysisTab(analysis)
    qtbot.addWidget(tab)

    assert tab.findChild(QTableWidget, "tacticDemandTable") is None
    assert any(label.text() == "Unavailable" for label in tab.findChildren(QLabel))
    requirements = tab.findChild(QTableWidget, "tacticRoleRequirementsTable")
    assert requirements.item(0, 4).text() == "Unresolved role"


def testReanalyseEmitsWithoutChangingCoreResult(qtbot) -> None:  # type: ignore[no-untyped-def]
    analysis = _analysis(
        {"insideForward": {"dribbling": 4}},
        _tactic((_position("slot-one", "AML", "insideForward"),)),
    )
    view = TacticDetailView()
    qtbot.addWidget(view)
    view.tacticShow("High Press", analysis=analysis)
    spy = QSignalSpy(view.reanalyseRequested)

    qtbot.mouseClick(view.reanalyseButton, Qt.MouseButton.LeftButton)

    assert spy.count() == 1
    assert view.reanalyseButton.isEnabled()
    assert view.reanalyseButton.toolTip().startswith("Recalculate tactic demand")
    assert "Does not regenerate screenshots" in view.reanalyseButton.toolTip()


def testTacticFooterButtonsShareSizeAndRow(qtbot) -> None:  # type: ignore[no-untyped-def]
    analysis = _analysis(
        {"insideForward": {"dribbling": 4}},
        _tactic((_position("slot-one", "AML", "insideForward"),)),
    )
    view = TacticDetailView()
    qtbot.addWidget(view)
    view.tacticShow("High Press", analysis=analysis)
    view.show()
    qtbot.waitExposed(view)

    buttons = (view.editModelButton, view.importToModelButton, view.reanalyseButton)
    widths = {button.width() for button in buttons}
    tops = {button.mapTo(view, button.rect().topLeft()).y() for button in buttons}

    assert len(widths) == 1
    assert len(tops) == 1
    assert view.reanalyseButton.text() == "Reanalyse Tactic"


def testTacticDetailViewShowsAnalysisOnNamedTab(qtbot) -> None:  # type: ignore[no-untyped-def]
    analysis = _analysis(
        {"insideForward": {"dribbling": 4}},
        _tactic((_position("slot-one", "AML", "insideForward"),)),
    )
    view = TacticDetailView()
    qtbot.addWidget(view)
    view.tacticShow("High Press", analysis=analysis)
    analysisIndex = next(
        index for index in range(view.tabs.count()) if view.tabs.tabText(index) == "Analysis"
    )
    view.tabs.setCurrentIndex(analysisIndex)

    assert view.analysisTab.findChild(QTableWidget, "tacticRoleRequirementsTable") is not None
    assert view.analysisTab.findChild(QLabel, "emptyTitle") is None


def testMainWindowReanalyseReloadsSavedModelWithoutOcr(qtbot) -> None:  # type: ignore[no-untyped-def]
    tactic = _tactic((_position("slot-one", "AML", "insideForward"),))
    analysis = _analysis({"insideForward": {"dribbling": 4}}, tactic)
    window = MainWindow(Mock(), Mock(), (), Mock(), Mock(), Mock())
    qtbot.addWidget(window)
    window.database.tacticDetailRecord.return_value = Mock(assignedSquads=(), updatedAt=None)
    window.tacticModelLoader = Mock()
    window.tacticModelLoader.tacticLoad.return_value = Mock(
        tactic=tactic,
        issues=(),
        source="objectModel",
        complete=True,
        confirmed=True,
        metadata={},
        phaseSlots=None,
        stale=False,
    )
    window.tacticAnalysisService = Mock()
    window.tacticAnalysisService.analysisBuild.return_value = analysis
    window.tacticScreenshotExtractor = Mock()
    window.currentTacticModel = tactic
    window.tacticDetailView.tacticName = tactic.name
    window.tacticDetailView.selectedTabName = "Analysis"

    window._tacticAnalyse()

    window.tacticScreenshotExtractor.assert_not_called()
    window.tacticAnalysisService.analysisBuild.assert_called_with(tactic)
    assert (
        window.tacticDetailView.analysisTab.findChild(QTableWidget, "tacticRoleRequirementsTable")
        is not None
    )
    assert (
        window.tacticDetailView.tabs.tabText(window.tacticDetailView.tabs.currentIndex())
        == "Analysis"
    )
