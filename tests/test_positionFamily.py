from fmsat.tactics.positionFamily import (
    PositionFamily,
    playerPositionFamilies,
    positionFamilyFor,
)


def testExactTacticPositionsCollapseToPositionFamilies() -> None:
    expected = {
        "GK": PositionFamily.GK,
        "DL": PositionFamily.FB,
        "DR": PositionFamily.FB,
        "WBL": PositionFamily.WB,
        "WBR": PositionFamily.WB,
        "DCL": PositionFamily.DC,
        "DC": PositionFamily.DC,
        "DCR": PositionFamily.DC,
        "DMCL": PositionFamily.DM,
        "DM": PositionFamily.DM,
        "DMCR": PositionFamily.DM,
        "MCL": PositionFamily.MC,
        "MC": PositionFamily.MC,
        "MCR": PositionFamily.MC,
        "ML": PositionFamily.MW,
        "MR": PositionFamily.MW,
        "AMCL": PositionFamily.AMC,
        "AMC": PositionFamily.AMC,
        "AMCR": PositionFamily.AMC,
        "AML": PositionFamily.AMW,
        "AMR": PositionFamily.AMW,
        "STCL": PositionFamily.STC,
        "STC": PositionFamily.STC,
        "STCR": PositionFamily.STC,
    }

    assert {code: positionFamilyFor(code) for code in expected} == expected


def testNaturalPlayerPositionsUseTheSameFamilies() -> None:
    assert playerPositionFamilies("D (RL)") == {PositionFamily.FB}
    assert playerPositionFamilies("D (RLC)") == {
        PositionFamily.FB,
        PositionFamily.DC,
    }
    assert playerPositionFamilies("D/WB (R)") == {
        PositionFamily.FB,
        PositionFamily.WB,
    }
    assert playerPositionFamilies("M/AM (RL)") == {
        PositionFamily.MW,
        PositionFamily.AMW,
    }
    assert playerPositionFamilies("M/AM (C)") == {
        PositionFamily.MC,
        PositionFamily.AMC,
    }
    assert playerPositionFamilies("ST (C)") == {PositionFamily.STC}


def testUnknownPositionDoesNotInventAFamily() -> None:
    assert positionFamilyFor("XYZ") is None
    assert playerPositionFamilies("XYZ") == frozenset()
