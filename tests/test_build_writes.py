"""A build writes only to its output and doctree folders (G4-T6).

Where the project root is and where a tool writes is the user's choice, and a
build writes where the user pointed it: its output folder and its doctree
folder, wherever they are. These tests copy a project, hash every file
outside those two folders, build, and compare.
"""

import hashlib
import json
import os
import shutil
import stat
import sys
from pathlib import Path

import pytest

from sphinxcontrib.mat_simulink import _linker

REPO = Path(__file__).parent.parent
BUILDERS = ("html", "dirhtml", "matlab-api-check")

# chmod does not stop root, and Windows has no such permission.
CAN_MAKE_READ_ONLY = sys.platform != "win32" and os.geteuid() != 0

FUNCTION = "function f\n% F does nothing.\nend\n"
CONF = (
    'extensions = ["sphinxcontrib.matlab"]\n'
    'matlab_src_code_project_root = ".."\n'
    'matlab_src_include_patterns = ["src/**"]\n'
    'html_baseurl = "https://example.org/docs"\n'
)
# the committed settings of a project whose output folder is not this one
SETTINGS = '{"mode": "local", "local": "elsewhere/", "published": ""}\n'


def synthetic_project(tmp_path):
    root = tmp_path / "proj"
    (root / "src").mkdir(parents=True)
    (root / "src" / "f.m").write_text(FUNCTION)
    docs = root / "docs"
    docs.mkdir()
    (docs / "conf.py").write_text(CONF)
    (docs / "index.rst").write_text("Index\n=====\n\n.. mat:autofunction:: src/f.m\n")
    folder = root / "+sphinxcontrib" / "+matlabdomain"
    folder.mkdir(parents=True)
    (folder / _linker.NAME).write_text(SETTINGS)
    return root, docs


def copied_project(tmp_path, name):
    """Copy ``docs/`` and ``examples/apidoc``, which include each other,
    without build output and bytecode caches (a cache that is already there
    would hide that a build writes one).
    """
    for folder in ("docs", "examples/apidoc"):
        shutil.copytree(
            REPO / folder,
            tmp_path / folder,
            ignore=shutil.ignore_patterns("_build", "__pycache__"),
        )
    return tmp_path, tmp_path / name


def snapshot(top, skip):
    """``{path: hash}`` of every file and folder below ``top`` except below
    the ``skip`` folders.
    """
    out = {}
    for folder, dirs, files in os.walk(top):
        folder = Path(folder)
        dirs[:] = [d for d in dirs if (folder / d) not in skip]
        for name in dirs:
            out[(folder / name).relative_to(top).as_posix() + "/"] = ""
        for name in files:
            path = folder / name
            out[path.relative_to(top).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return out


def changed(before, after):
    return sorted(
        path
        for path in before.keys() | after.keys()
        if before.get(path) != after.get(path)
    )


def build_all(make_app, top, srcdir):
    """Build every builder; the paths below ``top`` outside the output and
    doctree folders that changed.
    """
    build = srcdir / "_build"  # the default output and doctree folders
    before = snapshot(top, {build})
    for name in BUILDERS:
        app = make_app(buildername=name, srcdir=srcdir)
        assert Path(app.outdir).parent == build
        assert Path(app.doctreedir).parent == build
        app.build()
        app.cleanup()
    return changed(before, snapshot(top, {build}))


def test_synthetic_project_writes_nothing_outside(make_app, tmp_path):
    root, docs = synthetic_project(tmp_path)
    assert build_all(make_app, root, docs) == []


# The builds of docs/ and examples/apidoc take about a minute together.
@pytest.mark.parametrize("name", ["docs", "examples/apidoc/docs"])
def test_repository_projects_write_nothing_outside(make_app, tmp_path, name):
    top, srcdir = copied_project(tmp_path, name)
    assert build_all(make_app, top, srcdir) == []


@pytest.mark.skipif(not CAN_MAKE_READ_ONLY, reason="needs POSIX permissions")
def test_read_only_project_root_builds(make_app, tmp_path):
    root, docs = synthetic_project(tmp_path)
    (docs / "_build").mkdir()
    folders = [p for p in root.rglob("*") if p.is_dir() and "_build" not in p.parts]
    paths = [p for p in root.rglob("*") if "_build" not in p.parts]
    for path in [root, *paths]:
        path.chmod(path.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    try:
        app = make_app(srcdir=docs, freshenv=True)
        app.build(force_all=True)
        assert app.statuscode == 0
        assert app.warning.getvalue() == ""
    finally:
        for folder in [root, *folders]:
            folder.chmod(0o755)
        for path in paths:
            if path not in folders:
                path.chmod(0o644)
    assert json.loads(
        (root / "+sphinxcontrib" / "+matlabdomain" / _linker.NAME).read_text()
    ) == json.loads(SETTINGS)
