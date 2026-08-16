"""Regression tests for historical OCR-zone geometry."""

from __future__ import annotations

from sqlalchemy import create_engine as createEngine

from fmsat.core.config import Configuration
from fmsat.core.ocrZoneHistory import OcrZoneDriftClassifier, OcrZoneGeometry
from fmsat.database.ocrZoneHistory import OcrZoneHistoryStore


def _geometry(x: float = 0.20, y: float = 0.15) -> OcrZoneGeometry:
    return OcrZoneGeometry(x, y, 0.59, 0.68)


def testDriftIsUnavailableUntilEnoughValidatedHistoryExists() -> None:
    classifier = OcrZoneDriftClassifier(minimumHistory=5)

    result = classifier.classify(_geometry(), (_geometry(),) * 4)

    assert result.state == "unavailable"
    assert result.score is None
    assert result.historyCount == 4


def testMedianMadSeparatesNormalDriftAndAnomaly() -> None:
    classifier = OcrZoneDriftClassifier(
        minimumHistory=5,
        normalScoreMax=3.5,
        driftingScoreMax=6.0,
        minimumScale=0.002,
    )
    history = tuple(
        _geometry(x, y)
        for x, y in (
            (0.200, 0.150),
            (0.201, 0.149),
            (0.199, 0.151),
            (0.202, 0.150),
            (0.200, 0.152),
            (0.201, 0.151),
        )
    )

    normal = classifier.classify(_geometry(0.202, 0.151), history)
    drifting = classifier.classify(_geometry(0.209, 0.151), history)
    anomalous = classifier.classify(_geometry(0.240, 0.151), history)

    assert normal.state == "normal"
    assert drifting.state == "drifting"
    assert anomalous.state == "anomalous"
    assert anomalous.score is not None
    assert anomalous.delta is not None
    assert anomalous.delta.x > 0.03


def testAnomalousObservationIsRetainedButNeverLearnsBaseline() -> None:
    engine = createEngine("sqlite:///:memory:", future=True)
    store = OcrZoneHistoryStore(engine)
    classifier = OcrZoneDriftClassifier(minimumHistory=5, minimumScale=0.002)

    for offset in (0.000, 0.001, -0.001, 0.002, -0.002):
        result = store.observe(
            "tactic-in-possession",
            "instructionModal",
            "instructionPanel",
            _geometry(0.20 + offset, 0.15),
            classifier,
            validated=True,
        )
        assert result.state == "unavailable"

    anomaly = store.observe(
        "tactic-in-possession",
        "instructionModal",
        "instructionPanel",
        _geometry(0.30, 0.15),
        classifier,
        validated=True,
    )

    assert anomaly.state == "anomalous"
    history = store.history(
        "tactic-in-possession", "instructionModal", "instructionPanel"
    )
    assert len(history) == 5
    assert all(item.geometry.x < 0.21 for item in history)


def testUnvalidatedObservationNeverLearnsBaseline() -> None:
    engine = createEngine("sqlite:///:memory:", future=True)
    store = OcrZoneHistoryStore(engine)
    classifier = OcrZoneDriftClassifier(minimumHistory=5)

    store.observe(
        "tactic-out-of-possession",
        "instructionModal",
        "instructionPanel",
        _geometry(),
        classifier,
        validated=False,
    )

    assert store.history(
        "tactic-out-of-possession", "instructionModal", "instructionPanel"
    ) == ()


def _expectedRegions(
    rows: tuple[tuple[str, ...], ...],
    rowY: tuple[float, ...],
    height: float,
) -> dict[str, dict[str, float]]:
    xValues = (0.012, 0.177, 0.342, 0.507, 0.672, 0.838)
    result = {}
    for y, categories in zip(rowY, rows, strict=True):
        for x, category in zip(xValues, categories):
            result[category] = {"x": x, "y": y, "width": 0.149, "height": height}
    return result


def testAcceptedTacticGeometryIsAnExplicitRegressionContract() -> None:
    """Moving any known-good normalized zone requires an intentional test update."""

    configuration = Configuration().tacticExtraction
    profiles = {
        profile["name"]: profile for profile in configuration["phaseRegionProfiles"]
    }
    assert profiles["compactTwoPitch"]["regions"] == {
        "inPossession": {"x": 0.026, "y": 0.227, "width": 0.484, "height": 0.700},
        "outOfPossession": {"x": 0.522, "y": 0.227, "width": 0.474, "height": 0.700},
    }
    assert profiles["widePlannerWithSquad"]["regions"] == {
        "inPossession": {"x": 0.024, "y": 0.218, "width": 0.271, "height": 0.550},
        "outOfPossession": {"x": 0.317, "y": 0.218, "width": 0.271, "height": 0.550},
    }

    expectedInPossession = _expectedRegions(
        (
            (
                "passingDirectness",
                "tempo",
                "timeWasting",
                "attackingTransition",
                "attackingWidth",
                "playForSetPieces",
            ),
            (
                "creativeFreedom",
                "buildUpStrategy",
                "goalKicks",
                "goalkeeperDistribution",
                "supportingRuns",
                "dribbling",
            ),
            (
                "progressThrough",
                "passReception",
                "patience",
                "shotsFromDistance",
                "crossingStyle",
                "goalkeeperDistributionSpeed",
            ),
        ),
        (0.172, 0.450, 0.729),
        0.252,
    )
    expectedOutOfPossession = _expectedRegions(
        (
            (
                "lineOfEngagement",
                "defensiveLine",
                "triggerPress",
                "defensiveTransition",
                "tackling",
                "crossEngagement",
            ),
            (
                "pressingTrap",
                "shortGoalkeeperDistribution",
                "defensiveLineBehaviour",
            ),
        ),
        (0.234, 0.622),
        0.349,
    )

    instructionRegions = configuration["instructionPanelRegions"]
    assert instructionRegions["inPossession"] == expectedInPossession
    assert instructionRegions["outOfPossession"] == expectedOutOfPossession
