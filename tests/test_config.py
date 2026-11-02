"""Project root, source patterns and removed options."""

import importlib.metadata

import pytest
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
