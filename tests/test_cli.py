"""Unified command-line entry point."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from sphinxcontrib import matlab_cli
from sphinxcontrib.matlab_apidoc import _cli as apidoc
from sphinxcontrib.matlab_quickstart import _cli as quickstart
from sphinxcontrib.matlab_skills import _cli as skills


def parsers():
    """Every parser of the subcommands, also those of ``scmd skills``."""
    found = [apidoc.get_parser(), quickstart.get_parser()]
    top = skills.get_parser()
    found.append(top)
    for action in top._subparsers._group_actions:  # type: ignore[union-attr]
        found.extend(action.choices.values())  # type: ignore[union-attr]
    return found


@pytest.fixture(autouse=True)
def _plain_help(monkeypatch):
    monkeypatch.setenv("PYTHON_COLORS", "0")  # argparse colors help from Python 3.14


@pytest.mark.parametrize("command", ["scmd", "sphinxcontrib-matlabdomain"])
def test_installed_entry_point(command):
    executable = Path(sys.executable).parent / (
        command + (".exe" if os.name == "nt" else "")
    )
    for args, expected in (
        (["--version"], command),
        (["apidoc", "--help"], command),
        (["quickstart", "--help"], command),
        (["skills", "list"], "setting-up-a-project"),
    ):
        result = subprocess.run(
            [str(executable), *args], capture_output=True, text=True, check=False
        )
        assert result.returncode == 0, result.stderr
        assert expected in result.stdout


@pytest.mark.parametrize("command", ["apidoc", "quickstart", "skills"])
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
    assert "{apidoc,quickstart,skills}" in capsys.readouterr().out
    for args in ([], ["unknown"], ["apidoc", "--unknown"]):
        with pytest.raises(SystemExit) as exc:
            matlab_cli.main(args)
        assert exc.value.code == 2


def test_short_and_long_options():
    for parser in parsers():
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
    assert skills.get_parser().parse_args(
        ["install", "-d", "x", "-f"]
    ) == skills.get_parser().parse_args(["install", "--dest", "x", "--force"])


def test_subcommands_run(tmp_path, capsys):
    assert matlab_cli.main(["apidoc", "--conf-dir", str(tmp_path)]) == 2
    assert "scmd apidoc: error:" in capsys.readouterr().err
    assert matlab_cli.main(["quickstart", str(tmp_path / "missing"), "--quiet"]) == 2
    assert "scmd quickstart: error:" in capsys.readouterr().err
    assert matlab_cli.main(["skills", "install", "missing"]) == 2
    assert "scmd skills install: error:" in capsys.readouterr().err


@pytest.mark.parametrize(
    "args",
    [
        ["--help"],
        ["--version"],
        ["apidoc", "--help"],
        ["quickstart", "--help"],
        ["skills", "--help"],
        ["bogus"],
        ["apidoc", "--conf-dir", "missing"],
        ["quickstart", "missing", "--quiet"],
        ["skills", "install", "missing"],
    ],
)
def test_python_dash_m_names_scmd(args, tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "sphinxcontrib.matlab_cli", *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
        env={**os.environ, "PYTHON_COLORS": "0"},
    )
    output = result.stdout + result.stderr
    assert "matlab_cli" not in output
    assert output.startswith(("usage: scmd", "scmd"))


@pytest.mark.parametrize(
    ("argv0", "expected"),
    [
        ("/venv/bin/scmd", "scmd"),
        ("/venv/Scripts/scmd.exe", "scmd"),
        ("/site-packages/sphinxcontrib/matlab_cli.py", "scmd"),
        ("/venv/bin/sphinxcontrib-matlabdomain", "sphinxcontrib-matlabdomain"),
        ("/venv/Scripts/sphinxcontrib-matlabdomain.exe", "sphinxcontrib-matlabdomain"),
    ],
)
def test_program_name(argv0, expected, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [argv0, "apidoc", "--conf-dir", "missing"])
    assert matlab_cli.main() == 2
    assert capsys.readouterr().err.startswith(f"{expected} apidoc: error:")
