from pathlib import Path

from fmsat.cli import main


def testCliHex(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    sample = tmp_path / "sample.fmf"
    sample.write_bytes(b"abcdef")

    assert main(["hex", str(sample), "--length", "6"]) == 0
    output = capsys.readouterr().out

    assert "61 62 63 64 65 66" in output
    assert "00 00" not in output
