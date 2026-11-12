"""An incremental HTML build gives the same output as a clean one (G4-T3).

For each edit: a clean HTML build of a small project, the edit, an incremental
HTML build into the same output and doctree folders, and a clean HTML build of
the edited project in fresh folders. The two output trees must be equal under
``snapshot``. The two-builder variant runs ``matlab-api-check`` and ``text``
on the same doctree folder (other output folders) between the edit and the
incremental HTML build, as the user guide allows for the API check. The three
``*_after_another_builder`` tests show each cause of G4-T3 on the smallest
project, with api-check alone (fixed by G4-F8: the HTML build that follows
another builder's reading writes every page once, and removes the pages of
documents gone since its last build).

The project's files are a minute old; every edit changes the size of the
files it writes and sets their modification time to now (``_touch``), so it
is never hidden by an unchanged ``(mtime_ns, size)`` key. Renamed files keep
their size and get a new path and time.
"""

import json
import os
import re
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any, cast

import pytest
from sphinx.cmd.build import build_main
from sphinx.util.inventory import InventoryFile
from test_apidoc import FUNCTION

from sphinxcontrib.matlab_apidoc import main as apidoc

ROOT = Path(__file__).parent
MODEL = ROOT / "simulink" / "fixtures" / "R2020a" / "slx" / "probeModel.slx"

CONF = (
    'project = "Edits"\n'
    'extensions = ["sphinxcontrib.matlab"]\n'
    'matlab_src_code_project_root = "src"\n'
    'matlab_src_sidecar_suffixes = [".rst"]\n'
    'matlab_apidoc_output_dir = "api"\n'
    'matlab_apidoc_group = "folder"\n'
    "html_last_updated_fmt = None\n"
)

PAGES = {
    "conf.py": CONF,
    "index.rst": "Edits\n=====\n\n.. toctree::\n\n   api/index\n   links\n"
    "   p1\n   p2\n",
    "links.rst": "Links\n=====\n\n"
    ":mat:func:`alpha`, :mat:func:`beta`, :mat:func:`gamma`, "
    ":mat:obj:`thing`, :mat:obj:`mexed`, :mat:func:`manual`, "
    ":mat:obj:`model`, :mat:folder:`lib/`, :mat:folder:`core/`, "
    ":mat:sidecar:`lib/notes.rst`, :mat:sidecar:`lib/guide.rst`.\n",
    "p1.rst": "P1\n==\n\n.. mat:function:: manual(x)\n\n   Manual.\n",
    "p2.rst": "P2\n==\n\nNothing yet.\n",
}

SOURCES = {
    "src/lib/alpha.m": FUNCTION.format(name="alpha"),
    "src/lib/beta.m": FUNCTION.format(name="beta"),
    "src/lib/notes.rst": "Notes\n=====\n\nAbout :mat:func:`alpha`.\n",
    "src/tools/mexed.m": "% MEXED Help for a MEX function.\n%   mexed(x)\n",
    "src/shape/thing.m": FUNCTION.format(name="thing"),
}


def _touch(path):
    """Set the modification time of ``path`` to now: after the project's
    files (a minute old, ``make_project``) and the first build's output.
    """
    now = time.time_ns()
    os.utime(path, ns=(now, now))


def _write(root, path, text):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    _touch(target)


def _set_description(slx, text):
    """Rewrite the model description in ``slx`` (a different size)."""
    with zipfile.ZipFile(slx) as z:
        items = [(i, z.read(i.filename)) for i in z.infolist()]
    with zipfile.ZipFile(slx, "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in items:
            if info.filename == "metadata/coreProperties.xml":
                data = re.sub(
                    rb"<dc:description>.*?</dc:description>",
                    f"<dc:description>{text}</dc:description>".encode(),
                    data,
                    flags=re.DOTALL,
                )
            z.writestr(info, data)
    _touch(slx)


def _rename(root, old, new):
    (root / old).rename(root / new)
    for path in (root / new).rglob("*"):
        _touch(path)
    _touch(root / new)


def _remove(root, path):
    (root / path).unlink()
    _touch((root / path).parent)


EDITS = {
    "no_edit": lambda _root: None,
    "help_text": lambda r: _write(
        r, "src/lib/alpha.m", "function alpha()\n% alpha new and longer help.\nend\n"
    ),
    "add_file": lambda r: _write(r, "src/lib/gamma.m", FUNCTION.format(name="gamma")),
    "remove_file": lambda r: _remove(r, "src/lib/beta.m"),
    "move_directive": lambda r: (
        _write(r, "p1.rst", "P1\n==\n\nMoved away.\n"),
        _write(r, "p2.rst", "P2\n==\n\n.. mat:function:: manual(x)\n\n   Manual.\n"),
    ),
    "rename_folder": lambda r: _rename(r, "src/lib", "src/core"),
    "add_mex": lambda r: _write(r, "src/tools/mexed.mexa64", "binary"),
    "function_to_classdef": lambda r: _write(
        r, "src/shape/thing.m", "classdef thing\n% thing class help.\nend\n"
    ),
    "same_name": lambda r: _write(
        r, "src/shape/alpha.m", FUNCTION.format(name="alpha")
    ),
    "add_sidecar": lambda r: _write(r, "src/lib/guide.rst", "Guide\n=====\n\nNew.\n"),
    "remove_sidecar": lambda r: _remove(r, "src/lib/notes.rst"),
    "change_slx": lambda r: _set_description(
        r / "src/model.slx", "A changed and longer description"
    ),
}

# Edits applied to a project that already has the state the edit removes.
SETUP = {
    "remove_mex": ("add_mex", lambda r: _remove(r, "src/tools/mexed.mexa64")),
}


def make_project(root, setup=None):
    for path, text in {**PAGES, **SOURCES}.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    shutil.copyfile(MODEL, root / "src" / "model.slx")
    if setup:
        EDITS[setup](root)
    stamp = time.time_ns() - 60 * 10**9
    for path in root.rglob("*"):
        os.utime(path, ns=(stamp, stamp))


def run_apidoc(root):
    assert apidoc(["-q", "-c", str(root)]) == 0


def build(make_app, root, builddir, buildername="html"):
    run_apidoc(root)
    app = make_app(buildername, srcdir=root, builddir=builddir)
    app.build()
    app.cleanup()
    return Path(app.outdir)


def snapshot(outdir):
    """``{relative path: content}`` of every file below ``outdir``.

    Files are compared byte for byte, except ``objects.inv`` (decoded, as a
    sorted list of entries) and ``searchindex.js`` (decoded, without two
    things an incremental build of plain Sphinx 9.2 also leaves out or
    behind: the index entries of the pages it does not write, and terms that
    no page has any more).
    """
    out = {}
    for path in sorted(outdir.rglob("*")):
        rel = path.relative_to(outdir).as_posix()
        if path.is_dir():
            continue
        if rel == "objects.inv":
            with open(path, "rb") as f:
                inv = InventoryFile.load(cast(Any, f), "", lambda _base, uri: uri)
            # Sphinx before 8.2 gives tuples (project, version, uri, display).
            out[rel] = sorted(
                (
                    kind,
                    name,
                    *(
                        item[2:4]
                        if isinstance(item, tuple)
                        else (item.uri, item.display_name)
                    ),
                )
                for kind, items in inv.items()
                for name, item in items.items()
            )
        elif rel == "searchindex.js":
            text = path.read_text(encoding="utf-8")
            index = json.loads(text.removeprefix("Search.setIndex(").rstrip(")\n"))
            index.pop("indexentries")
            for key in ("terms", "titleterms"):
                index[key] = {
                    term: docs if isinstance(docs, list) else [docs]
                    for term, docs in index[key].items()
                    if docs != []
                }
            out[rel] = index
        else:
            out[rel] = path.read_bytes()
    return out


def differences(a, b):
    keys = sorted(set(a) | set(b))
    return [k for k in keys if a.get(k) != b.get(k)]


def run_cell(make_app, tmp_path, edit, other_builders):
    """Output snapshots of the build before ``edit``, the incremental build
    after it, and the clean build of the edited project.
    """
    inc = tmp_path / "inc"
    setup, apply = SETUP.get(edit) or (None, EDITS[edit])
    make_project(inc, setup)
    before = snapshot(build(make_app, inc, inc / "_build"))
    apply(inc)
    if other_builders:
        for name in ("matlab-api-check", "text"):
            build(make_app, inc, inc / "_build", name)
    incremental = build(make_app, inc, inc / "_build")

    clean = tmp_path / "clean"
    make_project(clean, setup)
    apply(clean)
    fresh = build(make_app, clean, clean / "_build")
    return before, snapshot(incremental), snapshot(fresh)


def test_two_clean_builds_are_equal(make_app, tmp_path):
    one, two = tmp_path / "one", tmp_path / "two"
    make_project(one)
    make_project(two)
    a = snapshot(build(make_app, one, one / "_build"))
    b = snapshot(build(make_app, two, two / "_build"))
    assert a.keys() == b.keys()
    assert differences(a, b) == []


CELLS = [
    pytest.param(edit, other, id=f"{edit}-{'shared_d' if other else 'html'}")
    for other in (False, True)
    for edit in (*EDITS, *SETUP)
]


@pytest.mark.parametrize(("edit", "other_builders"), CELLS)
def test_incremental_equals_clean(make_app, tmp_path, edit, other_builders):
    before, incremental, clean = run_cell(make_app, tmp_path, edit, other_builders)
    # The edit changes the output (no_edit: it does not).
    assert (differences(before, clean) == []) == (edit == "no_edit")
    assert differences(incremental, clean) == []


# The smallest projects for each cause, with matlab-api-check alone as the
# other builder (the user guide allows sharing -d with it).

MINIMAL_CONF = (
    'extensions = ["sphinxcontrib.matlab"]\nmatlab_src_code_project_root = "src"\n'
)


def minimal(root, files):
    for path, text in files.items():
        _write(root, path, text)
    stamp = time.time_ns() - 60 * 10**9
    for path in root.rglob("*"):
        os.utime(path, ns=(stamp, stamp))


with_and_without_check = pytest.mark.parametrize(
    "check", [False, True], ids=["html", "api_check"]
)


def html_edit_html(make_app, root, edit, check):
    """HTML build, ``edit``, api-check if ``check``, HTML build; return the
    output folder.
    """
    builddir = root / "_build"
    names = (
        ("html", None, "matlab-api-check", "html") if check else ("html", None, "html")
    )
    for name in names:
        if name is None:
            edit(root)
            continue
        app = make_app(name, srcdir=root, builddir=builddir)
        app.build()
        app.cleanup()
    return builddir / "html"


@with_and_without_check
def test_link_to_a_moved_object_after_another_builder(make_app, tmp_path, check):
    minimal(
        tmp_path,
        {
            "conf.py": MINIMAL_CONF,
            "src/.keep": "",
            "index.rst": "I\n=\n\n.. toctree::\n\n   a\n   b\n   c\n",
            "a.rst": "A\n=\n\n.. mat:function:: manual\n",
            "b.rst": "B\n=\n\nSee :mat:func:`manual`.\n",
            "c.rst": "C\n=\n",
        },
    )

    def move(root):
        _write(root, "a.rst", "A\n=\n\nMoved.\n")
        _write(root, "c.rst", "C\n=\n\n.. mat:function:: manual\n")

    outdir = html_edit_html(make_app, tmp_path, move, check)
    assert 'href="c.html#mat-manual"' in (outdir / "b.html").read_text(encoding="utf-8")


@with_and_without_check
def test_changed_help_after_another_builder(make_app, tmp_path, check):
    minimal(
        tmp_path,
        {
            "conf.py": MINIMAL_CONF,
            "index.rst": "I\n=\n\n.. mat:autofunction:: alpha\n",
            "src/alpha.m": FUNCTION.format(name="alpha"),
        },
    )

    def edit(root):
        _write(root, "src/alpha.m", "function alpha()\n% alpha new help.\nend\n")

    outdir = html_edit_html(make_app, tmp_path, edit, check)
    assert "alpha new help." in (outdir / "index.html").read_text(encoding="utf-8")


@with_and_without_check
def test_removed_api_page_after_another_builder(make_app, tmp_path, check):
    minimal(
        tmp_path,
        {
            "conf.py": MINIMAL_CONF + 'matlab_apidoc_output_dir = "api"\n'
            'matlab_apidoc_group = "folder"\n',
            "index.rst": "I\n=\n\n.. toctree::\n\n   api/index\n",
            "src/one/alpha.m": FUNCTION.format(name="alpha"),
            "src/two/beta.m": FUNCTION.format(name="beta"),
        },
    )
    run_apidoc(tmp_path)

    def edit(root):
        shutil.rmtree(root / "src" / "two")
        run_apidoc(root)

    outdir = html_edit_html(make_app, tmp_path, edit, check)
    assert (outdir / "api/one/index.html").is_file()
    assert not (outdir / "api/two/index.html").exists()


# What each build writes (G4-F8). A build that read nothing and whose output
# is in step with the environment writes nothing; one that follows another
# builder's reading writes every page once.

COUNT_FILES = {
    "conf.py": MINIMAL_CONF,
    "index.rst": "I\n=\n\n.. toctree::\n\n   a\n   b\n",
    "a.rst": "A\n=\n\n.. mat:autofunction:: alpha\n",
    "b.rst": "B\n=\n\nText.\n",
    "src/alpha.m": FUNCTION.format(name="alpha"),
}
ALL = {"index", "a", "b"}
UP_TO_DATE = "no targets are out of date"


def run(make_app, root, name="html", builddir=None, **kwargs):
    """Build; return the documents whose page was written, and the status."""
    app = make_app(name, srcdir=root, builddir=builddir or root / "_build", **kwargs)
    pages = []
    app.connect("html-page-context", lambda _app, page, *_: pages.append(page))
    app.build()
    app.cleanup()
    return set(pages) & set(app.env.found_docs), app.status.getvalue()


def test_one_builder_writes_what_it_read(make_app, tmp_path):
    minimal(tmp_path, COUNT_FILES)
    assert run(make_app, tmp_path)[0] == ALL
    written, status = run(make_app, tmp_path)
    assert written == set()
    assert UP_TO_DATE in status
    _write(tmp_path, "b.rst", "B\n=\n\nMore text.\n")
    assert run(make_app, tmp_path)[0] == {"b", "index"}  # index: toctree parent
    _write(tmp_path, "src/alpha.m", "function alpha()\n% alpha new help.\nend\n")
    assert run(make_app, tmp_path)[0] == {"a", "index"}
    # api-check with nothing changed reads nothing: the HTML output stays
    # in step and the next HTML build writes nothing.
    run(make_app, tmp_path, "matlab-api-check")
    written, status = run(make_app, tmp_path)
    assert written == set()
    assert UP_TO_DATE in status


def test_an_output_out_of_step_writes_every_page_once(make_app, tmp_path):
    minimal(tmp_path, COUNT_FILES)
    run(make_app, tmp_path)
    _write(tmp_path, "b.rst", "B\n=\n\nMore text.\n")
    run(make_app, tmp_path, "matlab-api-check")  # reads b
    written, status = run(make_app, tmp_path)
    assert written == ALL
    assert "0 added, 0 changed, 0 removed" in status  # nothing read
    assert "More text." in (tmp_path / "_build/html/b.html").read_text(encoding="utf-8")
    written, status = run(make_app, tmp_path)
    assert written == set()
    assert UP_TO_DATE in status


def test_html_and_dirhtml_on_one_doctree_folder(make_app, tmp_path):
    minimal(
        tmp_path,
        {
            "conf.py": MINIMAL_CONF,
            "src/.keep": "",
            "index.rst": "I\n=\n\n.. toctree::\n\n   a\n   b\n   c\n",
            "a.rst": "A\n=\n\n.. mat:function:: manual\n",
            "b.rst": "B\n=\n\nSee :mat:func:`manual`.\n",
            "c.rst": "C\n=\n",
        },
    )
    out = tmp_path / "_build"
    found = {"index", "a", "b", "c"}
    assert run(make_app, tmp_path, "html")[0] == found
    assert run(make_app, tmp_path, "dirhtml")[0] == found
    assert run(make_app, tmp_path, "html")[0] == set()
    for first, second, target in (("html", "dirhtml", "c"), ("dirhtml", "html", "a")):
        source = "a" if target == "c" else "c"
        _write(tmp_path, f"{source}.rst", f"{source.upper()}\n=\n\nMoved.\n")
        _write(
            tmp_path,
            f"{target}.rst",
            f"{target.upper()}\n=\n\n.. mat:function:: manual\n",
        )
        assert run(make_app, tmp_path, first)[0] == {"a", "b", "c", "index"}
        assert run(make_app, tmp_path, second)[0] == found  # out of step
        assert run(make_app, tmp_path, first)[0] == set()
        assert run(make_app, tmp_path, second)[0] == set()
        html = (out / "html/b.html").read_text(encoding="utf-8")
        dirhtml = (out / "dirhtml/b/index.html").read_text(encoding="utf-8")
        assert f'href="{target}.html#mat-manual"' in html
        assert f'href="../{target}/#mat-manual"' in dirhtml


def test_two_html_output_folders_on_one_doctree_folder(tmp_path):
    minimal(
        tmp_path,
        {
            "conf.py": MINIMAL_CONF,
            "index.rst": "I\n=\n\n.. mat:autofunction:: alpha\n",
            "src/alpha.m": FUNCTION.format(name="alpha"),
        },
    )
    doctrees = tmp_path / "_build" / "doctrees"

    def html(name):
        out = tmp_path / "_build" / name
        argv = ["-q", "-b", "html", "-d", str(doctrees), str(tmp_path), str(out)]
        assert build_main(argv) == 0
        return (out / "index.html").read_text(encoding="utf-8")

    html("one")
    html("two")
    _write(tmp_path, "src/alpha.m", "function alpha()\n% alpha new help.\nend\n")
    assert "alpha new help." in html("one")
    assert "alpha new help." in html("two")


def test_serial_and_parallel_builds_agree(make_app, tmp_path):
    outputs = []
    for parallel in (0, 2):
        root = tmp_path / f"j{parallel}"
        make_project(root)
        build(make_app, root, root / "_build")
        EDITS["rename_folder"](root)
        run_apidoc(root)
        app = make_app(
            "matlab-api-check", srcdir=root, builddir=root / "_build", parallel=parallel
        )
        app.build()
        app.cleanup()
        run_apidoc(root)
        app = make_app("html", srcdir=root, builddir=root / "_build", parallel=parallel)
        app.build()
        app.cleanup()
        # api-check read the edit; the HTML build wrote every page.
        assert app.env.get_domain("mat").data["in_step"] == {
            (name, os.path.normcase(os.path.abspath(root / "_build" / name)))
            for name in ("matlab-api-check", "html")
        }
        outputs.append(snapshot(root / "_build" / "html"))
    assert not (tmp_path / "j2/_build/html/api/lib").exists()
    assert differences(*outputs) == []


TWO_FOLDERS = {
    "conf.py": MINIMAL_CONF + 'matlab_apidoc_output_dir = "api"\n'
    'matlab_apidoc_group = "folder"\n',
    "index.rst": "I\n=\n\n.. toctree::\n\n   api/index\n",
    "src/one/alpha.m": FUNCTION.format(name="alpha"),
    "src/two/beta.m": FUNCTION.format(name="beta"),
}


def test_only_pages_this_output_wrote_are_removed(make_app, tmp_path):
    minimal(tmp_path, TWO_FOLDERS)
    run_apidoc(tmp_path)
    run(make_app, tmp_path)
    api = tmp_path / "_build" / "html" / "api"
    # The user's own files below the API folder of the output, one where the
    # page of a document would be that this output never wrote.
    mine = {api / "mine.html": "mine\n", api / "three" / "index.html": "three\n"}
    for path, text in mine.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    _write(tmp_path, "src/three/gamma.m", FUNCTION.format(name="gamma"))
    run_apidoc(tmp_path)
    run(make_app, tmp_path, "matlab-api-check")  # reads api/three/index
    shutil.rmtree(tmp_path / "src" / "three")
    shutil.rmtree(tmp_path / "src" / "two")
    run_apidoc(tmp_path)
    run(make_app, tmp_path, "matlab-api-check")  # removes api/two, api/three
    assert run(make_app, tmp_path)[0] == {"index", "api/index", "api/one/index"}
    assert not (api / "two").exists()
    assert not (tmp_path / "_build/html/_sources/api/two").exists()
    assert (api / "one" / "index.html").is_file()
    for path, text in mine.items():
        assert path.read_text(encoding="utf-8") == text


@pytest.mark.parametrize("change", ["config", "fresh_env"])
def test_config_change_and_fresh_env_after_another_builder(make_app, tmp_path, change):
    """A changed configuration keeps the build state: the page of the
    removed document goes. ``-E`` starts a new environment without it:
    every page is read and written, and the page stays, as Sphinx keeps the
    pages of removed documents (``make clean``).
    """
    minimal(tmp_path, TWO_FOLDERS)
    run_apidoc(tmp_path)
    run(make_app, tmp_path)
    shutil.rmtree(tmp_path / "src" / "two")
    run_apidoc(tmp_path)
    run(make_app, tmp_path, "matlab-api-check")
    if change == "config":
        kwargs: dict[str, Any] = {"confoverrides": {"rst_epilog": ".. |x| replace:: x"}}
    else:
        kwargs = {"freshenv": True}
    written, status = run(make_app, tmp_path, **kwargs)
    assert written == {"index", "api/index", "api/one/index"}
    assert "3 changed" in status or "3 added" in status
    assert (tmp_path / "_build/html/api/two/index.html").exists() == (
        change == "fresh_env"
    )
