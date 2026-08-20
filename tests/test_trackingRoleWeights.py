"""Regression coverage for built-in tracking-role assessment policy."""

from fmsat.core.config import Configuration


def testTrackingAttackingMidfielderHasExplicitWeights() -> None:
    weights = Configuration().roleAssessmentWeights()

    tracking = weights["trackingAttackingMidfielder"]

    assert tracking["work_rate"] == 5
    assert tracking["stamina"] == 5
    assert tracking["teamwork"] == 5
    assert tracking["positioning"] == 4
    assert tracking["marking"] == 4
