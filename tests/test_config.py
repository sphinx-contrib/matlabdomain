"""Project root, source patterns and removed options."""

import importlib.metadata
import logging
import re

import pytest
import sphinx
from sphinx.cmd.build import build_main
from sphinx.errors import ConfigError


@pytest.fixture
def project(tmp_path):
    src = tmp_path / "docs"
    (src / "code" / "+pkg").mkdir(parents=True)
    (src / "code" / "+pkg" / "f.m").write_text("function f\n% F doc\nend\n")
    (src / "conf.py").write_text(
        'extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]\n'
    )
    (src / "index.rst").write_text("Index\n=====\n\n.. mat:autofunction:: pkg.f\n")
    return src


def test_project_root_is_relative_to_srcdir(make_app, project, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # not the source or config directory
    app = make_app(
        srcdir=project, confoverrides={"matlab_src_code_project_root": "code"}
    )
    app.build()
    assert "F doc" in (app.outdir / "index.html").read_text()
    assert "WARNING" not in app.warning.getvalue()


def test_extension_version_without_package_metadata(make_app, project, monkeypatch):
    def missing(name):
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", missing)
    app = make_app(srcdir=project)
    assert app.extensions["sphinxcontrib.matlab"].version == "0.0.0"


@pytest.mark.parametrize(
    "overrides",
    [
        {"matlab_src_dir": "code"},
        {"matlab_src_dir": "code", "matlab_src_code_project_root": "code"},
    ],
)
def test_matlab_src_dir_raises(make_app, project, overrides):
    with pytest.raises(ConfigError, match="matlab_src_dir was removed: use "):
        make_app(srcdir=project, confoverrides=overrides)


@pytest.mark.parametrize(
    "name",
    [
        "matlab_keep_package_prefix",
        "matlab_short_links",
    ],
)
@pytest.mark.parametrize("value", [True, False])
def test_removed_options_raise(make_app, project, name, value):
    with pytest.raises(ConfigError, match=f"{name} was removed"):
        make_app(srcdir=project, confoverrides={name: value})


def test_removed_options_are_reported_together(make_app, project):
    overrides = {"matlab_src_dir": "code", "matlab_keep_package_prefix": True}
    with pytest.raises(ConfigError) as error:
        make_app(srcdir=project, confoverrides=overrides)
    message = str(error.value)
    assert "matlab_src_dir was removed" in message
    assert "matlab_keep_package_prefix was removed" in message
    assert message.endswith("Remove them from conf.py.")


@pytest.mark.parametrize(
    ("line", "message"),
    [
        (
            'matlab_src_code_project_rot = "code"',
            r"matlab_src_code_project_rot is not a configuration value \(did you "
            r"mean matlab_src_code_project_root\?\)\. Correct or delete",
        ),
        ("matlab_zzz = 1", r"matlab_zzz is not a configuration value\. Correct"),
    ],
)
def test_unknown_matlab_names_raise(make_app, project, line, message):
    with open(project / "conf.py", "a", encoding="utf-8") as conf:
        conf.write(f"{line}\n")
    with pytest.raises(ConfigError, match=message):
        make_app(srcdir=project)


def test_other_names_in_conf_py_are_ignored(make_app, project):
    with open(project / "conf.py", "a", encoding="utf-8") as conf:
        conf.write(
            '_matlab_helper = "code"\nmatlab_src_code_project_root = _matlab_helper\n'
        )
    make_app(srcdir=project)


def test_unknown_matlab_names_set_by_another_extension_raise(make_app, project):
    # Like sphinx-multiproject, which sets a project's values on config-inited.
    with open(project / "conf.py", "a", encoding="utf-8") as conf:
        conf.write(
            "def setup(app):\n"
            "    def inject(app, config):\n"
            '        config["matlab_src_code_projct_root"] = "code"\n'
            '        config["matlab_src_code_project_root"] = "code"\n'
            '    app.connect("config-inited", inject, priority=-999)\n'
        )
    with pytest.raises(
        ConfigError,
        match=r"^matlab_src_code_projct_root is not a configuration value \(did "
        r"you mean matlab_src_code_project_root\?\)\. Correct",
    ):
        make_app(srcdir=project)


def sphinx_build(args):
    """Run ``sphinx-build args`` in this process; return its exit status."""
    try:
        return build_main(args)
    finally:
        # Sphinx 8.0 raises on a warning as long as the -W handlers of this
        # build are on its logger, and a later test may log without an app.
        sphinx_logger = logging.getLogger("sphinx")
        for handler in sphinx_logger.handlers[:]:
            sphinx_logger.removeHandler(handler)


def test_project_root_is_relative_to_srcdir_not_confdir(project, tmp_path):
    # sphinx-multiversion and sphinx-multiproject keep conf.py elsewhere.
    confdir = tmp_path / "conf"
    confdir.mkdir()
    (project / "conf.py").rename(confdir / "conf.py")
    with open(confdir / "conf.py", "a", encoding="utf-8") as conf:
        conf.write('matlab_src_code_project_root = "code"\n')
    out = tmp_path / "out"
    assert sphinx_build(["-q", "-W", "-c", str(confdir), str(project), str(out)]) == 0
    assert "F doc" in (out / "index.html").read_text(encoding="utf-8")


def assert_configuration_error(stderr, message):
    """``stderr`` of sphinx-build shows the ``ConfigError`` ``message`` the
    way the Sphinx under test prints one (reference/configuration.rst).
    """
    # With FORCE_COLOR (CI) Sphinx colours the first line.
    stderr = re.sub(r"\x1b\[[0-9;]*m", "", stderr)
    if tuple(map(int, sphinx.__version__.split(".")[:2])) >= (8, 2):
        # The report Sphinx prints for every error, ending in the exception.
        assert "Configuration error!" in stderr
        assert f"\n    sphinx.errors.ConfigError: {message}\n" in stderr
    else:
        assert f"Configuration error:\n{message}\n" in stderr


def test_a_bad_value_stops_sphinx_build_naming_it(project, tmp_path, capsys):
    with open(project / "conf.py", "a", encoding="utf-8") as conf:
        conf.write('matlab_auto_link = "some"\n')
    out = tmp_path / "out"
    assert sphinx_build(["-q", str(project), str(out)]) == 2
    assert_configuration_error(
        capsys.readouterr().err,
        "matlab_auto_link must be None, 'basic' or 'all', not 'some'.",
    )
    assert not (out / "index.html").exists()


def test_a_missing_project_root_stops_sphinx_build(project, tmp_path, capsys):
    with open(project / "conf.py", "a", encoding="utf-8") as conf:
        conf.write('matlab_src_code_project_root = "../no_such_folder"\n')
    out = tmp_path / "out"
    assert sphinx_build(["-q", str(project), str(out)]) == 2
    err = capsys.readouterr().err
    # The folder as resolved: next to the source folder, not below it.
    message = re.search(r"matlab_src_code_project_root '(.*)' is not a folder\.", err)
    assert message is not None
    resolved = message[1].replace("\\\\", "/")
    assert resolved.endswith("/no_such_folder")
    assert "/docs/" not in resolved
    assert_configuration_error(
        err,
        f"{message[0]} Set it to the folder of the MATLAB code; a relative path "
        "is relative to the Sphinx source folder.",
    )
    assert not (out / "index.html").exists()
