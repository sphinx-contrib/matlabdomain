"""Project root, source patterns and removed options."""

import importlib.metadata
import logging
import re

import pytest
import sphinx
from sphinx.cmd.build import build_main
from sphinx.errors import ConfigError

from sphinxcontrib import mat_api_check


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


# -- which run checks which value ----------------------------------------------


def _with_root(project, *lines):
    """Add the project root and ``lines`` to ``conf.py``."""
    with open(project / "conf.py", "a", encoding="utf-8") as conf:
        conf.write('matlab_src_code_project_root = "code"\n')
        conf.write("".join(f"{line}\n" for line in lines))


def _plain(text):
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def config_warnings(text):
    """Return the ``mat.config`` lines of a warning stream."""
    return [line for line in _plain(text).splitlines() if "[mat.config]" in line]


def config_warning(message, users, this="this build"):
    return (
        f"WARNING: [sphinxcontrib-matlabdomain] {message} It is used only by "
        f"{users}; {this} ignores it. [mat.config]"
    )


API = "the matlab-api-check builder"
RULES = "matlab_api_check_rules: unknown rule 'bogus'; the rules are " + ", ".join(
    mat_api_check.RULES
)


OUTSIDE = "matlab_api_check_files: '../x.m' leaves matlab_src_code_project_root."


def _status_with_W():
    """sphinx-build -W fails at the end (1) from Sphinx 8.1, at once (2) before."""
    return 1 if tuple(map(int, sphinx.__version__.split(".")[:2])) >= (8, 1) else 2


def test_a_value_of_another_builder_warns_once(project, tmp_path, capsys):
    """The api-check values stop only -b matlab-api-check; an HTML build
    warns once (mat.config) and goes on; -W makes that a failure.
    """
    _with_root(project, 'matlab_api_check_rules = {"bogus": "error"}')
    out = tmp_path / "out"
    assert sphinx_build(["-q", "-E", str(project), str(out)]) == 0
    assert config_warnings(capsys.readouterr().err) == [
        config_warning(f"{RULES}.", API)
    ]
    assert "F doc" in (out / "index.html").read_text(encoding="utf-8")

    args = ["-q", "-E", "-b", "matlab-api-check", str(project), str(tmp_path / "api")]
    assert sphinx_build(args) == 2
    assert_configuration_error(capsys.readouterr().err, f"{RULES}.")

    assert sphinx_build(["-q", "-E", "-W", str(project), str(tmp_path / "w")]) == (
        _status_with_W()
    )
    assert len(config_warnings(capsys.readouterr().err)) == 1


def test_suppress_warnings_silences_mat_config(make_app, project):
    _with_root(
        project, 'matlab_apidoc_group = "x"', 'suppress_warnings = ["mat.config"]'
    )
    app = make_app(srcdir=project)
    assert app.warning.getvalue() == ""


def test_an_apidoc_value_in_a_build_warns_once_naming_apidoc(project, tmp_path, capsys):
    _with_root(project, 'matlab_apidoc_group = "x"')
    assert sphinx_build(["-q", "-E", "-b", "text", str(project), str(tmp_path)]) == 0
    assert config_warnings(capsys.readouterr().err) == [
        config_warning(
            "matlab_apidoc_group must be 'namespace' or 'folder', not 'x'.",
            "scmd apidoc",
        )
    ]


@pytest.mark.parametrize(
    ("line", "builder", "outcome", "message"),
    [
        # matlab-api-check values
        ('matlab_api_check_files = ["../x.m"]', "matlab-api-check", "stop", OUTSIDE),
        ('matlab_api_check_files = ["../x.m"]', "text", "warn", (OUTSIDE, API)),
        (
            'matlab_api_check_ignore_unmatched = "no"',
            "matlab-api-check",
            "stop",
            "matlab_api_check_ignore_unmatched must be bool, not 'no'.",
        ),
        ('matlab_api_check_ignore_unmatched = "no"', "html", "sphinx", None),
        (
            "matlab_api_check_ignore_unmatched = 0",
            "html",
            "warn",
            ("matlab_api_check_ignore_unmatched must be bool, not 0.", API),
        ),
        ('matlab_api_check_files_from = "missing.txt"', "html", "ok", None),
        (
            'matlab_api_check_files_from = "missing.txt"',
            "matlab-api-check",
            "stop",
            "matlab_api_check_files_from: cannot read 'missing.txt': ",
        ),
        # values of HTML builds
        (
            "matlab_stable_urls = 0",
            "dirhtml",
            "stop",
            "matlab_stable_urls must be bool, not 0.",
        ),
        (
            "matlab_stable_urls = 0",
            "json",
            "warn",
            ("matlab_stable_urls must be bool, not 0.", "HTML builds"),
        ),
        ('matlab_stable_urls = "no"', "text", "sphinx", None),
        (
            "matlab_apidoc_output_dir = 5",
            "html",
            "stop",
            "matlab_apidoc_output_dir must be str or None, not 5.",
        ),
        ("matlab_apidoc_output_dir = 5", "text", "sphinx", None),
        # values of scmd apidoc
        (
            "matlab_apidoc_maxdepth = 0",
            "html",
            "warn",
            (
                "matlab_apidoc_maxdepth must be 1 or more, or -1 for no limit, not 0.",
                "scmd apidoc",
            ),
        ),
        ("matlab_apidoc_maxdepth = -1", "html", "ok", None),
        ('matlab_apidoc_maxdepth = "x"', "html", "sphinx", None),
        (
            'matlab_apidoc_tocfile = "a/b"',
            "html",
            "warn",
            ("matlab_apidoc_tocfile 'a/b' must be a file name.", "scmd apidoc"),
        ),
        # values of every builder: booleans are True or False
        (
            'matlab_show_property_specs = "no"',
            "html",
            "stop",
            "matlab_show_property_specs must be bool, not 'no'.",
        ),
        (
            "matlab_class_signature = 0",
            "text",
            "stop",
            "matlab_class_signature must be bool, not 0.",
        ),
        (
            'matlab_link_shadowed_files_to_chooser_pages = "no"',
            "matlab-api-check",
            "stop",
            "matlab_link_shadowed_files_to_chooser_pages must be bool, not 'no'.",
        ),
    ],
)
def test_which_run_checks_which_value(
    make_app, project, monkeypatch, line, builder, outcome, message
):
    """A run stops for a bad value it uses, warns once (mat.config) for one
    only another run uses, and leaves a wrong type of that one to Sphinx's
    own warning.
    """
    monkeypatch.chdir(project)
    _with_root(project, line)
    name = line.split()[0]
    if outcome == "stop":
        with pytest.raises(ConfigError) as error:
            make_app(builder, srcdir=project)
        assert str(error.value).startswith(message)
        return
    app = make_app(builder, srcdir=project)
    warnings = app.warning.getvalue()
    if outcome == "warn":
        assert config_warnings(warnings) == [config_warning(*message)]
    elif outcome == "sphinx":
        assert config_warnings(warnings) == []
        assert warnings.count(f"The config value `{name}' has type") == 1
    else:
        assert name not in warnings


def test_a_command_line_value_is_checked_by_the_run_that_uses_it(
    project, tmp_path, capsys
):
    _with_root(project)
    entry = ["-D", "matlab_api_check_files=../x.m"]
    assert sphinx_build(["-q", "-E", *entry, str(project), str(tmp_path / "h")]) == 0
    assert config_warnings(capsys.readouterr().err) == [config_warning(OUTSIDE, API)]
    api = ["-b", "matlab-api-check", str(project), str(tmp_path / "a")]
    assert sphinx_build(["-q", "-E", *entry, *api]) == 2
    assert_configuration_error(capsys.readouterr().err, OUTSIDE)


@pytest.mark.parametrize(("flag", "written"), [("0", False), ("1", True)])
def test_a_boolean_from_the_command_line(project, tmp_path, capsys, flag, written):
    _with_root(project)
    out = tmp_path / "out"
    argv = ["-q", "-E", "-D", f"matlab_stable_urls={flag}", str(project), str(out)]
    assert sphinx_build(argv) == 0
    assert capsys.readouterr().err == ""
    assert (out / "mat" / "ref" / "+pkg" / "f.m.html").exists() is written


def test_a_bad_value_set_by_another_extension(make_app, project):
    """Like sphinx-multiproject: values set before the checks are checked."""
    _with_root(project)
    with open(project / "conf.py", "a", encoding="utf-8") as conf:
        conf.write(
            "def setup(app):\n"
            "    def inject(app, config):\n"
            '        config["matlab_api_check_files"] = 5\n'
            '    app.connect("config-inited", inject, priority=-999)\n'
        )
    app = make_app(srcdir=project)
    assert config_warnings(app.warning.getvalue()) == [
        config_warning(
            "matlab_api_check_files must be None, a list of paths or glob "
            "patterns, or a string of them separated by commas.",
            API,
        )
    ]
    with pytest.raises(ConfigError, match=r"^matlab_api_check_files must be None"):
        make_app("matlab-api-check", srcdir=project)
