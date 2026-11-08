"""Unified command-line entry point."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from sphinxcontrib import matlab_cli
from sphinxcontrib.matlab_apidoc import _cli as apidoc
from sphinxcontrib.matlab_quickstart import _cli as quickstart


@pytest.fixture(autouse=True)
def _plain_help(monkeypatch):
    monkeypatch.setenv("PYTHON_COLORS", "0")  # argparse colors help from Python 3.14


@pytest.mark.parametrize("command", ["scmd", "sphinxcontrib-matlabdomain"])
def test_installed_entry_point(command):
    executable = Path(sys.executable).parent / (
        command + (".exe" if os.name == "nt" else "")
    )
    for args in (["--version"], ["apidoc", "--help"], ["quickstart", "--help"]):
        result = subprocess.run(
            [str(executable), *args], capture_output=True, text=True, check=False
        )
        assert result.returncode == 0, result.stderr
        assert command in result.stdout


@pytest.mark.parametrize("command", ["apidoc", "quickstart"])
def test_subcommand_help(command, capsys):
    with pytest.raises(SystemExit) as exc:
        matlab_cli.main([command, "--help"])
    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert f"usage: scmd {command}" in output
    assert "-V, --version" in output


def test_root_help_and_errors(capsys):
    with pytest.raises(SystemExit) as exc:
        matlab_cli.main(["--help"])
    assert exc.value.code == 0
    assert "{apidoc,quickstart}" in capsys.readouterr().out
    for args in ([], ["unknown"], ["apidoc", "--unknown"]):
        with pytest.raises(SystemExit) as exc:
            matlab_cli.main(args)
        assert exc.value.code == 2


def test_short_and_long_options():
    for parser in (apidoc.get_parser(), quickstart.get_parser()):
        for action in parser._actions:
            if action.option_strings:
                assert any(option.startswith("--") for option in action.option_strings)
                assert any(
                    option.startswith("-") and not option.startswith("--")
                    for option in action.option_strings
                )
    assert apidoc.get_parser().parse_args(["-k", "-f", "-n", "-q", "-c", "docs"]) == (
        apidoc.get_parser().parse_args(
            ["--check", "--force", "--dry-run", "--quiet", "--conf-dir", "docs"]
        )
    )
    assert quickstart.get_parser().parse_args(
        ["-f", "-n", "-q", "-o", "docs", "-a", "answers.toml"]
    ) == quickstart.get_parser().parse_args(
        [
            "--force",
            "--dry-run",
            "--quiet",
            "--output-dir",
            "docs",
            "--answers",
            "answers.toml",
        ]
    )


def test_subcommands_run(tmp_path, capsys):
    assert matlab_cli.main(["apidoc", "--conf-dir", str(tmp_path)]) == 2
    assert "scmd apidoc: error:" in capsys.readouterr().err
    assert matlab_cli.main(["quickstart", str(tmp_path / "missing"), "--quiet"]) == 2
    assert "scmd quickstart: error:" in capsys.readouterr().err
