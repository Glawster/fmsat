"""Edit Tactic Model dialog uses the shared FMSAT table presentation."""

from fmsat.app.styles import stylePaletteLoad
from fmsat.app.tacticModelEditDialog import TacticModelEditDialog
from fmsat.football.role import Role
from fmsat.football.roleIdentity import RoleIdentity
from fmsat.football.roleProfile import RoleProfile
from fmsat.tactics.formation import Formation
from fmsat.tactics.position import Position
from fmsat.tactics.positionIdentity import PositionIdentity
from fmsat.tactics.tactic import Tactic


def _tactic() -> Tactic:
    position = Position(
        identity=PositionIdentity.AMC,
        role=Role(RoleIdentity.UNRESOLVED),
        roleProfile=RoleProfile(name="Observed role"),
        slotId="slot-one",
        canonicalPosition="AMC",
        canonicalRole="insideForward",
    )
    return Tactic(
        name="High Press",
        inPossession=Formation(name="IP", positions=[position]),
        outOfPossession=Formation(name="OOP", positions=[]),
    )


def testTacticModelEditTablesUseWorkspaceTableStyle(qtbot) -> None:  # type: ignore[no-untyped-def]
    dialog = TacticModelEditDialog(_tactic())
    qtbot.addWidget(dialog)
    palette = stylePaletteLoad()

    assert dialog.objectName() == "tacticModelEditDialog"
    assert dialog.objectName() != "adminEditDialog"
    assert dialog.rolesTable.objectName() == "tacticModelRolesTable"
    assert dialog.instructionsTable.objectName() == "tacticModelInstructionsTable"
    assert palette["surface"] in dialog.styleSheet()
    assert palette["accent"] in dialog.styleSheet()
    assert dialog.rolesTable.alternatingRowColors()
