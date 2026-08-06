from fmparser.signatures import ascii_strings, entropy, header_info, section_candidates


def test_header_info_recognizes_observed_fmf_prefix() -> None:
    info = header_info(bytes.fromhex("02 01 61 66 65 2e 08 00 00 55 05 00 00 00 00 00"))

    assert info.version == "2.1"
    assert info.flags["signature"] == "observed-fmf-prefix"


def test_ascii_strings_returns_offsets() -> None:
    strings = ascii_strings(b"\x00abc\x00balanced tactic\x00")

    assert strings[0].offset == 5
    assert strings[0].value == "balanced tactic"


def test_entropy_range() -> None:
    assert entropy(b"\x00" * 128) == 0.0


def test_section_candidates_find_embedded_length() -> None:
    candidates = section_candidates(bytes.fromhex("04 00 00 00 aa bb cc dd"))

    assert candidates[0].offset == 4
    assert candidates[0].length == 4
