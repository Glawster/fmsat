"""Opt-in final clean-room acceptance gate for requirement 007B."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from fmsat.app.squadDetailModel import RoleDisplay
from fmsat.app.squadRolesWorkspace import SquadRolesTab

FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "roleKnowledge"


def _fixturesRequired() -> tuple[dict[str, object], ...]:
    fixtures = []
    for path in sorted(FIXTURE_DIRECTORY.glob("*.expected.yaml")):
        content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        assert isinstance(content, dict)
        fixtures.append(content)
    return tuple(fixtures)


@pytest.mark.expensive
def testCleanRoomRoleKnowledgeRespectsEvidenceState() -> None:
    """007B must never manufacture semantic role knowledge or assessment data."""

    fixtures = _fixturesRequired()
    assert fixtures
    for fixture in fixtures:
        roleCode = str(fixture.get("roleCode") or "")
        confirmationState = fixture.get("confirmationState")
        assert confirmationState in {"confirmed", "unresolved"}

        definition = fixture.get("expectedDefinition")
        requirements = fixture.get("expectedRequirements")

        if confirmationState == "unresolved":
            observedAbbreviation = str(fixture.get("observedAbbreviation") or "")
            observedPhase = str(fixture.get("observedPhase") or "")
            assert observedAbbreviation, f"{roleCode} has no preserved observed abbreviation"
            assert observedAbbreviation.casefold() != "unknown"
            assert observedPhase in {
                "inPossession",
                "outOfPossession",
            }, f"{roleCode} has no preserved observed tactic phase"
            assert definition is None, f"{roleCode} must not invent a semantic definition"
            assert requirements is None, f"{roleCode} must not invent assessment weights"
            continue

        assert isinstance(definition, dict), f"{roleCode} has no expected definition YAML"
        assert isinstance(requirements, dict), f"{roleCode} has no expected requirements YAML"
        abbreviations = definition.get("abbreviations")
        assert isinstance(abbreviations, list) and abbreviations, f"{roleCode} has no abbreviation"
        assert all(str(value).strip().casefold() != "unknown" for value in abbreviations)
        weights = requirements.get("attributeWeights")
        assert (
            isinstance(weights, dict) and weights
        ), f"{roleCode} has no explicit assessment weights"


@pytest.mark.expensive
def testCleanRoomObservedRolesDoNotRenderUnknownInRolesWorkspace(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Observed role abbreviations remain visible in their directly observed tactic phase."""

    roles = []
    for fixture in _fixturesRequired():
        definition = fixture.get("expectedDefinition")
        if isinstance(definition, dict):
            abbreviations = definition.get("abbreviations")
            assert isinstance(abbreviations, list) and abbreviations
            displayName = str(definition["displayName"])
            abbreviation = str(abbreviations[0])
            positions = ", ".join(str(value) for value in definition.get("positions", ()))
            phases = []
            if definition.get("inPossession") is True:
                phases.append("In Possession")
            if definition.get("outOfPossession") is True:
                phases.append("Out Of Possession")
            phaseText = ", ".join(phases)
        else:
            abbreviation = str(fixture.get("observedAbbreviation") or "")
            observedPhase = str(fixture.get("observedPhase") or "")
            assert abbreviation
            assert observedPhase in {"inPossession", "outOfPossession"}
            displayName = abbreviation
            positions = "Unavailable"
            phaseText = "In Possession" if observedPhase == "inPossession" else "Out Of Possession"

        roles.append(
            RoleDisplay(
                roleCode=str(fixture["roleCode"]),
                displayName=displayName,
                abbreviation=abbreviation,
                positions=positions,
                phases=phaseText,
                coverage="No Candidates found" if definition is None else "Uncovered",
                candidates=(),
            )
        )

    tab = SquadRolesTab(tuple(roles))
    qtbot.addWidget(tab)

    visibleRoleCells = {
        tab.roleTable.item(row, column).text()
        for row in range(tab.roleTable.rowCount())
        for column in (0, 1)
        if tab.roleTable.item(row, column) is not None and tab.roleTable.item(row, column).text()
    }
    assert visibleRoleCells
    expectedObserved = {
        str(fixture.get("observedAbbreviation"))
        for fixture in _fixturesRequired()
        if fixture.get("confirmationState") == "unresolved"
    }
    assert expectedObserved <= visibleRoleCells
    assert "Unknown" not in visibleRoleCells
