"""The documentation in ``docs/`` (plan.md Phase 10): it builds without
warnings, and its reference pages list every configuration value, directive,
directive option, role, warning and command-line option, and nothing else.
"""

import re
import shutil
from pathlib import Path

import pytest

from sphinxcontrib.matlab import MATLABDomain
from sphinxcontrib.matlab_apidoc._cli import get_parser

REPO = Path(__file__).parents[1]
REFERENCE = REPO / "docs" / "reference"
SOURCE = REPO / "sphinxcontrib"

# How the code emits warning subtypes: a logger keyword, mat_types._warn, and
# (subtype, message, row) tuples collected for later.
WARNING_RE = re.compile(
    r'subtype="(\w+)"|_warn\(\s*"(\w+)"'
    r'|(?:append\(|\[)\s*\(\s*"([a-z]+(?:_[a-z]+)*)",'
)


def entries(pattern, page):
    """Return the first group of ``pattern`` on each matching line of ``page``."""
    text = (REFERENCE / page).read_text(encoding="utf-8")
    return set(re.findall(pattern, text, re.MULTILINE))


def documented_directives():
    """``{directive: {option, ...}}`` from the ``rst:directive`` entries."""
    directives = {}
    options = column = None
    text = (REFERENCE / "directives.rst").read_text(encoding="utf-8")
    for line in text.splitlines():
        if m := re.match(r"\.\. rst:directive:: \.\. mat:(\w+)::", line):
            options = directives.setdefault(m[1], set())
            column = None
        elif m := re.match(r"(\s+\.\. rst:directive:option:: )(\S+)$", line):
            options.add(m[2])
            column = len(m[1])
        elif column and re.fullmatch(rf" {{{column}}}\S+", line):
            # another option name of the same entry
            options.add(line.strip())
        else:
            column = None
    return directives


@pytest.fixture
def bare_app(make_app, tmp_path):
    (tmp_path / "conf.py").write_text('extensions = ["sphinxcontrib.matlab"]\n')
    (tmp_path / "index.rst").write_text("Index\n=====\n")
    return make_app(srcdir=tmp_path)


def test_docs_build_without_warnings(make_app, tmp_path):
    # The docs include files from examples/apidoc.
    for folder in ("docs", "examples/apidoc"):
        shutil.copytree(
            REPO / folder, tmp_path / folder, ignore=shutil.ignore_patterns("_build")
        )
    app = make_app(srcdir=tmp_path / "docs", freshenv=True)
    app.build(force_all=True)
    assert app.config.nitpicky
    assert app.warning.getvalue() == ""


def test_configuration_values(bare_app):
    config = {opt.name for opt in bare_app.config if opt.name.startswith("matlab_")}
    assert entries(r"^\.\. confval:: (\w+)$", "configuration.rst") == config


def test_directives_and_options(bare_app):
    directives = {
        name: set(cls.option_spec or {})
        for name, cls in MATLABDomain.directives.items()
    }
    registry = bare_app.registry
    for name, cls in registry.domain_directives["mat"].items():
        documenter = registry.documenters.get(f"mat:{name.removeprefix('auto')}")
        # mat:autopage renders a page, not an object.
        options = cls.option_spec if documenter is None else documenter.option_spec
        directives[name] = set(options)
    assert documented_directives() == directives


def test_roles(bare_app):
    roles = set(MATLABDomain.roles) | set(bare_app.registry.domain_roles.get("mat", {}))
    assert entries(r"^\.\. rst:role:: mat:(\w+)$", "directives.rst") == roles


def test_warnings():
    subtypes = {
        next(filter(None, m.groups()))
        for path in SOURCE.rglob("*.py")
        for m in WARNING_RE.finditer(path.read_text(encoding="utf-8"))
    }
    assert len(subtypes) > 5
    assert entries(r"^\s+\* - ``mat\.(\w+)``$", "warnings.rst") == subtypes


def test_command_line_options():
    cli = set()
    for action in get_parser()._actions:
        cli.update(action.option_strings or [action.metavar or action.dest.upper()])
    options = set()
    for line in entries(r"^\.\. option:: (.+)$", "cli.rst"):
        options.update(part.split()[0] for part in line.split(", "))
    assert options == cli
