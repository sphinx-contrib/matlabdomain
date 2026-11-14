"""The HTML build writes the state of simulinkDocumentationLinker.m and leaves
the committed settings alone (``mat_simulink/_linker.py``).
"""

import json

import pytest
from sphinx.errors import ConfigError

from sphinxcontrib.mat_simulink import _linker

FUNCTION = "function f\n% F does nothing.\nend\n"
CONF = (
    'extensions = ["sphinxcontrib.matlab"]\n'
    'matlab_src_code_project_root = ".."\n'
    'matlab_src_include_patterns = ["src/**"]\n'
)


def project(
    tmp_path, settings: str | None = '{"mode": "local", "local": "old/"}', conf=""
):
    root = tmp_path / "proj"
    (root / "src").mkdir(parents=True)
    (root / "src" / "f.m").write_text(FUNCTION)
    docs = root / "docs"
    docs.mkdir()
    (docs / "conf.py").write_text(CONF + conf)
    (docs / "index.rst").write_text("Index\n=====\n\n.. mat:autofunction:: src/f.m\n")
    if settings is not None:
        folder = root / "+sphinxcontrib" / "+matlabdomain"
        folder.mkdir(parents=True)
        (folder / _linker.NAME).write_text(settings)
    return root


def build(make_app, root, **overrides):
    app = make_app(srcdir=root / "docs", confoverrides=overrides)
    app.build()
    app.cleanup()
    return app


def settings(root):
    path = root / "+sphinxcontrib" / "+matlabdomain" / _linker.NAME
    return json.loads(path.read_text(encoding="utf-8"))


def state(root):
    path = root / "docs" / "_build" / "html" / "mat" / _linker.NAME
    return json.loads(path.read_text(encoding="utf-8"))


def test_build_writes_the_state_and_says_what_differs(make_app, tmp_path):
    root = project(tmp_path, conf='html_baseurl = "https://example.org/docs"\n')
    path = root / "+sphinxcontrib" / "+matlabdomain" / _linker.NAME
    before = path.read_bytes()
    app = build(make_app, root)
    assert state(root) == {"mode": "local"}
    assert path.read_bytes() == before
    log = app.status.getvalue()
    assert (
        "+sphinxcontrib/+matlabdomain/simulinkDocumentationLinker.json differs "
        "from this build: local is 'old/', this build has 'docs/_build/html/'; "
        "published is not set, this build has 'https://example.org/docs/'; the "
        "build does not change it" in log
    )
    assert app.warning.getvalue() == ""


def test_matching_settings_say_nothing(make_app, tmp_path):
    # A form without the trailing slash is the same address.
    text = '{"local": "docs/_build/html", "published": "https://example.org/docs/"}'
    root = project(tmp_path, text, conf='html_baseurl = "https://example.org/docs"\n')
    app = build(make_app, root)
    assert "differs" not in app.status.getvalue()
    assert settings(root) == json.loads(text)


def test_livehtml_writes_the_server_state_only(make_app, tmp_path):
    root = project(tmp_path, '{"mode": "local", "local": "docs/_build/html"}')
    app = build(
        make_app, root, matlab_simulink_autobuild_server="http://127.0.0.1:8123"
    )
    assert state(root) == {"mode": "server", "server": "http://127.0.0.1:8123/"}
    assert settings(root) == {"mode": "local", "local": "docs/_build/html"}
    assert "server is not set, this build has 'http://127.0.0.1:8123/'" in (
        app.status.getvalue()
    )
    build(make_app, root)
    assert state(root) == {"mode": "local"}


def test_multiversion_build_does_not_compare_local(make_app, tmp_path):
    conf = (
        'def setup(app):\n    app.add_config_value("smv_current_version", "", "html")\n'
    )
    root = project(tmp_path, conf=conf)
    app = build(make_app, root, smv_current_version="v1")
    assert settings(root) == {"mode": "local", "local": "old/"}
    assert state(root) == {"mode": "local"}
    assert "differs" not in app.status.getvalue()


@pytest.mark.parametrize("text", ["[1, 2]", "{"])
def test_bad_settings_are_not_compared(make_app, tmp_path, text):
    root = project(tmp_path, text)
    app = build(make_app, root)
    assert "is not a JSON object" in app.status.getvalue()
    assert "it is not compared with this build" in app.status.getvalue()
    assert app.warning.getvalue() == ""
    path = root / "+sphinxcontrib" / "+matlabdomain" / _linker.NAME
    assert path.read_text() == text
    assert state(root) == {"mode": "local"}


def test_projects_without_settings_get_nothing(make_app, tmp_path):
    root = project(tmp_path, None)
    build(make_app, root)
    assert not (root / "docs" / "_build" / "html" / "mat" / _linker.NAME).exists()
    assert not (root / "+sphinxcontrib").exists()


def test_bad_server(make_app, tmp_path):
    root = project(tmp_path)
    with pytest.raises(
        ConfigError, match="matlab_simulink_autobuild_server must be None"
    ):
        make_app(
            srcdir=root / "docs",
            confoverrides={"matlab_simulink_autobuild_server": "x"},
        )


def test_output_outside_the_root(tmp_path, monkeypatch):
    assert _linker._below(str(tmp_path / "a" / "b"), str(tmp_path)) == "a/b/"
    assert _linker._below(str(tmp_path), str(tmp_path / "a")) is None
    assert _linker._below(str(tmp_path / "x"), str(tmp_path / "a")) is None
    assert _linker._below(str(tmp_path), str(tmp_path)) is None

    def relpath(path, start):
        raise ValueError("another drive")

    monkeypatch.setattr(_linker.os.path, "relpath", relpath)
    assert _linker._below("D:\\out", "C:\\proj") is None
