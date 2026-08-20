from unittest.mock import patch

from fmsat.main import main


def testMainHelp(capsys) -> None:  # type: ignore[no-untyped-def]

    assert main(["--help"]) == 0

    output = capsys.readouterr().out
    assert "fmsat parser --help" in output


def testMainDispatchesParser() -> None:

    with patch("fmsat.cli.main", return_value=7) as parserMain:
        assert main(["parser", "inspect", "sample.fmf"]) == 7

    parserMain.assert_called_once_with(["inspect", "sample.fmf"])


def testMainRejectsUnknownCommand(capsys) -> None:  # type: ignore[no-untyped-def]

    assert main(["unknown"]) == 2
    assert "unknown command: unknown" in capsys.readouterr().err
