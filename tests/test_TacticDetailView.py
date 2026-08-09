"""Tactic detail prototype tests for requirement 009."""

from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QHBoxLayout, QLabel, QTabWidget

from fmsat.app.tacticDetailView import PitchWidget, TacticDetailView


def testTacticDetailUsesRequiredTabOrder(qtbot) -> None:  # type: ignore[no-untyped-def]
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
