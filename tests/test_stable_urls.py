"""Stable addresses of documented objects (mat_urls): redirect files that
follow an object to whichever page it is on, the "¶" links to them and the
inventory entries that point to them.
"""

import re
from pathlib import Path

from test_intersphinx import anchors, build_library, inventory, resolve, target

from sphinxcontrib import mat_urls


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
    outdir = build_library(make_app, tmp_path / "lib")
    chooser = (outdir / "mat/name/helper.html").read_text(encoding="utf-8")
    assert "url=" not in chooser
    assert re.findall(r'<li><a href="([^"]*)">([^<]*)</a> \((\w+)\)', chooser) == [
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


def test_turned_off(make_app, tmp_path):
    outdir = build_library(
        make_app, tmp_path / "lib", conf="matlab_stable_urls = False\n"
    )
    assert not (outdir / "mat").exists()
    page = (outdir / "api/util/index.html").read_text(encoding="utf-8")
    assert 'class="headerlink" href="#mat-util/scale.m"' in page
    # The inventory keeps the page addresses.
    assert inventory(outdir)["util/scale.m"] == (
        "api/util/index.html#mat-util/scale.m",
        "scale",
    )


def test_no_inventory(tmp_path):
    # A builder of the HTML format that writes no objects.inv.
    mat_urls.rewrite_inventory(str(tmp_path / "objects.inv"), {"a.m": "x.html"})
    assert not (tmp_path / "objects.inv").exists()


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
