from fmsat.fmf.signatures import asciiStrings, entropy, headerInfo, sectionCandidates


def testHeaderInfoRecognizesObservedFmfPrefix() -> None:

    info = headerInfo(bytes.fromhex("02 01 61 66 65 2e 08 00 00 55 05 00 00 00 00 00"))

    assert info.version == "2.1"
    assert info.flags["signature"] == "observed-fmf-prefix"


def testAsciiStringsReturnsOffsets() -> None:

    strings = asciiStrings(b"\x00abc\x00balanced tactic\x00")

    assert strings[0].offset == 5
    assert strings[0].value == "balanced tactic"


def testEntropyRange() -> None:

    assert entropy(b"\x00" * 128) == 0.0


def testSectionCandidatesFindEmbeddedLength() -> None:

    candidates = sectionCandidates(bytes.fromhex("04 00 00 00 aa bb cc dd"))

    assert candidates[0].offset == 4
    assert candidates[0].length == 4
