"""The documentation in ``docs/`` (plan.md Phase 10): it builds without
warnings, and its reference pages list every configuration value, directive,
directive option, role, warning and command-line option, and nothing else.
"""

import re
import shutil
import tomllib
from pathlib import Path

import pytest

from sphinxcontrib.matlab import MATLABDomain
from sphinxcontrib.matlab_apidoc._cli import get_parser
from sphinxcontrib.matlab_quickstart._cli import get_parser as get_quickstart_parser
from sphinxcontrib.matlab_skills._cli import get_parser as get_skills_parser

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
            assert options is not None
            options.add(m[2])
            column = len(m[1])
        elif column and re.fullmatch(rf" {{{column}}}\S+", line):
            # another option name of the same entry
            assert options is not None
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
        # mat:autosidecar renders a sidecar doc, not an object.
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


def program_options(program):
    """Return the ``.. option::`` names after ``.. program:: <program>``."""
    text = (REFERENCE / "cli.rst").read_text(encoding="utf-8")
    parts = re.split(r"^\.\. program:: (.+)$", text, flags=re.MULTILINE)
    body = dict(zip(parts[1::2], parts[2::2], strict=True))[program]
    options = set()
    for line in re.findall(r"^\.\. option:: (.+)$", body, re.MULTILINE):
        options.update(part.split()[0] for part in line.split(", "))
    return options


def skills_subparser(name):
    def parser():
        action = get_skills_parser()._subparsers._group_actions[0]  # type: ignore[union-attr]
        return action.choices[name]  # type: ignore[index]

    return parser


@pytest.mark.parametrize(
    ("program", "parser"),
    [
        ("scmd apidoc", get_parser),
        ("scmd quickstart", get_quickstart_parser),
        ("scmd skills", get_skills_parser),
        ("scmd skills list", skills_subparser("list")),
        ("scmd skills install", skills_subparser("install")),
    ],
)
def test_command_line_options(program, parser):
    cli = set()
    for action in parser()._actions:
        cli.update(action.option_strings or [action.metavar or action.dest.upper()])
    assert program_options(program) == cli


def repository_configuration(root):
    suffixes = {".toml", ".ini", ".cfg", ".yaml", ".yml", ".json"}
    names = {
        "uv.lock",
        ".python-version",
        ".gitignore",
        ".gitattributes",
        ".editorconfig",
        "MANIFEST.in",
        "Makefile",
        "make.bat",
        "conf.py",
        "CONTRIBUTING.rst",
        "codespell_ignore_words.txt",
        "CODEOWNERS",
    }
    paths = list(root.iterdir())
    for folder in (".github", ".vscode"):
        paths.extend((root / folder).rglob("*"))
    for folder in ("docs", "test_slow/gauntlet"):
        if (root / folder).is_dir():
            paths.extend((root / folder).iterdir())
    paths.extend((root / "examples").rglob("conf.py"))
    return {
        path.relative_to(root).as_posix()
        for path in paths
        if path.is_file()
        and "_build" not in path.relative_to(root).parts
        and (path.suffix in suffixes or path.name in names)
    }


def test_repository_configuration():
    page = REPO / "docs/developer-guide/contributing.rst"
    section = page.read_text(encoding="utf-8").split(
        ".. _repository-configuration:", 1
    )[1]
    documented = re.findall(r"^``([^`]+)``$", section, re.MULTILINE)
    assert len(documented) == len(set(documented)), "duplicate config entries"
    assert set(documented) == repository_configuration(REPO)


def test_ruff_hook_matches_dev_pin():
    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    pins = [
        d.removeprefix("ruff==")
        for d in project["dependency-groups"]["dev"]
        if isinstance(d, str) and d.startswith("ruff==")
    ]
    hooks = (REPO / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    hook = re.search(r"ruff-pre-commit\s+rev: v(\S+)", hooks)
    assert hook is not None
    assert pins == [hook[1]]


@pytest.mark.parametrize(
    ("name", "included"),
    [
        ("new-tool.toml", True),
        (".github/workflows/new.yml", True),
        (".github/CODEOWNERS", True),
        (".vscode/new.json", True),
        ("test_slow/gauntlet/new.toml", True),
        ("examples/apidoc/docs/conf.py", True),
        ("tests/roots/new/conf.py", False),
        ("test_slow/gauntlet/runs/new/config.json", False),
        ("examples/apidoc/docs/_build/conf.py", False),
    ],
)
def test_repository_configuration_scope(tmp_path, name, included):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    assert (name in repository_configuration(tmp_path)) == included
