"""Validation-widget tests for the tactic Overview tab."""

from dataclasses import dataclass

from PySide6.QtWidgets import QLabel, QTabWidget

from fmsat.app.tacticDetailView import TacticDetailView
from fmsat.app.tacticValidationWidget import TacticValidationWidget


@dataclass(frozen=True, slots=True)
class DummyIssue:
    message: str


@dataclass(frozen=True, slots=True)
class DummyFormation:
    positions: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class DummyTactic:
    inPossession: DummyFormation
    outOfPossession: DummyFormation


@dataclass(frozen=True, slots=True)
class DummyResult:
    tactic: DummyTactic | None
    issues: tuple[DummyIssue, ...]
    complete: bool
    confirmed: bool


def testOverviewContainsValidationWidget(qtbot) -> None:  # type: ignore[no-untyped-def]
    view = TacticDetailView()
    qtbot.addWidget(view)
    tabs = view.findChild(QTabWidget, "tacticTabs")

    assert tabs is not None
    assert tabs.widget(0).findChild(TacticValidationWidget) is not None


def testValidationWidgetShowsCompleteConfirmedTactic(qtbot) -> None:  # type: ignore[no-untyped-def]
    result = DummyResult(
        tactic=_tacticCreate(),
        issues=(),
        complete=True,
        confirmed=True,
    )
    widget = TacticValidationWidget(result)
    qtbot.addWidget(widget)

    labels = [label.text() for label in widget.findChildren(QLabel)]

    assert "Validated" in labels
    assert labels.count("11 of 11 positions") == 2
    assert "●  No validation issues were reported." in labels


def testValidationWidgetShowsIncompletePhase(qtbot) -> None:  # type: ignore[no-untyped-def]
    result = DummyResult(
        tactic=_tacticCreate(inPossessionCount=9),
        issues=(
            DummyIssue("inPossession has 9 mapped positions; 11 expected"),
        ),
        complete=False,
        confirmed=True,
    )
    widget = TacticValidationWidget(result)
    qtbot.addWidget(widget)

    labels = [label.text() for label in widget.findChildren(QLabel)]

    assert "Incomplete" in labels
    assert "9 of 11 positions" in labels
    assert "●  inPossession has 9 mapped positions; 11 expected" in labels


def testTacticShowRefreshesValidationResult(qtbot) -> None:  # type: ignore[no-untyped-def]
    view = TacticDetailView()
    qtbot.addWidget(view)
    result = DummyResult(
        tactic=None,
        issues=(
            DummyIssue("No structured tactic definition exists"),
        ),
        complete=False,
        confirmed=False,
    )

    view.tacticShow("Unstructured", validation=result)
    labels = [label.text() for label in view.overviewTab.validationWidget.findChildren(QLabel)]

    assert "Unable to build" in labels
    assert "●  No structured tactic definition exists" in labels


def _tacticCreate(*, inPossessionCount: int = 11) -> DummyTactic:
    return DummyTactic(
        inPossession=DummyFormation(tuple(object() for _ in range(inPossessionCount))),
        outOfPossession=DummyFormation(tuple(object() for _ in range(11))),
    )
