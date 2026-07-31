"""Screenshot requirement planning tests."""

from fmsat.core.detection import ScreenType
from fmsat.core.requirements import TacticScreenshotPlanner


def _plannerCreate() -> TacticScreenshotPlanner:
    return TacticScreenshotPlanner.fromMapping(
        {
            "required_screens": [
                {
                    "type": "SQUAD_ATTRIBUTES",
                    "title": "Squad Attributes",
                    "instructions": "Show the full player table.",
                }
            ]
        }
    )


def testNewTacticListsRequiredScreenshot() -> None:
    plan = _plannerCreate().plan("High Press", set())

    assert not plan.isComplete
    assert [item.screenType for item in plan.missing] == [ScreenType.SQUAD_ATTRIBUTES]


def testRecognisedTacticDoesNotRequireCompletedScreenshot() -> None:
    plan = _plannerCreate().plan("High Press", {ScreenType.SQUAD_ATTRIBUTES})

    assert plan.isComplete
    assert [item.screenType for item in plan.completed] == [ScreenType.SQUAD_ATTRIBUTES]
