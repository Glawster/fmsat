"""UI regression contracts backed by canonical tactic screenshots."""

from pathlib import Path

import pytest
import yaml
from PySide6.QtWidgets import QTabWidget

from fmsat.app.tacticDetailModel import DisplaySlot, TacticDetailModel
from fmsat.app.tacticDetailView import PitchWidget, TacticDetailView

_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "tactics"
_SCREENSHOT_ROOT = Path(__file__).parent / "screenshots" / "tactics"
_FIXTURES = ("highPress", "highPress2", "libero1974", "liberoWealdstone")


def _fixtureLoad(name: str) -> dict:
    """Load reviewed truth for one canonical screenshot set."""

    return yaml.safe_load((_FIXTURE_ROOT / f"{name}.yaml").read_text(encoding="utf-8"))


def _displaySlots(roles: list[str]) -> tuple[DisplaySlot, ...]:
    """Build deterministic UI slots while preserving reviewed role order."""

    slots = []
    for index, role in enumerate(roles):
        column = index % 4
        row = index // 4
        slots.append(
            DisplaySlot(
                slotId=f"slot-{index + 1:02d}",
                position="TEST",
                role=role,
                duty="",
                x=0.15 + (column * 0.23),
                y=0.15 + (row * 0.30),
                row="unknown",
            )
        )
    return tuple(slots)


def _modelBuild(expected: dict) -> TacticDetailModel:
    """Build the real tactic UI model from reviewed fixture truth."""

    return TacticDetailModel(
        formation="Canonical screenshot fixture",
        mentality="Fixture",
        status="Reviewed truth",
        assignedSquads="None",
        updated="Fixture",
        revisions=("Current",),
        formationSlots=_displaySlots(expected["inPossessionRoles"]),
        outOfPossessionSlots=_displaySlots(expected["outOfPossessionRoles"]),
        summaryItems=(("Evidence", "Canonical screenshot fixture"),),
        notes="Rendered from reviewed screenshot truth.",
        instructionGroups=(),
    )


@pytest.mark.parametrize("fixtureName", _FIXTURES)
def testTacticScreenshotFixtureIsComplete(fixtureName: str) -> None:
    """Every tactic fixture must contain the three immutable evidence screenshots."""

    fixture = _fixtureLoad(fixtureName)
    screenshotDirectory = _SCREENSHOT_ROOT / fixtureName

    assert fixture["fixture"] == fixtureName
    assert sorted(path.name for path in screenshotDirectory.iterdir() if path.is_file()) == [
        "formation.png",
        "inPossession.png",
        "outOfPossession.png",
    ]
    for screenshot in fixture["screenshots"].values():
        assert Path(screenshot).exists()


@pytest.mark.parametrize("fixtureName", _FIXTURES)
def testTacticFixtureDefinesElevenRolesPerPhase(fixtureName: str) -> None:
    """Reviewed formation evidence must describe all eleven simultaneous slots."""

    expected = _fixtureLoad(fixtureName)["expected"]

    assert len(expected["inPossessionRoles"]) == 11
    assert len(expected["outOfPossessionRoles"]) == 11


@pytest.mark.parametrize("fixtureName", _FIXTURES)
def testTacticShapeUiPreservesReviewedRoleOrder(fixtureName: str, qtbot) -> None:  # type: ignore[no-untyped-def]
    """The Shape tab must render phase roles in the reviewed fixture order."""

    fixture = _fixtureLoad(fixtureName)
    expected = fixture["expected"]
    view = TacticDetailView(model=_modelBuild(expected))
    qtbot.addWidget(view)
    view.tacticShow(fixtureName)

    tabs = view.findChild(QTabWidget, "tacticTabs")
    assert tabs is not None
    shape = tabs.widget(1)
    pitches = shape.findChildren(PitchWidget)

    assert len(pitches) == 2
    assert [slot.role for slot in pitches[0].slots] == expected["inPossessionRoles"]
    assert [slot.role for slot in pitches[1].slots] == expected["outOfPossessionRoles"]


def testHighPressFixturesKeepReviewedVersionDifference() -> None:
    """The two same-family fixtures must not collapse into one stale formation."""

    first = _fixtureLoad("highPress")["expected"]
    second = _fixtureLoad("highPress2")["expected"]

    assert first["outOfPossessionRoles"] == second["outOfPossessionRoles"]
    assert first["inPossessionRoles"] != second["inPossessionRoles"]
    assert "WM" in first["inPossessionRoles"]
    assert first["inPossessionRoles"].count("AWB") == 1
    assert second["inPossessionRoles"].count("AWB") == 2
