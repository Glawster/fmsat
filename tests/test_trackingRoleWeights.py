"""Regression coverage for built-in tracking-role assessment policy."""

from fmsat.core.config import Configuration


def testTrackingAttackingMidfielderHasExplicitWeights() -> None:
    weights = Configuration().roleAssessmentWeights()

    tracking = weights["trackingAttackingMidfielder"]

    assert tracking["work_rate"] == 10
    assert tracking["stamina"] == 10
    assert tracking["teamwork"] == 10
    assert tracking["positioning"] == 8
    assert tracking["marking"] == 8
