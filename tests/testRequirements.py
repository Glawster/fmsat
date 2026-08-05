"""Screenshot requirement planning tests."""

from fmsat.core.config import Configuration
from fmsat.core.detection import ScreenType
from fmsat.core.requirements import TacticScreenshotPlanner


def _plannerCreate() -> TacticScreenshotPlanner:
    return TacticScreenshotPlanner.fromMapping(
        {
            "required_screens": [
                {
                    "type": "TACTIC_FORMATION",
                    "title": "Formation",
                    "instructions": "Show the formation.",
                },
                {
                    "type": "TACTIC_IN_POSSESSION",
                    "title": "In Possession",
                    "instructions": "Show in-possession instructions.",
                },
                {
                    "type": "TACTIC_OUT_OF_POSSESSION",
                    "title": "Out of Possession",
                    "instructions": "Show out-of-possession instructions.",
                },
                {
                    "type": "SQUAD_ATTRIBUTES",
                    "title": "Squad Attributes",
                    "instructions": "Show the full player table.",
                },
            ]
        }
    )


def testNewTacticListsRequiredScreenshot() -> None:
    plan = _plannerCreate().plan("High Press", set())

    assert not plan.isComplete
    assert [item.screenType for item in plan.missing] == [
        ScreenType.TACTIC_FORMATION,
        ScreenType.TACTIC_IN_POSSESSION,
        ScreenType.TACTIC_OUT_OF_POSSESSION,
        ScreenType.SQUAD_ATTRIBUTES,
    ]


def testRecognisedTacticDoesNotRequireCompletedScreenshot() -> None:
    plan = _plannerCreate().plan("High Press", {ScreenType.SQUAD_ATTRIBUTES})

    assert not plan.isComplete
    assert [item.screenType for item in plan.completed] == [ScreenType.SQUAD_ATTRIBUTES]


def testConfiguredTacticInstructionsExplainClipboardCapture() -> None:
    planner = TacticScreenshotPlanner.fromMapping(Configuration().screens["workflow"])
    tacticRequirements = [
        requirement
        for requirement in planner.requirements
        if requirement.screenType is not ScreenType.SQUAD_ATTRIBUTES
    ]

    assert tacticRequirements
    assert all("screenshot" in item.instructions.casefold() for item in tacticRequirements)
    assert all("clipboard" in item.instructions.casefold() for item in tacticRequirements)
