import zlib

from fmsat.compression import compressionProbe


def testProbeCompressionReportsSuccess() -> None:

    payload = zlib.compress(b"football manager tactic")

    attempts = compressionProbe(payload)

    assert any(item.algorithm == "zlib" and item.success for item in attempts)
