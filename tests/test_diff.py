from fmparser.diff import changed_bytes, group_changes


def test_changed_bytes_handles_replacements_and_growth() -> None:
    changes = changed_bytes(b"abc", b"axcd")

    assert [(item.offset, item.old, item.new) for item in changes] == [
        (1, ord("b"), ord("x")),
        (3, None, ord("d")),
    ]


def test_group_changes_clusters_nearby_offsets() -> None:
    groups = group_changes(changed_bytes(bytes([1, 2, 3, 4]), bytes([1, 9, 8, 4])))

    assert len(groups) == 1
    assert groups[0].start == 1
    assert groups[0].end == 2
