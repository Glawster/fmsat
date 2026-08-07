from fmsat.diff import bytesChanged, changesGroup


def testChangedBytesHandlesReplacementsAndGrowth() -> None:

    changes = bytesChanged(b"abc", b"axcd")

    assert [(item.offset, item.old, item.new) for item in changes] == [
        (1, ord("b"), ord("x")),
        (3, None, ord("d")),
    ]


def testGroupChangesClustersNearbyOffsets() -> None:

    groups = changesGroup(bytesChanged(bytes([1, 2, 3, 4]), bytes([1, 9, 8, 4])))

    assert len(groups) == 1
    assert groups[0].start == 1
    assert groups[0].end == 2
