"""Presentation regressions for observed-but-unresolved tactic roles."""

from types import SimpleNamespace

from fmsat.app.squadDetailModel import RoleDisplay, _slotRoleLabel
from fmsat.app.squadRolesWorkspace import SquadRolesTab


def testObservedUnresolvedRoleKeepsFmAbbreviation(qtbot) -> None:  # type: ignore[no-untyped-def]
    role = RoleDisplay(
        roleCode="unresolved:slot-left:OOP",
        displayName="TW",
        abbreviation="TW",
        positions="AML",
        phases="OOP",
        coverage="No Candidates found",
        candidates=(),
        resolutionState="unknownRole",
        resolutionReason="Semantic role definition is not confirmed.",
    )
    tab = SquadRolesTab((role,))
    qtbot.addWidget(tab)

    assert tab.roleTable.item(0, 1).text() == "TW"
    assert tab.roleTable.item(0, 2).text() == "No Candidates found"


def testRequiredSlotUsesObservedRoleInsteadOfUnknownLabel() -> None:
    role = SimpleNamespace(
        roleCode=None,
        displayName="TW",
        abbreviation="TW",
    )

    assert _slotRoleLabel(role) == "TW"
