import json
from pathlib import Path

from fmparser.cli import main


def testCliNoArgumentsShowsHelp(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main([]) == 2
    output = capsys.readouterr().out

    assert "--tactic" in output
    assert "--unity" in output


def testCliTacticPathCanBeStoredAsDefault(
    tmp_path: Path,
    monkeypatch,  # type: ignore[no-untyped-def]
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    config = tmp_path / "config.json"
    sample = tmp_path / "sample.fmf"
    sample.write_bytes(b"abcdef")
    monkeypatch.setenv("FMPARSER_CONFIG", str(config))

    assert main(["--tactic", str(sample)]) == 0
    output = capsys.readouterr().out

    assert "Default tactic:" in output
    assert json.loads(config.read_text(encoding="utf-8"))["tactic"] == str(sample.resolve())


def testCliInspectUsesConfiguredTactic(
    tmp_path: Path,
    monkeypatch,  # type: ignore[no-untyped-def]
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    config = tmp_path / "config.json"
    sample = tmp_path / "sample.fmf"
    sample.write_bytes(b"abcdef")
    config.write_text(json.dumps({"tactic": str(sample)}), encoding="utf-8")
    monkeypatch.setenv("FMPARSER_CONFIG", str(config))

    assert main(["--inspect"]) == 0
    output = capsys.readouterr().out

    assert "Filename:" in output
    assert str(sample) in output


def testCliSaveStoresTacticWhileRunningAction(
    tmp_path: Path,
    monkeypatch,  # type: ignore[no-untyped-def]
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    config = tmp_path / "config.json"
    sample = tmp_path / "sample.fmf"
    sample.write_bytes(b"abcdef")
    monkeypatch.setenv("FMPARSER_CONFIG", str(config))

    assert main(["--tactic", str(sample), "--save", "--inspect"]) == 0
    output = capsys.readouterr().out

    assert "Filename:" in output
    assert json.loads(config.read_text(encoding="utf-8"))["tactic"] == str(sample.resolve())


def testCliCompareUsesFlagLedWorkflow(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    old = tmp_path / "old.fmf"
    new = tmp_path / "new.fmf"
    old.write_bytes(b"abc")
    new.write_bytes(b"abd")

    assert main(["--tactic", str(old), "--compare", str(new)]) == 0
    output = capsys.readouterr().out

    assert "Binary Diff" in output
    assert str(old) in output
    assert str(new) in output


def testCliRejectsMixedTacticAndUnityModes(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    sample = tmp_path / "sample.fmf"
    sample.write_bytes(b"abc")

    assert main(["--tactic", str(sample), "--unity", str(sample), "--list"]) == 1
    error = capsys.readouterr().err

    assert "Choose either tactic options or Unity options" in error
