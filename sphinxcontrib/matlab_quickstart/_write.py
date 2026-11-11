"""sphinxcontrib.matlab_quickstart._write.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

What ``scmd quickstart`` writes (plan.md Section 2.13): the
files of the Sphinx source folder from the templates, and the edits
outside it: the docs dependency group through ``uv add --frozen``, lines in
``.gitignore`` and ``.gitattributes``, and, for a project with Simulink
files, the MATLAB function behind their Help links (``linker_files``). It
never touches ``uv.lock``, the project's MATLAB code or CI, and never
commits.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from sphinx.util.template import ReSTRenderer

from ..mat_api_check import RULES
from ..mat_simulink import MATLAB_TOOLS
from ..mat_types import DEFAULT_EXCLUSION_PATTERNS
from ._detect import SECTION_FILES

TEMPLATE_DIR = Path(__file__).parent / "templates"
MATLABDOMAIN_URL = "https://github.com/sphinx-contrib/matlabdomain"
#: the files of the Sphinx source folder, in the order they are written
DOCS_FILES = (
    "conf.py",
    "index.rst",
    "_static/.gitkeep",
    "Makefile",
    "make.bat",
    "BUILDING_DOCS.md",
)
#: themes that come with Sphinx (no package to install)
BUILTIN_THEMES = frozenset(
    {
        "alabaster", "agogo", "basic", "bizstyle", "classic", "default",
        "epub", "haiku", "nature", "nonav", "pyramid", "scrolls",
        "sphinxdoc", "traditional",
    }
)  # fmt: skip
GITATTRIBUTES_LINE = "*.bat text eol=crlf"
#: the files edited outside the Sphinx source folder
OUTSIDE_FILES = ("pyproject.toml", ".gitignore", ".gitattributes")


def py(value):
    """Return a Python literal for ``conf.py``, strings in double quotes."""
    if isinstance(value, (tuple, list)):
        return f"({', '.join(map(py, value))})"
    return json.dumps(value, ensure_ascii=False)


def _renderer():
    renderer = ReSTRenderer([TEMPLATE_DIR])
    renderer.env.trim_blocks = True
    renderer.env.lstrip_blocks = True
    renderer.env.filters["py"] = py
    return renderer


def requirements(answers, install):
    """Return the docs dependencies (PEP 508), without an editable install."""
    out = ["sphinx>=8.0"]
    if install.kind != "editable":
        out.append(install.requirement)
    if answers["markdown"]:
        out.append("myst-parser>=4,<6")
    theme = answers["theme"]
    if theme not in BUILTIN_THEMES:
        out.append(theme.replace("_", "-"))
    out.append("sphinx-autobuild")
    return out


def _quote(requirement):
    return f'"{requirement}"' if any(c in requirement for c in " <>;@") else requirement


def shell(command):
    """Return a command as a line to type."""
    return " ".join(map(_quote, command))


def pip_lines(answers, install):
    """Return the ``pip install`` lines of the docs dependencies."""
    lines = [shell(["pip", "install", *requirements(answers, install)])]
    if install.kind == "editable":
        lines.append(shell(["pip", "install", "-e", install.requirement]))
    return lines


def install_lines(answers, install, pyproject):
    """Return how to install the docs dependencies without uv: ``pip install``,
    after a ``[dependency-groups]`` table for an existing ``pyproject.toml``.
    """
    lines = pip_lines(answers, install)
    if not pyproject:
        return lines
    return [
        "Add to pyproject.toml (pip install --group docs needs pip 25.1 or later):",
        "  [dependency-groups]",
        "  docs = [",
        *(f"      {json.dumps(r)}," for r in requirements(answers, install)),
        "  ]",
        "or install them directly:",
        *(f"  {line}" for line in lines),
    ]


def uv_commands(answers, install):
    """Return the ``uv add`` commands of a uv project."""
    base = ["uv", "add", "--frozen", "--group", "docs"]
    out = [[*base, *requirements(answers, install)]]
    if install.kind == "editable":
        out.append([*base, "--editable", install.requirement])
    return out


def headings_text(entries):
    """Return the headings for the build guide (`Inputs:`, ...)."""
    names = [entry if isinstance(entry, str) else entry[0] for entry in entries]
    return ", ".join(f"`{name}:`" for name in names)


def render(answers, context):
    """Return ``{name: bytes}`` of the files in the Sphinx source folder."""
    context = {
        **answers,
        **context,
        "uv": answers["make"] == "uv",
        "generate": answers["api_pages"] == "generate",
        "napoleon": answers["napoleon_custom_sections"],
        "headings": headings_text(answers["napoleon_custom_sections"]),
        "default_exclude": DEFAULT_EXCLUSION_PATTERNS,
        "api_check_rules": list(RULES),
        "section_files": SECTION_FILES,
        "matlabdomain_url": MATLABDOMAIN_URL,
    }
    renderer = _renderer()
    out = {}
    for name in DOCS_FILES:
        if name == "BUILDING_DOCS.md" and not answers["guide"]:
            continue
        if name == "_static/.gitkeep":
            out[name] = b""
            continue
        text = renderer.render(f"{name}.jinja", context).rstrip("\n") + "\n"
        if name == "make.bat":
            # cmd.exe misreads labels in LF-only files
            text = text.replace("\n", "\r\n")
        out[name] = text.encode("utf-8")
    return out


@dataclass
class Written:
    """What ``write_files`` wrote (or would write), as paths below the
    Sphinx source folder.
    """

    created: list = field(default_factory=list)
    updated: list = field(default_factory=list)
    unchanged: list = field(default_factory=list)


def write_files(docs, files, dry_run):
    """Write ``files`` (``{name: bytes}``) below ``docs``."""
    out = Written()
    for name, data in files.items():
        path = os.path.join(docs, *name.split("/"))
        try:
            with open(path, "rb") as f:
                old = f.read()
        except FileNotFoundError:
            status = out.created
        else:
            status = out.unchanged if old == data else out.updated
        status.append(name)
        if status is not out.unchanged and not dry_run:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)
    return out


LINKER_FOLDER = "+sphinxcontrib/+matlabdomain"
LINKER = "simulinkDocumentationLinker"
#: the exclusion pattern of the linker's folder
LINKER_EXCLUDE = "+sphinxcontrib/"
#: the address of ``make livehtml`` (sphinx-autobuild's default)
LIVE_SERVER = "http://127.0.0.1:8000/"


def linker_files(root, docs_rel, published=""):
    """Return ``{name: bytes}`` below ``root``: the function behind the Help
    links of Simulink files, and its settings unless they exist (the user
    may have set the published site; builds never change them).
    """
    source = MATLAB_TOOLS / "+sphinxcontrib" / "+matlabdomain" / f"{LINKER}.m"
    files = {f"{LINKER_FOLDER}/{LINKER}.m": source.read_bytes()}
    settings = f"{LINKER_FOLDER}/{LINKER}.json"
    if not os.path.isfile(os.path.join(root, *settings.split("/"))):
        text = json.dumps(
            {
                "mode": "local",
                "local": f"{docs_rel}/_build/html/",
                "server": LIVE_SERVER,
                "published": published,
            },
            indent=1,
        )
        files[settings] = (text + "\n").encode("utf-8")
    return files


def missing_lines(path, lines):
    """Return the ``lines`` that ``path`` does not have yet."""
    try:
        with open(path, encoding="utf-8", errors="surrogateescape") as f:
            have = {line.strip() for line in f}
    except FileNotFoundError:
        have = set()
    return [line for line in lines if line not in have]


def append_lines(path, lines):
    """Append ``lines`` to ``path``, in its line-ending style."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except FileNotFoundError:
        data = b""
    newline = b"\r\n" if b"\r\n" in data else b"\n"
    if data and not data.endswith(b"\n"):
        data += newline
    data += b"".join(line.encode("utf-8") + newline for line in lines)
    with open(path, "wb") as f:
        f.write(data)


def run(command, cwd):
    """Run ``command`` in ``cwd``: ``(exit status, output)``."""
    proc = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def git_dirty(root):
    """Return the files of ``OUTSIDE_FILES`` with uncommitted changes in
    ``root``, or None when ``root`` is not in a git work tree.
    """
    if shutil.which("git") is None:
        return None
    status, _ = run(["git", "rev-parse", "--is-inside-work-tree"], root)
    if status:
        return None
    status, output = run(["git", "status", "--porcelain", "--", *OUTSIDE_FILES], root)
    if status:  # pragma: no cover - defensive: rev-parse just succeeded
        return None
    return sorted({line[3:].strip('"') for line in output.splitlines()})
