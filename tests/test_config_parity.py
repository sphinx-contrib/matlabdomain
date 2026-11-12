"""One ``conf.py``, the same settings and the same errors in ``sphinx-build``
and in ``scmd apidoc`` (G4-T11).

Everything is driven by ``mat_config.CONFIG``: a new config value is covered
without editing the tests. A row for which only one of the two refuses a
wrong value must be listed in ``ONE_SIDED``, so the gap is a decision.
"""

import dataclasses
import io
import os
import sys
from pathlib import Path

import pytest
from sphinx.application import Sphinx
from sphinx.errors import ConfigError, ExtensionError
from sphinx.util.docutils import docutils_namespace

from sphinxcontrib import mat_config
from sphinxcontrib.mat_types import IndexSettings
from sphinxcontrib.matlab_apidoc import _cli as apidoc

HERE = Path(__file__).parent
CONF_FILES = sorted(
    [
        *HERE.glob("roots/*/conf.py"),
        *HERE.parent.glob("docs/conf.py"),
        *HERE.parent.glob("examples/*/docs/conf.py"),
    ]
)


def _id(path):
    return path.parent.relative_to(HERE.parent if "roots" not in path.parts else HERE)


def _start_app(srcdir, tmp_path):
    """Return a Sphinx application (dummy builder) and its warnings text."""
    warning = io.StringIO()
    with docutils_namespace():
        app = Sphinx(
            str(srcdir),
            str(srcdir),
            str(tmp_path / "out"),
            str(tmp_path / "doctrees"),
            "dummy",
            status=None,
            warning=warning,
            freshenv=True,
        )
    return app, warning.getvalue()


@pytest.mark.parametrize("conf_py", CONF_FILES, ids=[str(_id(c)) for c in CONF_FILES])
def test_build_and_command_read_the_same_settings(conf_py, tmp_path):
    """The source settings and every value of the table are the same."""
    srcdir = conf_py.parent
    try:
        app, _ = _start_app(srcdir, tmp_path)
    except ExtensionError as err:  # an extension of docs/ that is not installed
        pytest.skip(f"{srcdir.name}: {err}")
    command = apidoc.read_conf(str(srcdir))
    mat_config.check_sources(command, os.path.abspath(srcdir))

    from_build = IndexSettings.from_config(app.config, app.srcdir)
    from_command = IndexSettings.from_config(command, os.path.abspath(srcdir))
    assert (from_build is None) == (from_command is None)
    if from_build is not None and from_command is not None:
        for field in dataclasses.fields(IndexSettings):
            assert getattr(from_build, field.name) == getattr(
                from_command, field.name
            ), field.name
    for name in mat_config.CONFIG:
        assert getattr(app.config, name) == getattr(command, name), name


# -- the same errors -----------------------------------------------------------

#: row -> wrong values of the right type (an allowed set or a format)
BAD_FORMAT = {
    "matlab_auto_link": ["bogus"],
    "matlab_apidoc_group": ["bogus"],
    "matlab_apidoc_page_size": [0],
    "matlab_apidoc_tocfile": ["a/b"],
    "matlab_version": ["R2999z"],
    "matlab_src_encoding": ["no-such-codec"],
    "matlab_external_names": [["(unclosed"]],
    "matlab_api_check_rules": [{"bogus-rule": "error"}],
}

#: (row, "type" or "format") -> who refuses it: "build" or "command". Both
#: refusing, or both accepting, is not listed. Each tool checks only the
#: values it uses (decided 2026-11-11), so ``scmd apidoc`` can run on a
#: project that is not ready for a build or a check yet. The command reads
#: the rows of ``matlab_src_*``, ``matlab_version`` and ``matlab_apidoc_*``
#: only; the build checks the value of the others (and, for
#: ``matlab_apidoc_*``, only the type, as a warning).
ONE_SIDED = {
    ("matlab_auto_link", "format"): "build",
    ("matlab_external_names", "type"): "build",
    ("matlab_external_names", "format"): "build",
    ("matlab_api_check_rules", "type"): "build",
    ("matlab_api_check_rules", "format"): "build",
    ("matlab_api_check_ignore_patterns", "type"): "build",
    ("matlab_api_check_section_labels", "type"): "build",
    ("matlab_apidoc_output_dir", "type"): "command",
    ("matlab_apidoc_separate", "type"): "command",
    ("matlab_apidoc_maxdepth", "type"): "command",
    ("matlab_apidoc_tocfile", "type"): "command",
    ("matlab_apidoc_tocfile", "format"): "command",
    ("matlab_apidoc_templatedir", "type"): "command",
    ("matlab_apidoc_remove_old", "type"): "command",
    ("matlab_apidoc_group", "type"): "command",
    ("matlab_apidoc_group", "format"): "command",
    ("matlab_apidoc_page_size", "type"): "command",
    ("matlab_apidoc_page_size", "format"): "command",
    ("matlab_apidoc_private", "type"): "command",
}


def wrong_type(default, types):
    """Return a value whose type the row does not allow, or None (any is)."""
    if types == () and default is None:
        return None
    allowed = {types} if isinstance(types, type) else set(types)
    allowed = allowed or {type(default)}
    for candidate in (12345, "text", [1], {"a": 1}, 1.5):
        if type(candidate) not in allowed:
            return candidate
    return None


def cases():
    for name, (default, _, types) in mat_config.CONFIG.items():
        if name in mat_config.REMOVED:
            continue  # both raise one message: test_config.py
        value = wrong_type(default, types)
        if value is not None:
            yield pytest.param(name, "type", value, id=f"{name}-type")
        for value in BAD_FORMAT.get(name, []):
            yield pytest.param(name, "format", value, id=f"{name}-format")


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    """One tiny project; each case rewrites its ``conf.py``."""
    root = tmp_path_factory.mktemp("parity")
    (root / "src").mkdir()
    (root / "src" / "f.m").write_text("function y = f(x)\n% F doc.\ny = x;\nend\n")
    (root / "index.rst").write_text("T\n=\n\n.. mat:autofunction:: f\n")
    return root


def outcomes(project, assignment, tmp_path, capsys):
    """``(build, command)``, each ``None`` (accepts) or the error message."""
    (project / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\n'
        'matlab_src_code_project_root = "src"\n'
        'matlab_apidoc_output_dir = "api"\n'
        f"{assignment}\n"
    )
    try:
        _start_app(project, tmp_path)
        build = None
    except ConfigError as err:
        build = str(err)
    capsys.readouterr()
    status = apidoc.main(["-n", "-q", "-c", str(project)])
    stderr = capsys.readouterr().err.strip()
    prefix = "scmd apidoc: error: "
    command = stderr.removeprefix(prefix) if status == apidoc.USAGE_ERROR else None
    return build, command


def test_one_sided_rows_exist():
    """No stale entry: every listed row is in the table."""
    assert {name for name, _ in ONE_SIDED} <= set(mat_config.CONFIG)
    assert set(BAD_FORMAT) <= set(mat_config.CONFIG)


@pytest.mark.parametrize(("name", "kind", "value"), list(cases()))
def test_build_and_command_refuse_alike(name, kind, value, project, tmp_path, capsys):
    build, command = outcomes(project, f"{name} = {value!r}", tmp_path, capsys)
    expected = ONE_SIDED.get((name, kind))
    if expected == "build":
        assert build is not None
        assert command is None
    elif expected == "command":
        assert command is not None
        assert build is None
    else:
        assert (build is None) == (command is None), (build, command)
        assert build == command  # the same words, naming the same value


# -- the order of the extensions ----------------------------------------------

MATLAB = "sphinxcontrib.matlab"
OTHERS = [
    "myst_parser",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",
]
ORDERS = [
    [MATLAB, *OTHERS],
    [*OTHERS, MATLAB],
]


def _write_extension_project(root, extensions, legacy=None):
    (root / "src").mkdir(exist_ok=True)
    (root / "pysrc").mkdir(exist_ok=True)
    (root / "src" / "f.m").write_text(
        "function y = f(x)\n% F Double x.\ny = 2*x;\nend\n"
    )
    (root / "src" / "C.m").write_text(
        "classdef C\n    % C A class.\n    methods\n"
        "        function r = m(obj, a)\n        % M a method\n        r = a;\n"
        "        end\n    end\nend\n"
    )
    (root / "src" / "notes.md").write_text("# Notes\n\nSome *Markdown*.\n")
    (root / "pysrc" / "t11mod.py").write_text(
        '"""Module."""\n\n\ndef pyfun(a):\n    """Add one.\n\n'
        '    Args:\n        a: first\n    """\n    return a + 1\n'
    )
    (root / "index.rst").write_text(
        "T\n=\n\n.. mat:autofunction:: f\n\n.. mat:autoclass:: C\n   :members:\n\n"
        ".. mat:autosidecar:: notes.md\n\n.. automodule:: t11mod\n   :members:\n"
    )
    conf = (
        "import os, sys\nsys.path.insert(0, os.path.abspath('pysrc'))\n"
        f"extensions = {extensions!r}\n"
        "matlab_src_code_project_root = 'src'\n"
        "matlab_src_sidecar_suffixes = ['.md']\n"
        "intersphinx_mapping = {}\nnitpicky = True\n"
    )
    if legacy is not None:
        conf += f"autodoc_use_legacy_class_based = {legacy}\n"
    (root / "conf.py").write_text(conf)


def _build_html(root, tmp_path):
    sys.modules.pop("t11mod", None)
    saved = list(sys.path)
    warning = io.StringIO()
    try:
        with docutils_namespace():
            app = Sphinx(
                str(root),
                str(root),
                str(tmp_path / "out"),
                str(tmp_path / "doctrees"),
                "html",
                status=None,
                warning=warning,
                freshenv=True,
            )
            app.build()
    finally:
        sys.path[:] = saved
        sys.modules.pop("t11mod", None)
    pages = {
        p.relative_to(tmp_path / "out").as_posix(): p.read_text(
            encoding="utf-8", errors="replace"
        )
        for p in sorted((tmp_path / "out").rglob("*.html"))
        if "_static" not in p.parts
    }
    return pages, warning.getvalue().replace(str(root), "<R>")


def test_extension_order_does_not_change_the_output(tmp_path):
    """sphinxcontrib.matlab first or last: the same pages and warnings."""
    results = []
    for number, order in enumerate(ORDERS):
        root = tmp_path / f"order{number}"
        root.mkdir()
        _write_extension_project(root, order)
        results.append(_build_html(root, root / "_b"))
    (first_pages, first_warnings), (last_pages, last_warnings) = results
    assert first_warnings == last_warnings == ""
    assert first_pages == last_pages
    assert "mat/ref/f.m.html" in first_pages
    assert "pyfun" in first_pages["index.html"]


# -- Python autodoc beside the MATLAB domain -----------------------------------


def test_autodoc_implementations_render_the_same(tmp_path):
    """With ``autodoc_use_legacy_class_based`` True or False the Python object
    and the MATLAB objects render alike, each in its domain, with no warning.
    """
    results = {}
    for legacy in (False, True):
        root = tmp_path / f"legacy{legacy}"
        root.mkdir()
        _write_extension_project(root, [MATLAB, *OTHERS], legacy=legacy)
        results[legacy] = _build_html(root, root / "_b")
    assert results[False][1] == results[True][1] == ""
    assert results[False][0] == results[True][0]
    index = results[False][0]["index.html"]
    assert 'class="py function"' in index
    assert 'class="mat function"' in index
    assert 'class="mat class"' in index
