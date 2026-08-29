"""Tactic detail prototype tests for requirement 009."""

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMenu, QPushButton, QTabWidget

from fmsat.app.tacticDetailModel import DisplaySlot, TacticDetailModel
from fmsat.app.tacticDetailPrototype import tacticDetailPrototype
from fmsat.app.tacticDetailView import PitchWidget, TacticDetailView


def testTacticDetailUsesRequiredTabOrder(qapp, qtbot) -> None:  # type: ignore[no-untyped-def]
    view = TacticDetailView()
    qtbot.addWidget(view)

    tabs = view.findChild(QTabWidget, "tacticTabs")

    assert tabs is not None
    assert [tabs.tabText(index) for index in range(tabs.count())] == [
        "Overview",
        "Shape",
        "Instructions",
        "Analysis",
    ]


def testTacticShowRefreshesIdentityAndAssignmentSignal(qtbot) -> None:  # type: ignore[no-untyped-def]
    view = TacticDetailView()
    qtbot.addWidget(view)
    assigned = QSignalSpy(view.assignmentRequested)

    view.tacticShow("Morphing System")
    qtbot.mouseClick(view.assignmentButton, Qt.MouseButton.LeftButton)

    assert view.titleLabel.text() == "Morphing System"
    assert assigned.count() == 1
    assert assigned.at(0) == ["Morphing System"]


def testAssignedSquadCardOpensSoleSquadDirectly(qtbot) -> None:  # type: ignore[no-untyped-def]
    view = TacticDetailView()
    qtbot.addWidget(view)
    requested = QSignalSpy(view.squadRequested)
    model = tacticDetailPrototype()
    model = replace(
        model,
        assignedSquads="First Team",
        assignedSquadNames=("First Team",),
    )

    view.tacticShow("Morphing System", model)
    assert view.assignedSquadsCard.objectName() == "factCard"
    qtbot.mouseClick(view.assignedSquadsCard, Qt.MouseButton.LeftButton)

    assert requested.count() == 1
    assert requested.at(0) == ["First Team"]


def testAssignedSquadCardOffersMenuForSeveralSquads(qtbot) -> None:  # type: ignore[no-untyped-def]
    view = TacticDetailView()
    qtbot.addWidget(view)
    requested = QSignalSpy(view.squadRequested)

    qtbot.mouseClick(view.assignedSquadsCard, Qt.MouseButton.LeftButton)
    menu = view.findChild(QMenu, "assignedSquadsMenu")

    assert menu is not None
    assert [action.text() for action in menu.actions()] == ["First Team", "U21s"]
    menu.actions()[1].trigger()
    assert requested.at(0) == ["U21s"]


def testImportToModelButtonEmitsCurrentTactic(qtbot) -> None:  # type: ignore[no-untyped-def]
    view = TacticDetailView()
    qtbot.addWidget(view)
    importRequested = QSignalSpy(view.importToModelRequested)

    view.tacticShow("Morphing System")
    qtbot.mouseClick(view.importToModelButton, Qt.MouseButton.LeftButton)

    assert importRequested.count() == 1
    assert importRequested.at(0) == ["Morphing System"]


def testShapeHasSeparatePhasePitches(qtbot) -> None:  # type: ignore[no-untyped-def]
    view = TacticDetailView()
    qtbot.addWidget(view)
    tabs = view.findChild(QTabWidget, "tacticTabs")

    assert tabs is not None
    shape = tabs.widget(1)
    headings = [label.text() for label in shape.findChildren(QLabel)]

    assert "In Possession" in headings
    assert "Out Of Possession" in headings
    assert len(shape.findChildren(PitchWidget)) == 2


def testOverviewFormationUsesFortyPercentOfResponsiveRow(qtbot) -> None:  # type: ignore[no-untyped-def]
    view = TacticDetailView()
    qtbot.addWidget(view)
    tabs = view.findChild(QTabWidget, "tacticTabs")

    assert tabs is not None
    overview = tabs.widget(0)
    pitch = overview.findChild(PitchWidget)
    layout = overview.layout()

    assert pitch is not None
    assert isinstance(layout, QHBoxLayout)
    assert layout.stretch(0) == 2
    assert layout.stretch(1) == 3
    assert pitch.minimumWidth() == 0


def testAnalysisExplainsGeneratedEmptyState(qtbot) -> None:  # type: ignore[no-untyped-def]
    view = TacticDetailView()
    qtbot.addWidget(view)
    labels = [label.text() for label in view.findChildren(QLabel)]

    assert "Analysis Is Ready When You Are" in labels
    assert any("No tactical conclusions have been generated yet" in text for text in labels)
    assert "Generate analysis" not in [button.text() for button in view.findChildren(QPushButton)]
    assert view.reanalyseButton.isEnabled() is False


def testTacticShowCanReplaceDisplayedModelData(qtbot) -> None:  # type: ignore[no-untyped-def]

    view = TacticDetailView()
    qtbot.addWidget(view)
    model = TacticDetailModel(
        formation="4-3-3",
        mentality="From model",
        status="Saved model",
        assignedSquads="First Team",
        updated="11 Aug 2026",
        revisions=("Current",),
        formationSlots=(DisplaySlot("01", "GK", "GK", "Defend", 0.5, 0.9, "goalkeeper"),),
        outOfPossessionSlots=(DisplaySlot("01", "GK", "GK", "Defend", 0.5, 0.9, "goalkeeper"),),
        summaryItems=(("Model Source", "Saved tactic model"),),
        notes="Loaded from object model.",
        instructionGroups=(("Transition", (("Counter", "On"),)),),
    )

    view.tacticShow("My Saved Model", model, sourceLabel="Saved Tactic Model")
    labels = [label.text() for label in view.findChildren(QLabel)]

    assert view.titleLabel.text() == "My Saved Model"
    assert "Tactic Workspace  ·  Saved Tactic Model" in labels
    assert "11 Aug 2026" in labels


def testOverviewShowsIncompleteDataBanner(qtbot) -> None:  # type: ignore[no-untyped-def]

    view = TacticDetailView()
    qtbot.addWidget(view)
    model = TacticDetailModel(
        formation="Unknown",
        mentality="Not available",
        status="Incomplete data",
        assignedSquads="None",
        updated="Unknown",
        revisions=("Current",),
        formationSlots=(),
        outOfPossessionSlots=(),
        summaryItems=(("Availability", "Structured tactic data is missing"),),
        notes="Missing structured/saved model data.",
        instructionGroups=(),
    )

    view.tacticShow("Incomplete Tactic", model, sourceLabel="Incomplete Data")
    labels = [label.text() for label in view.findChildren(QLabel)]

    assert "Incomplete Tactic Data" in labels
    assert any("Import and confirm tactic screenshots" in text for text in labels)
