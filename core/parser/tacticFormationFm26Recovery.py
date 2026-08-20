"""FM26 position recovery for goalkeeper role labels near the DC/GK boundary."""

from __future__ import annotations

from dataclasses import replace

from fmsat.core.rolePositionCompatibility import rolePositionFamilies
from fmsat.tactics.positionFamily import PositionFamily

from .tacticFormationFm26 import TacticFormationExtractor as Fm26TacticFormationExtractor
from .tacticModels import FormationSlot, TacticalPhase, TacticIssue


class TacticFormationExtractor(Fm26TacticFormationExtractor):
    """Recover a GK slot when explicit goalkeeper-role evidence is unambiguous."""

    def _slotBuild(
        self,
        results,
        phase: TacticalPhase,
        x: float,
        y: float,
        sourceImport: str,
        index: int,
    ) -> tuple[FormationSlot, list[TacticIssue]]:
        slot, issues = super()._slotBuild(
            results,
            phase,
            x,
            y,
            sourceImport,
            index,
        )
        if (
            slot.role
            and rolePositionFamilies(slot.role) == frozenset({PositionFamily.GK})
            and slot.position != "GK"
            and 0.30 <= x <= 0.70
            and y >= 0.80
        ):
            slot = replace(slot, position="GK")
        return slot, issues
