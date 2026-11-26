"""Stable addresses of documented objects (mat_urls): redirect files that
follow an object to whichever page it is on, the "¶" links to them and the
inventory entries that point to them.
"""

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from sphinx.errors import ConfigError
from test_apidoc import FUNCTION, write
from test_config import assert_configuration_error, sphinx_build
from test_intersphinx import (
    anchors,
    build_library,
    follow,
    inventory,
    resolve,
    target,
)

from sphinxcontrib import mat_urls
from sphinxcontrib.matlab_apidoc import main as apidoc
from sphinxcontrib.matlab_apidoc._generate import MARKER

#: the error for a file the build did not write where a stable address goes
IN_THE_WAY = (
    r"^matlab_stable_urls: '.+' is in the way of a file of the stable "
    r"addresses, and the build does not overwrite a file it did not write\. "
    r"Remove or rename it \(html_extra_path or html_static_path may copy it "
    r"there\), or set matlab_stable_urls = False\.$"
)
CHOICE = re.compile(
    r'<a class="reference internal" href="([^"]*)"><code[^>]*>'
    r'<span class="pre">([^<]*)</span></code></a> \((\w+)\)'
)


def refs_map(outdir):
    text = (outdir / "mat/refs.js").read_text(encoding="utf-8")
    prefix = f"{mat_urls.JS_MARKER}\nwindow.matStableRefs = "
    assert text.startswith(prefix)
    return json.loads(text[len(prefix) :].rstrip().removesuffix(";"))


def test_stable_addresses_follow_a_moved_object(make_app, tmp_path):
    lib = tmp_path / "lib"
    outdir = build_library(make_app, lib, "namespace", 2)
    by_name, by_ref = "mat/name/scale.html", "mat/ref/util/scale.m.html"
    for stub in (by_name, by_ref):
        assert resolve(stub, target(outdir, stub)) == "api/global.html#mat-util/scale.m"
    assert 'class="headerlink" href="../mat/name/scale.html"' in (
        outdir / "api/global.html"
    ).read_text(encoding="utf-8")

    outdir = build_library(make_app, lib, "namespace", 2, ["util/alpha.m"])
    for stub in (by_name, by_ref):
        url = resolve(stub, target(outdir, stub))
        assert url == "api/global-2.html#mat-util/scale.m"
        assert "mat-util/scale.m" in anchors(outdir, url)


def test_names_of_several_objects_and_members(make_app, tmp_path):
    outdir = build_library(make_app, tmp_path / "lib", private=True)
    chooser = (outdir / "mat/name/helper.html").read_text(encoding="utf-8")
    assert "url=" not in chooser
    # A page in the site's theme, which this extension still owns.
    assert mat_mark_and_theme(chooser)
    assert CHOICE.findall(chooser) == [
        (
            "../../api/examples/index.html#mat-examples/helper.m",
            "examples/helper.m",
            "function",
        ),
        (
            "../../api/toolbox/index.html#mat-toolbox/helper.m",
            "toolbox/helper.m",
            "function",
        ),
    ]
    for stub in ("mat/ref/examples/helper.m.html", "mat/ref/toolbox/helper.m.html"):
        assert target(outdir, stub).startswith("../../../api/")
    member = "mat/name/geom.Circle.area.html"
    assert resolve(member, target(outdir, member)) == (
        "api/%2Bgeom/index.html#mat-+geom/Circle.m.area"
    )
    assert (outdir / "mat/ref/+geom/Circle.m.area.html").is_file()
    assert (outdir / "mat/ref/+geom/index.html").is_file()  # the folder
    assert (outdir / "mat/name/geom.html").is_file()  # the namespace
    # A private file has an address by path only.
    assert (outdir / "mat/ref/util/private/check.m.html").is_file()
    assert not (outdir / "mat/name/check.html").exists()
    # A plain folder has no MATLAB name.
    assert (outdir / "mat/ref/util/index.html").is_file()
    assert not (outdir / "mat/name/util.html").exists()


def mat_mark_and_theme(page):
    return mat_urls.MARKER in page and 'href="../../_static/' in page


@pytest.mark.parametrize(
    "conflict", ["mat/ref/one.m.html", "mat/refs.js", "_static/mat_urls.js"]
)
def test_unowned_stable_output_is_not_overwritten(make_app, tmp_path, conflict):
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\nmatlab_src_code_project_root = "."\n'
    )
    (tmp_path / "index.rst").write_text("Index\n=====\n\n.. mat:autofunction:: one\n")
    (tmp_path / "one.m").write_text("function one\n% ONE Help.\nend\n")
    app = make_app(srcdir=tmp_path)
    target_path = Path(app.outdir) / conflict
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("user-owned content", encoding="utf-8")
    with pytest.raises(ConfigError, match=IN_THE_WAY):
        if conflict.startswith("_static/"):
            mat_urls.add_script(app)
        else:
            app.build()
    assert target_path.read_text(encoding="utf-8") == "user-owned content"


def test_a_file_of_html_extra_path_in_the_way_stops_sphinx_build(tmp_path, capsys):
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\nmatlab_src_code_project_root = "."\n'
        'html_extra_path = ["extra"]\n'
    )
    (tmp_path / "index.rst").write_text("Index\n=====\n\n.. mat:autofunction:: one\n")
    (tmp_path / "one.m").write_text("function one\n% ONE Help.\nend\n")
    write(tmp_path, {"extra/mat/ref/one.m.html": "user-owned content"})
    out = tmp_path / "_build"
    assert sphinx_build(["-q", str(tmp_path), str(out)]) == 2
    err = capsys.readouterr().err
    message = re.search(IN_THE_WAY[1:-1], err)
    assert message is not None
    path = re.match(r"matlab_stable_urls: '(.+?)' is in the way", message[0])
    assert path is not None
    assert path[1].replace("\\\\", "/").endswith("/_build/mat/ref/one.m.html")
    assert_configuration_error(err, message[0])
    assert (out / "mat/ref/one.m.html").read_text() == "user-owned content"


def test_unowned_chooser_is_not_overwritten(make_app, tmp_path):
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\nmatlab_src_code_project_root = "."\n'
    )
    (tmp_path / "index.rst").write_text(
        "Index\n=====\n\n.. mat:autofunction:: a/helper.m\n\n"
        ".. mat:autofunction:: b/helper.m\n"
    )
    write(tmp_path, {"a/helper.m": FUNCTION.format(name="helper")})
    write(tmp_path, {"b/helper.m": FUNCTION.format(name="helper")})
    app = make_app(srcdir=tmp_path)
    target_path = Path(app.outdir) / "mat/name/helper.html"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("user-owned content", encoding="utf-8")
    with pytest.raises(ConfigError, match=IN_THE_WAY):
        app.build()
    assert target_path.read_text(encoding="utf-8") == "user-owned content"


def test_moved_object_script_and_not_found_page(make_app, tmp_path):
    outdir = build_library(make_app, tmp_path / "lib")
    script = (outdir / "_static" / mat_urls.SCRIPT).read_text(encoding="utf-8")
    assert "mat/refs.js" in script
    page = (outdir / "api/util/index.html").read_text(encoding="utf-8")
    # A clean build too: the script is there before the pages are written.
    assert f'src="../../_static/{mat_urls.SCRIPT}?v=' in page
    # Anchor (without mat-) -> stable address, "" if the same.
    refs = refs_map(outdir)
    assert refs["util/scale.m"] == ""
    assert refs["+geom/"] == "+geom/index"
    for key, value in refs.items():
        assert (outdir / f"mat/ref/{value or key}.html").is_file()
    not_found = (outdir / "404.html").read_text(encoding="utf-8")
    assert mat_urls.MARKER in not_found
    assert 'data-page="index.html"' in not_found
    assert "mat/refs.js" in not_found  # the script, inline


def test_plain_chooser_without_page_files(make_app, tmp_path):
    # dirhtml writes a page as a folder: the list is written as a plain page.
    write(tmp_path / "src", {"a/helper.m": FUNCTION.format(name="helper")})
    write(tmp_path / "src", {"b/helper.m": FUNCTION.format(name="helper")})
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\nmatlab_src_code_project_root = "src"\n'
    )
    (tmp_path / "index.rst").write_text(
        "Index\n=====\n\n.. mat:autofunction:: a/helper.m\n\n"
        ".. mat:autofunction:: b/helper.m\n"
    )
    app = make_app("dirhtml", srcdir=tmp_path)
    app.build()
    app.cleanup()
    outdir = Path(app.outdir)
    chooser = (outdir / "mat/name/helper.html").read_text(encoding="utf-8")
    assert chooser.splitlines()[1] == mat_urls.MARKER
    assert "<style>" in chooser
    assert [match[0] for match in CHOICE.findall(chooser)] == [
        "../../#mat-a/helper.m",
        "../../#mat-b/helper.m",
    ]


def test_turned_off(make_app, tmp_path):
    outdir = build_library(
        make_app, tmp_path / "lib", conf="matlab_stable_urls = False\n"
    )
    assert not (outdir / "mat").exists()
    page = (outdir / "api/util/index.html").read_text(encoding="utf-8")
    assert 'class="headerlink" href="#mat-util/scale.m"' in page
    assert mat_urls.SCRIPT not in page
    assert not (outdir / "404.html").exists()
    # The inventory keeps the page addresses.
    assert inventory(outdir)["util/scale.m"] == (
        "api/util/index.html#mat-util/scale.m",
        "scale",
    )


def test_no_inventory(tmp_path):
    # A builder of the HTML format that writes no objects.inv.
    mat_urls.rewrite_inventory(str(tmp_path / "objects.inv"), {"a.m": "x.html"})
    assert not (tmp_path / "objects.inv").exists()


def test_script_that_cannot_be_written(tmp_path, monkeypatch):
    (tmp_path / "_static" / mat_urls.SCRIPT).mkdir(parents=True)
    warnings = []
    monkeypatch.setattr(
        mat_urls.logger,
        "warning",
        lambda msg, *_args, **_kwargs: warnings.append(msg),
    )
    added = []
    app = SimpleNamespace(
        config=SimpleNamespace(matlab_stable_urls=True),
        builder=SimpleNamespace(
            format="html", out_suffix=".html", name="html", outdir=tmp_path
        ),
        add_js_file=added.append,
    )
    mat_urls.add_script(app)
    assert added == [mat_urls.SCRIPT]
    assert warnings == ["[sphinxcontrib-matlabdomain] cannot write %s: %s"]


def test_files_without_a_marker_are_not_ours(tmp_path):
    script = tmp_path / "_static" / mat_urls.SCRIPT
    script.parent.mkdir()
    first_line = mat_urls._JS.partition("\n")[0]
    for text in (f"{first_line}\nolder body\n", "user content"):
        script.write_text(text, encoding="utf-8")
        assert not mat_urls._is_ours(script)
    refs = tmp_path / mat_urls.REFS
    refs.parent.mkdir()
    refs.write_text('window.matStableRefs = {"a.m": ""};\n', encoding="utf-8")
    assert not mat_urls._is_ours(refs)


def test_unowned_refs_fail_before_pages_are_written(make_app, tmp_path):
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\nmatlab_src_code_project_root = "."\n'
    )
    (tmp_path / "index.rst").write_text("Index\n=====\n")
    refs = tmp_path / "_build" / "html" / mat_urls.REFS
    refs.parent.mkdir(parents=True)
    refs.write_text("user-owned content", encoding="utf-8")
    with pytest.raises(ConfigError, match=IN_THE_WAY):
        make_app(srcdir=tmp_path, builddir=tmp_path / "_build")
    assert refs.read_text(encoding="utf-8") == "user-owned content"
    assert not (refs.parents[1] / "index.html").exists()


BOX = """\
classdef Box
    % Box A box.
    properties
        Area % The area.
    end
    methods
        function a = area(obj)
            % area Compute the area.
            a = obj.Area;
        end
    end
end
"""


def test_names_differing_by_case_and_removed_objects(make_app, tmp_path):
    (tmp_path / "Box.m").write_text(BOX)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub/gone.m").write_text("function gone\n% gone Help.\nend\n")
    (tmp_path / "stay.m").write_text("function stay\n% stay Help.\nend\n")
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\nmatlab_src_code_project_root = "."\n'
    )
    index = tmp_path / "index.rst"
    index.write_text(
        "Index\n=====\n\n.. mat:autoclass:: Box\n   :members:\n\n"
        ".. mat:autofunction:: sub/gone.m\n\n.. mat:autofunction:: stay\n\n"
        "Mat notes\n---------\n\nText.\n"
    )
    app = make_app(srcdir=tmp_path)
    app.build()
    app.cleanup()
    outdir = Path(app.outdir)
    stubs = {
        p.relative_to(outdir).as_posix(): target(outdir, p.relative_to(outdir))
        for p in (outdir / "mat").rglob("*.html")
    }
    # Area and area would share a file on Windows and macOS: escaped apart.
    area = {s: t for s, t in stubs.items() if t.endswith(("Box.m.Area", "Box.m.area"))}
    assert len(area) == 4
    assert len({s.lower() for s in area}) == 4
    assert sorted(t.rpartition("#")[2] for t in area.values()) == [
        "mat-Box.m.Area",
        "mat-Box.m.Area",
        "mat-Box.m.area",
        "mat-Box.m.area",
    ]
    # The anchors differ in case only: their stable addresses are escaped.
    refs = refs_map(outdir)
    values = [refs["Box.m.Area"], refs["Box.m.area"]]
    assert all(values)
    assert len({v.lower() for v in values}) == 2
    assert stubs["mat/ref/sub/gone.m.html"] == "../../../index.html#mat-sub/gone.m"
    # A section whose id starts with mat- keeps its "¶" link.
    page = (outdir / "index.html").read_text(encoding="utf-8")
    assert 'class="headerlink" href="#mat-notes"' in page
    keep = outdir / "mat/name/notes.html"
    keep.write_text("not ours\n")
    (outdir / "mat/name/Box.html").unlink()
    (outdir / "mat/name/Box.html").mkdir()  # cannot be written
    (outdir / "mat/ref/stay.m.html").unlink()
    (outdir / "mat/ref/stay.m.html").mkdir()
    stay = outdir / "mat/name/stay.html"
    stay_mtime = stay.stat().st_mtime_ns
    (outdir / "404.html").write_text("mine\n")

    # Box moves to another page; gone.m is no longer documented.
    index.write_text(
        "Index\n=====\n\n.. toctree::\n\n   box\n\n.. mat:autofunction:: stay\n"
    )
    (tmp_path / "box.rst").write_text("Box\n===\n\n.. mat:autoclass:: Box\n")
    app = make_app(srcdir=tmp_path)
    app.build()
    app.cleanup()
    assert "cannot write" in app.warning.getvalue()
    assert target(outdir, "mat/ref/Box.m.html") == "../../box.html#mat-Box.m"
    assert not (outdir / "mat/name/gone.html").exists()
    assert not (outdir / "mat/ref/sub").exists()
    assert keep.is_file()
    assert stay.stat().st_mtime_ns == stay_mtime  # unchanged: not rewritten
    # The inventory points to the stable address only where it was written.
    inv = inventory(outdir)
    assert inv["Box.m"][0] == "mat/ref/Box.m.html"
    assert inv["stay.m"][0] == "index.html#mat-stay.m"
    assert (outdir / "404.html").read_text() == "mine\n"  # not ours: kept


def test_a_case_only_sibling_moves_the_address_of_the_existing_file(make_app, tmp_path):
    # Pinned as it is: the uppercase letters of Foo.m are escaped once it has
    # a sibling that differs only by case; foo.m keeps its plain name.
    (tmp_path / "Foo.m").write_text("function Foo\n% Foo Help.\nend\n")
    if (tmp_path / "foo.m").exists():
        pytest.skip("needs a case-sensitive file system")
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\nmatlab_src_code_project_root = "."\n'
    )
    index = tmp_path / "index.rst"
    index.write_text("Index\n=====\n\n.. mat:autofunction:: Foo\n")

    def stable_files():
        app = make_app(srcdir=tmp_path)
        app.build()
        app.cleanup()
        outdir = Path(app.outdir)
        return sorted(
            p.relative_to(outdir).as_posix() for p in (outdir / "mat").rglob("*.html")
        )

    assert stable_files() == ["mat/name/Foo.html", "mat/ref/Foo.m.html"]
    (tmp_path / "foo.m").write_text("function foo\n% foo Help.\nend\n")
    index.write_text(index.read_text() + "\n.. mat:autofunction:: foo\n")
    assert stable_files() == [
        "mat/name/foo.html",
        "mat/name/~46oo.html",
        "mat/ref/foo.m.html",
        "mat/ref/~46oo.m.html",
    ]


def test_incremental_builds_remove_stale_pages_and_relink(make_app, tmp_path):
    def build(files=(), remove=()):
        write(tmp_path / "src", {f: FUNCTION.format(name=Path(f).stem) for f in files})
        for name in remove:
            (tmp_path / name).unlink()
        assert apidoc(["-q", "-c", str(tmp_path)]) == 0
        app = make_app(srcdir=tmp_path)
        app.build()
        app.cleanup()
        return Path(app.outdir)

    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\nmatlab_src_code_project_root = "src"\n'
        'matlab_apidoc_output_dir = "api"\nmatlab_apidoc_group = "folder"\n'
        "matlab_apidoc_page_size = 1\n"
    )
    (tmp_path / "index.rst").write_text(
        "Index\n=====\n\n.. toctree::\n\n   api/index\n   links\n   extra\n"
    )
    (tmp_path / "links.rst").write_text("Links\n=====\n\n:mat:func:`util/scale.m`\n")
    (tmp_path / "extra.rst").write_text("Extra\n=====\n\nText.\n")
    outdir = build(["util/scale.m", "util/zeta.m", "old/f.m"])
    links = outdir / "links.html"
    assert 'href="api/util/index.html#mat-util/scale.m"' in links.read_text()

    # alpha.m sorts first: scale.m moves to index-2. links.rst is unchanged,
    # its page is written again.
    outdir = build(["util/alpha.m"])
    assert 'href="api/util/index-2.html#mat-util/scale.m"' in links.read_text()
    assert (outdir / "404.html").read_text().count(mat_urls.MARKER) == 1

    # Fewer pages: those whose source scmd apidoc removed go too;
    # the page of a removed hand-written source stays.
    removed = ["api/util/index-3.html", "_sources/api/util/index-3.rst.txt"]
    assert all((outdir / p).is_file() for p in removed)
    assert (outdir / "api/old/index.html").is_file()
    outdir = build(
        remove=["src/util/alpha.m", "src/util/zeta.m", "src/old/f.m", "extra.rst"]
    )
    assert 'href="api/util/index.html#mat-util/scale.m"' in links.read_text()
    assert not any((outdir / p).exists() for p in removed)
    assert not (outdir / "api/util/index-2.html").exists()
    assert not (outdir / "api/old").exists()
    assert (outdir / "api/util/index.html").is_file()
    assert (outdir / "extra.html").is_file()

    # Nothing moved: links.html is not written again.
    mtime = links.stat().st_mtime_ns
    build()
    assert links.stat().st_mtime_ns == mtime


def test_stale_pages_outside_or_at_the_source_folder(tmp_path):
    removed = tmp_path / "out" / "a.html"
    sources = tmp_path / "out" / "_sources"
    sources.mkdir(parents=True)
    removed.write_text("", encoding="utf-8")
    (sources / "a.txt").write_text("", encoding="utf-8")
    (sources / "a.rst.txt").write_text("", encoding="utf-8")
    key = ("html", "out")
    dom = SimpleNamespace(data={"api_pages": {key: {"a", "b"}}})
    # a and b are pages of scmd apidoc, c is hand-written
    write(
        tmp_path / "src", {"a.rst": f"{MARKER}\n", "b.rst": f"{MARKER}\n", "c.rst": ""}
    )

    def run(output_dir, found):
        builder = SimpleNamespace(
            format="html",
            out_suffix=".html",
            name="html",
            outdir=tmp_path / "out",
            get_outfilename=lambda doc: tmp_path / "out" / f"{doc}.html",
        )
        config = SimpleNamespace(
            matlab_apidoc_output_dir=output_dir,
            source_suffix={".rst": "restructuredtext", ".txt": "restructuredtext"},
            html_sourcelink_suffix=".txt",
        )
        app = SimpleNamespace(
            env=SimpleNamespace(
                found_docs=found, doc2path=lambda doc: tmp_path / "src" / f"{doc}.rst"
            ),
            config=config,
            builder=builder,
            srcdir=tmp_path / "src",
        )
        mat_urls.remove_stale_pages(app, dom, key)

    # Not below the source folder: no page is noted.
    run("../out", {"a", "b"})
    assert removed.is_file()
    assert dom.data["api_pages"][key] == set()
    run(".", {"a", "b", "c"})  # the source folder itself: every page of apidoc
    assert dom.data["api_pages"][key] == {"a", "b"}
    run(".", {"b"})
    assert list((tmp_path / "out").iterdir()) == []
    assert dom.data["api_pages"][key] == {"b"}


UNINDEXED_FOLDERS = """\
Index
=====

.. mat:folder:: mex/

.. mat:currentfolder:: tools

.. mat:function:: fastSolve

.. mat:currentfolder:: None

Links: :mat:folder:`mex/` :mat:func:`tools/fastSolve`
"""


@pytest.mark.parametrize("root", ['"."', None])
def test_hand_written_folders_that_are_not_indexed(make_app, tmp_path, root):
    # mat:folder describes a folder without reading it, like mat:function
    # (documenting.rst, "Writing directives by hand"); mat:currentfolder sets
    # the folder of the references after it. With or without an index, they
    # get their anchors, inventory lines and stable addresses, with no warning.
    conf = 'extensions = ["sphinxcontrib.matlab"]\n'
    if root:
        conf += f"matlab_src_code_project_root = {root}\n"
        write(tmp_path, {"f.m": FUNCTION.format(name="f")})
    write(tmp_path, {"conf.py": conf, "index.rst": UNINDEXED_FOLDERS})
    app = make_app(srcdir=tmp_path)
    app.build()
    assert app.warning.getvalue() == ""
    assert {
        name: entry for name, entry in inventory(app.outdir).items() if "/" in name
    } == {
        "mex/": ("mat/ref/mex/index.html", "-"),
        "tools/fastSolve": ("mat/ref/tools/fastSolve.html", "fastSolve"),
    }
    assert follow(app.outdir, "mat/ref/mex/index.html") == "index.html#mat-mex/"
    assert follow(app.outdir, "mat/ref/tools/fastSolve.html") == (
        "index.html#mat-tools/fastSolve"
    )
    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert 'href="#mat-mex/"' in html
    assert 'href="#mat-tools/fastSolve"' in html


def build_removed_pages(make_app, tmp_path, output_dir, remove=(), notes="notes"):
    """Run ``scmd apidoc`` and an HTML build of a project with ``util/alpha.m``,
    ``util/scale.m`` and ``util/zeta.m``, one API page each below ``output_dir``,
    and the hand-written orphan page ``notes``, after removing ``remove``.
    """
    if not (tmp_path / "conf.py").exists():
        write(
            tmp_path,
            {
                "conf.py": 'extensions = ["sphinxcontrib.matlab"]\n'
                'matlab_src_code_project_root = "src"\n'
                f"matlab_apidoc_output_dir = {output_dir!r}\n"
                'matlab_apidoc_group = "folder"\nmatlab_apidoc_page_size = 1\n',
                f"{notes}.rst": ":orphan:\n\nNotes\n=====\n\nHand-written.\n",
                **{
                    f"src/util/{name}.m": FUNCTION.format(name=name)
                    for name in ("alpha", "scale", "zeta")
                },
            },
        )
        if output_dir != ".":
            write(
                tmp_path,
                {"index.rst": "Index\n=====\n\n.. toctree::\n\n   api/index\n"},
            )
    for name in remove:
        (tmp_path / name).unlink()
    assert apidoc(["-q", "-c", str(tmp_path)]) == 0
    app = make_app(srcdir=tmp_path)
    app.build()
    app.cleanup()
    return Path(app.outdir)


@pytest.mark.parametrize(("output_dir", "api"), [("api", "api/"), (".", "")])
def test_pages_of_sources_apidoc_removed_go(make_app, tmp_path, output_dir, api):
    outdir = build_removed_pages(make_app, tmp_path, output_dir)
    gone = [
        f"{api}util/index-3.html",
        f"_sources/{api}util/index-3.rst.txt",
        "mat/ref/util/zeta.m.html",
        "mat/name/zeta.html",
    ]
    stay = [
        "index.html",
        "notes.html",
        "_sources/notes.rst.txt",
        f"{api}util/index.html",
        f"{api}util/index-2.html",
        f"_sources/{api}util/index-2.rst.txt",
        "mat/ref/util/scale.m.html",
        "mat/name/scale.html",
    ]
    assert all((outdir / p).is_file() for p in gone + stay)
    notes = (outdir / "notes.html").read_bytes()
    outdir = build_removed_pages(
        make_app, tmp_path, output_dir, remove=["src/util/zeta.m"]
    )
    assert not any((outdir / p).exists() for p in gone)
    assert all((outdir / p).is_file() for p in stay)
    assert (outdir / "notes.html").read_bytes() == notes
    assert follow(outdir, "mat/ref/util/scale.m.html") == (
        f"{api}util/index-2.html#mat-util/scale.m"
    )


@pytest.mark.parametrize(
    ("output_dir", "notes"), [("api", "api/notes"), (".", "notes")]
)
def test_pages_of_removed_hand_written_sources_stay(
    make_app, tmp_path, output_dir, notes
):
    # Next to the API pages, a hand-written page has no marker line: its
    # pages stay when its source is removed, as Sphinx keeps them.
    outdir = build_removed_pages(make_app, tmp_path, output_dir, notes=notes)
    stay = [f"{notes}.html", f"_sources/{notes}.rst.txt"]
    assert all((outdir / p).is_file() for p in stay)
    outdir = build_removed_pages(
        make_app, tmp_path, output_dir, remove=[f"{notes}.rst"], notes=notes
    )
    assert all((outdir / p).is_file() for p in stay)
