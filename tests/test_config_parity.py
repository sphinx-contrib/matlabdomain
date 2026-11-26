"""One ``conf.py``, the same settings and the same errors in ``sphinx-build``
and in ``scmd apidoc``.

Everything is driven by ``mat_config.CONFIG``: a new config value is covered
without editing the tests. A row for which only one of the two refuses a
wrong value must be listed in ``ONE_SIDED``, so the gap is a decision.
"""

import dataclasses
import io
import os
import re
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


# -- which run stops for which value -------------------------------------------

#: row -> wrong values of the right type (an allowed set, a range or a format)
BAD_FORMAT = {
    "matlab_src_code_project_root": ["no_such_folder"],
    "matlab_auto_link": ["bogus"],
    "matlab_apidoc_group": ["bogus"],
    "matlab_apidoc_page_size": [0],
    "matlab_apidoc_maxdepth": [0],
    "matlab_apidoc_tocfile": ["a/b"],
    "matlab_version": ["R2999z"],
    "matlab_src_encoding": ["no-such-codec"],
    "matlab_external_names": [["(unclosed"]],
    "matlab_api_check_rules": [{"bogus-rule": "error"}],
    "matlab_api_check_files": [["../x.m"]],
    "matlab_api_check_section_labels": [{"nope": []}],
}

#: the runs: an HTML build, -b matlab-api-check and scmd apidoc
RUNS = ("html", "api", "apidoc")
SOURCES = "html api apidoc"
PAGES = "html api"
#: row -> the runs a bad value stops. Every other run warns once
#: (mat.config), or a build leaves a wrong type to Sphinx's own type
#: warning, and goes on. Every row is listed, so a new value cannot be
#: added without deciding. Each run stops only for the values it uses, so
#: scmd apidoc runs on a project that is not ready for a build or a check
#: yet (decided 2026-11-11), and a build is not stopped by the values of
#: another builder.
STOPS = {
    "matlab_src_code_project_root": SOURCES,
    "matlab_src_include_patterns": SOURCES,
    "matlab_src_exclude_patterns": SOURCES,
    "matlab_src_sidecar_suffixes": SOURCES,
    "matlab_src_encoding": SOURCES,
    "matlab_version": SOURCES,
    "matlab_show_property_default_value": PAGES,
    "matlab_show_property_specs": PAGES,
    "matlab_auto_link": PAGES,
    "matlab_class_signature": PAGES,
    "matlab_add_namespace_names": PAGES,
    "matlab_inherited_members": PAGES,
    "matlab_external_names": PAGES,
    "matlab_stable_urls": "html",
    "matlab_link_shadowed_files_to_chooser_pages": PAGES,
    "matlab_api_check_rules": "api",
    "matlab_api_check_ignore_patterns": "api",
    "matlab_api_check_files": "api",
    "matlab_api_check_files_from": "api",
    "matlab_api_check_ignore_unmatched": "api",
    "matlab_api_check_section_labels": "api",
    "matlab_apidoc_output_dir": "html apidoc",
    "matlab_apidoc_separate": "apidoc",
    "matlab_apidoc_maxdepth": "apidoc",
    "matlab_apidoc_tocfile": "apidoc",
    "matlab_apidoc_templatedir": "apidoc",
    "matlab_apidoc_remove_old": "apidoc",
    "matlab_apidoc_group": "apidoc",
    "matlab_apidoc_page_size": "apidoc",
    "matlab_apidoc_private": "apidoc",
}


def wrong_type(default, types):
    """Return a value whose type the row does not allow."""
    allowed = set(types) or {type(default)}
    return next(
        c for c in (12345, "text", [1], {"a": 1}, 1.5) if type(c) not in allowed
    )


def cases():
    for name, row in mat_config.CONFIG.items():
        if name in mat_config.REMOVED:
            continue  # removed: every run raises one message, test_config.py
        yield pytest.param(name, wrong_type(row.default, row.types), id=f"{name}-type")
        for value in BAD_FORMAT.get(name, []):
            yield pytest.param(name, value, id=f"{name}-format")


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    """One tiny project; each case rewrites its ``conf.py``."""
    root = tmp_path_factory.mktemp("parity")
    (root / "src").mkdir()
    (root / "src" / "f.m").write_text("function y = f(x)\n% F doc.\ny = x;\nend\n")
    (root / "index.rst").write_text("T\n=\n\n.. mat:autofunction:: f\n")
    return root


def _build(project, builder, tmp_path):
    """``("stop", message)``, ``("warn", message)`` for a mat.config
    warning, ``("sphinx", None)`` for Sphinx's type warning, or ``None``.
    """
    warning = io.StringIO()
    try:
        with docutils_namespace():
            Sphinx(
                str(project),
                str(project),
                str(tmp_path / builder),
                str(tmp_path / f"{builder}.doctrees"),
                builder,
                status=None,
                warning=warning,
                freshenv=True,
            )
    except ConfigError as err:
        return "stop", str(err)
    return _warned(warning.getvalue(), "[sphinxcontrib-matlabdomain] ")


def _warned(text, prefix):
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)  # FORCE_COLOR, or an earlier test
    lines = [line for line in text.splitlines() if "WARNING" in line]
    if not lines:
        return None
    assert len(lines) == 1, lines  # one line, never ours and Sphinx's
    if "[mat.config]" in lines[0]:
        message = lines[0].split(prefix, 1)[1].split(" It is used only by ")[0]
        return "warn", message
    assert "The config value `" in lines[0]
    return "sphinx", None


def outcomes(project, assignment, tmp_path, capsys):
    """Run -> its outcome (``_build``) for a ``conf.py`` with ``assignment``."""
    (project / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\n'
        'matlab_src_code_project_root = "src"\n'
        'matlab_apidoc_output_dir = "api"\n'
        f"{assignment}\n"
    )
    result = {
        "html": _build(project, "html", tmp_path),
        "api": _build(project, "matlab-api-check", tmp_path),
    }
    capsys.readouterr()
    status = apidoc.main(["-n", "-q", "-c", str(project)])
    stderr = capsys.readouterr().err
    if status == apidoc.USAGE_ERROR:
        prefix = "scmd apidoc: error: "
        result["apidoc"] = "stop", stderr.strip().removeprefix(prefix)
    else:
        assert status == 0
        result["apidoc"] = _warned(stderr, "[scmd apidoc] ")
    return result


def test_every_row_is_decided():
    """No row without a decision and no stale entry."""
    assert set(STOPS) == set(mat_config.CONFIG) - set(mat_config.REMOVED)
    assert set(BAD_FORMAT) <= set(STOPS)


@pytest.mark.parametrize(("name", "value"), list(cases()))
def test_each_run_stops_for_its_values_and_warns_for_the_others(
    name, value, project, tmp_path, capsys
):
    result = outcomes(project, f"{name} = {value!r}", tmp_path, capsys)
    # Every run reports a bad value: it stops or warns.
    got = {run: outcome for run, outcome in result.items() if outcome is not None}
    assert len(got) == len(RUNS), result
    stops = STOPS[name].split()
    assert [run for run in RUNS if got[run][0] == "stop"] == stops
    for run in set(RUNS) - set(stops):
        # apidoc runs no type check of Sphinx's
        allowed = ("warn",) if run == "apidoc" else ("warn", "sphinx")
        assert got[run][0] in allowed, (run, got)
    # The same words, naming the same value, wherever it is reported.
    messages = {got[run][1] for run in RUNS if got[run][1] is not None}
    assert len(messages) == 1, messages
    assert name in messages.pop()


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
