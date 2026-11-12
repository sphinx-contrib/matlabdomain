"""Chooser pages are rendered only when they may differ from the files on disk
(G4-F11): a build that writes no document page, whose chooser data is that of
``mat/choosers.json`` and whose chooser files all exist renders none.

Rendered pages are counted through ``html-page-context``, not timed.
"""

import json
from pathlib import Path

import pytest
from sphinx.errors import ExtensionError
from test_apidoc import FUNCTION
from test_incremental_equals_clean import MINIMAL_CONF, _write, minimal

from sphinxcontrib import mat_urls

FILES = {
    "conf.py": MINIMAL_CONF,
    "index.rst": "I\n=\n\n.. toctree::\n\n   api\n   other\n",
    "api.rst": "API\n===\n\n"
    + "".join(
        f".. mat:autofunction:: {folder}/{name}.m\n\n"
        for folder in ("a", "b")
        for name in ("helper", "util")
    ),
    "other.rst": "Other\n=====\n\nText.\n",
    **{
        f"src/{folder}/{name}.m": FUNCTION.format(name=name)
        for folder in ("a", "b")
        for name in ("helper", "util")
    },
}
CHOOSERS = {"mat/name/helper", "mat/name/util"}


def build(make_app, root, name="html", **kwargs):
    """Build; return the chooser pages and the documents rendered, and the
    warnings.
    """
    app = make_app(name, srcdir=root, builddir=root / "_build", **kwargs)
    pages = []
    app.connect("html-page-context", lambda _app, page, *_: pages.append(page))
    app.build()
    app.cleanup()
    rendered = {page for page in pages if page.startswith("mat/name/")}
    return rendered, set(pages) & set(app.env.found_docs), app.warning.getvalue()


def mat_files(outdir):
    return {
        path.relative_to(outdir).as_posix(): path.read_bytes()
        for path in sorted((outdir / "mat").rglob("*"))
        if path.is_file()
    }


def project(make_app, root, **kwargs):
    minimal(root, FILES)
    assert build(make_app, root, **kwargs)[0] == CHOOSERS
    outdir = root / "_build" / "html"
    state = outdir / mat_urls.STATE
    assert mat_urls.MARKER in state.read_text(encoding="utf-8")
    for stub in CHOOSERS:
        page = (outdir / f"{stub}.html").read_text(encoding="utf-8")
        assert mat_urls.MARKER in page
        assert 'href="../../_static/' in page  # themed
    return outdir


@pytest.mark.parametrize("parallel", [0, 2])
def test_no_change_renders_no_chooser_page(make_app, tmp_path, parallel):
    outdir = project(make_app, tmp_path, parallel=parallel)
    before = mat_files(outdir)
    rendered, written, warnings = build(make_app, tmp_path, parallel=parallel)
    assert (rendered, written, warnings) == (set(), set(), "")
    assert mat_files(outdir) == before  # themed pages kept, state the same


@pytest.mark.parametrize("parallel", [0, 2])
def test_a_written_page_renders_every_chooser_page(make_app, tmp_path, parallel):
    outdir = project(make_app, tmp_path, parallel=parallel)
    before = mat_files(outdir)
    _write(tmp_path, "other.rst", "Other\n=====\n\nMore text.\n")
    rendered, written, _ = build(make_app, tmp_path, parallel=parallel)
    # With -j the spy sees only the pages of the main process.
    assert "More text." in (outdir / "other.html").read_text(encoding="utf-8")
    assert "api" not in written
    assert rendered == CHOOSERS
    assert mat_files(outdir) == before


def test_changed_state_renders_every_chooser_page(make_app, tmp_path):
    outdir = project(make_app, tmp_path)
    before = mat_files(outdir)
    state = outdir / mat_urls.STATE
    data = json.loads(state.read_text(encoding="utf-8"))
    data["sha256"] = "0" * 64  # as if a chooser set or target had changed
    state.write_text(json.dumps(data), encoding="utf-8")
    rendered, _, warnings = build(make_app, tmp_path)
    assert (rendered, warnings) == (CHOOSERS, "")
    assert mat_files(outdir) == before  # state rewritten


def test_missing_chooser_file_renders_every_chooser_page(make_app, tmp_path):
    outdir = project(make_app, tmp_path)
    before = mat_files(outdir)
    (outdir / "mat/name/helper.html").unlink()
    rendered, _, warnings = build(make_app, tmp_path)
    assert (rendered, warnings) == (CHOOSERS, "")
    assert mat_files(outdir) == before


@pytest.mark.parametrize("state", ["missing", "empty", "invalid", "other_version"])
def test_unusable_state_renders_every_chooser_page(make_app, tmp_path, state):
    outdir = project(make_app, tmp_path)
    before = mat_files(outdir)
    path = outdir / mat_urls.STATE
    if state == "missing":
        path.unlink()
    elif state == "empty":
        path.write_bytes(b"")
    elif state == "invalid":
        path.write_bytes(b"{not json\xff")
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["matlabdomain"] = "0.0.1"
        path.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    rendered, _, warnings = build(make_app, tmp_path)
    assert (rendered, warnings) == (CHOOSERS, "")
    assert mat_files(outdir) == before


def _fail(*_args):
    raise RuntimeError("interrupted")


@pytest.mark.parametrize("event", ["html-collect-pages", "build-finished"])
def test_failed_build_leaves_no_state(make_app, tmp_path, event):
    outdir = project(make_app, tmp_path)
    before = mat_files(outdir)
    _write(tmp_path, "other.rst", "Other\n=====\n\nMore text.\n")
    app = make_app(srcdir=tmp_path, builddir=tmp_path / "_build")
    # Before this extension's handlers: pages are written, nothing collected
    # or finished.
    app.connect(event, _fail, priority=100)
    with pytest.raises(Exception, match="interrupted"):
        app.build()
    app.cleanup()
    assert (outdir / "other.html").read_text(encoding="utf-8").count("More text.")
    assert not (outdir / mat_urls.STATE).exists()
    # Sphinx has nothing to write: the chooser pages are rendered anyway.
    rendered, _, warnings = build(make_app, tmp_path)
    assert (rendered, warnings) == (CHOOSERS, "")
    assert mat_files(outdir) == before


@pytest.mark.parametrize("name", ["dirhtml", "singlehtml"])
def test_plain_choosers_have_no_state(make_app, tmp_path, name):
    minimal(tmp_path, FILES)
    outdir = tmp_path / "_build" / name
    for _ in range(2):
        rendered, _, warnings = build(make_app, tmp_path, name)
        assert (rendered, warnings) == (set(), "")
        files = mat_files(outdir)
        assert mat_urls.STATE not in files
        for stub in CHOOSERS:
            page = files[f"{stub}.html"].decode("utf-8")
            assert page.splitlines()[1] == mat_urls.MARKER
            assert "<style>" in page  # plain


def test_json_has_no_stable_addresses(make_app, tmp_path):
    minimal(tmp_path, FILES)
    rendered, _, _ = build(make_app, tmp_path, "json")
    assert rendered == set()
    assert not (tmp_path / "_build" / "json" / "mat").exists()


def test_redirects_keep_current_themed_pages(make_app, tmp_path):
    """Sphinx < 8.2 does not collect pages in a build that writes nothing;
    ``write_redirects`` then keeps the themed pages if they are current, else
    writes plain ones (and no state).
    """
    minimal(tmp_path, FILES)
    app = make_app(srcdir=tmp_path, builddir=tmp_path / "_build")
    app.build()
    outdir = Path(app.outdir)
    before = mat_files(outdir)
    app.builder.mat_chooser_pages = app.builder.mat_chooser_state = None
    mat_urls.write_redirects(app, None)
    assert mat_files(outdir) == before
    (outdir / mat_urls.STATE).unlink()
    app.builder.mat_chooser_pages = None
    mat_urls.write_redirects(app, None)
    app.cleanup()
    files = mat_files(outdir)
    assert mat_urls.STATE not in files
    assert "<style>" in files["mat/name/helper.html"].decode("utf-8")
    # dirhtml: plain pages either way.
    app = make_app("dirhtml", srcdir=tmp_path, builddir=tmp_path / "_build")
    app.build()
    outdir = Path(app.outdir)
    before = mat_files(outdir)
    app.builder.mat_chooser_pages = None
    mat_urls.write_redirects(app, None)
    app.cleanup()
    assert mat_files(outdir) == before


def test_state_holds_no_path_or_time(make_app, tmp_path):
    outdir = project(make_app, tmp_path)
    text = (outdir / mat_urls.STATE).read_text(encoding="utf-8")
    assert tmp_path.name not in text
    assert set(json.loads(text)) == {
        "builder",
        "marker",
        "matlabdomain",
        "pages",
        "sha256",
        "sphinx",
    }


def test_unowned_state_is_not_overwritten(make_app, tmp_path):
    # A state cut short is this extension's; a JSON file without the marker
    # is not.
    minimal(tmp_path, FILES)
    app = make_app(srcdir=tmp_path, builddir=tmp_path / "_build")
    path = Path(app.outdir) / mat_urls.STATE
    path.parent.mkdir(parents=True)
    path.write_text('{"mine": 1}', encoding="utf-8")
    with pytest.raises(ExtensionError, match="unowned file"):
        mat_urls.add_script(app)
    app.cleanup()
    assert path.read_text(encoding="utf-8") == '{"mine": 1}'
