"""Opt-in final clean-room acceptance gate for requirement 007B."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from fmsat.app.squadDetailModel import RoleDisplay
from fmsat.app.squadRolesWorkspace import SquadRolesTab


FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "roleKnowledge"


def _confirmedFixturesRequired() -> tuple[dict[str, object], ...]:
    fixtures = []
    for path in sorted(FIXTURE_DIRECTORY.glob("*.expected.yaml")):
        content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        assert isinstance(content, dict)
        fixtures.append(content)
    return tuple(fixtures)


def _finalGateEnabled() -> bool:
    return os.environ.get("FMSAT_007B_FINAL", "").strip() == "1"


@pytest.mark.skipif(not _finalGateEnabled(), reason="Set FMSAT_007B_FINAL=1 for the 007B clean-room gate")
def testCleanRoomExpectedRoleKnowledgeContainsNoUnknowns() -> None:
    """007B cannot close while any known role fixture is unresolved or lacks assessment data."""

    fixtures = _confirmedFixturesRequired()
    assert fixtures
    for fixture in fixtures:
        roleCode = str(fixture.get("roleCode") or "")
        assert fixture.get("confirmationState") == "confirmed", f"{roleCode} is still unresolved"
        definition = fixture.get("expectedDefinition")
        requirements = fixture.get("expectedRequirements")
        assert isinstance(definition, dict), f"{roleCode} has no expected definition YAML"
        assert isinstance(requirements, dict), f"{roleCode} has no expected requirements YAML"
        abbreviations = definition.get("abbreviations")
        assert isinstance(abbreviations, list) and abbreviations, f"{roleCode} has no abbreviation"
        assert all(str(value).strip().casefold() != "unknown" for value in abbreviations)
        weights = requirements.get("attributeWeights")
        assert isinstance(weights, dict) and weights, f"{roleCode} has no explicit assessment weights"


@pytest.mark.skipif(not _finalGateEnabled(), reason="Set FMSAT_007B_FINAL=1 for the 007B clean-room gate")
def testCleanRoomResolvedRolesDoNotRenderUnknownInRolesWorkspace(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Confirmed golden role knowledge must remove Unknown from the visible tactic-role cells."""

    roles = []
    for fixture in _confirmedFixturesRequired():
        definition = fixture.get("expectedDefinition")
        assert isinstance(definition, dict)
        abbreviations = definition.get("abbreviations")
        assert isinstance(abbreviations, list) and abbreviations
        phases = []
        if definition.get("inPossession") is True:
            phases.append("In Possession")
        if definition.get("outOfPossession") is True:
            phases.append("Out Of Possession")
        roles.append(
            RoleDisplay(
                roleCode=str(fixture["roleCode"]),
                displayName=str(definition["displayName"]),
                abbreviation=str(abbreviations[0]),
                positions=", ".join(str(value) for value in definition.get("positions", ())),
                phases=", ".join(phases),
                coverage="Uncovered",
                candidates=(),
            )
        )

    tab = SquadRolesTab(tuple(roles))
    qtbot.addWidget(tab)

    visibleRoleCells = {
        tab.roleTable.item(row, column).text()
        for row in range(tab.roleTable.rowCount())
        for column in (0, 1)
        if tab.roleTable.item(row, column) is not None
        and tab.roleTable.item(row, column).text()
    }
    assert visibleRoleCells
    assert "Unknown" not in visibleRoleCells
