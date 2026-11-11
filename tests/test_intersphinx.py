"""Intersphinx between a library built with scmd apidoc and a
consumer project: MATLAB-name, path and named-inventory references, and what
survives when an object moves to another API page (plan.md Section 2.3). The
library's inventory points to the stable addresses (``mat/ref/``).
"""

import functools
import html
import http.server
import re
import shutil
import threading
import urllib.request
import zlib
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote

import pytest
from sphinx.util.inventory import InventoryFile
from test_apidoc import FUNCTION, write

from sphinxcontrib import mat_urls
from sphinxcontrib.matlab_apidoc import main as apidoc

BASE = "https://docs.example.invalid/team/lib/"
CIRCLE = """\
classdef Circle < handle
    % Circle A circle.
    properties
        Radius = 1 % Radius of the circle.
    end
    methods
        function a = area(obj)
            % area Area of the circle.
            a = pi * obj.Radius^2;
        end
    end
end
"""
LIBRARY = {
    "+geom/Circle.m": CIRCLE,
    "+geom/+io/read.m": FUNCTION.format(name="read"),
    "util/scale.m": FUNCTION.format(name="scale"),
    "util/private/check.m": FUNCTION.format(name="check"),
    "toolbox/helper.m": FUNCTION.format(name="helper"),
    "examples/helper.m": FUNCTION.format(name="helper"),
}


def build_library(
    make_app, root, group="folder", page_size=100, extra=(), conf="", **apidoc_conf
):
    """Generate the API pages of the library ``root`` with
    scmd apidoc (other ``matlab_apidoc_*`` values in
    ``apidoc_conf``, other ``conf.py`` lines in ``conf``) and build its HTML
    from scratch; return the output folder.
    """
    files = {**LIBRARY, **{ref: FUNCTION.format(name=Path(ref).stem) for ref in extra}}
    write(root / "src", files)
    other = "".join(f"matlab_apidoc_{k} = {v!r}\n" for k, v in apidoc_conf.items())
    other += conf
    (root / "conf.py").write_text(
        'project = "Library"\n'
        'extensions = ["sphinxcontrib.matlab"]\n'
        'matlab_src_code_project_root = "src"\n'
        'matlab_apidoc_output_dir = "api"\n'
        f"matlab_apidoc_group = {group!r}\n"
        f"matlab_apidoc_page_size = {page_size}\n{other}"
    )
    (root / "index.rst").write_text(
        "Library\n=======\n\n.. toctree::\n\n   api/index\n"
    )
    assert apidoc(["-q", "-c", str(root)]) == 0
    shutil.rmtree(root / "_build", ignore_errors=True)
    app = make_app(srcdir=root, freshenv=True)
    app.build(force_all=True)
    # Several apps in one test: forget the global state (nodes, roles).
    app.cleanup()
    assert app.warning.getvalue() == ""
    return Path(app.outdir)


def build_consumer(make_app, root, mapping, references, conf=""):
    """Build a consumer that documents its own ``util/scale.m`` and lists
    ``references`` (key -> role; other ``conf.py`` lines in ``conf``); return
    ``(links, warnings)`` where links
    maps each key to the ``(href, text)`` of its link (href None: no link).
    """
    write(root / "src", {"util/scale.m": FUNCTION.format(name="scale")})
    (root / "conf.py").write_text(
        'project = "Consumer"\n'
        'extensions = ["sphinxcontrib.matlab", "sphinx.ext.intersphinx"]\n'
        'matlab_src_code_project_root = "src"\n'
        f"intersphinx_mapping = {mapping!r}\n"
        "nitpicky = True\n" + conf
    )
    items = "".join(f"* {key}: {role}\n" for key, role in references.items())
    (root / "index.rst").write_text(
        f"Consumer\n========\n\n.. mat:autofunction:: util/scale.m\n\n{items}"
    )
    shutil.rmtree(root / "_build", ignore_errors=True)
    app = make_app(srcdir=root, freshenv=True)
    app.build(force_all=True)
    app.cleanup()
    page = (Path(app.outdir) / "index.html").read_text(encoding="utf-8")
    links = {}
    for key, item in re.findall(r"<li><p>(\w+): (.*?)</p>\s*</li>", page, re.DOTALL):
        href = re.search(r'href="([^"]*)"', item)
        text = html.unescape(re.sub(r"<[^>]+>", "", item))
        links[key] = (html.unescape(href[1]) if href else None, text)
    return links, app.warning.getvalue()


def inventory(outdir):
    """``{name: (uri, display name)}`` of the mat entries of ``objects.inv``."""
    with open(outdir / "objects.inv", "rb") as f:
        inv = InventoryFile.load(cast(Any, f), "", lambda _base, uri: uri)
    out = {}
    for objtype, items in inv.items():
        for name, item in items.items():
            if objtype.startswith("mat:"):
                if isinstance(item, tuple):
                    out[name] = item[2], item[3]
                else:
                    out[name] = item.uri, item.display_name
    return out


def anchors(outdir, uri):
    """Return the ids on the page of ``uri`` (relative to ``outdir``); none if
    the page does not exist.
    """
    page = outdir / unquote(uri.partition("#")[0])
    if not page.is_file():
        return set()
    return set(re.findall(r'id="([^"]+)"', page.read_text(encoding="utf-8")))


def target(outdir, stub):
    """Return the address the redirect file ``stub`` sends the browser to."""
    text = (outdir / unquote(str(stub))).read_text(encoding="utf-8")
    assert mat_urls.MARKER in text
    match = re.search(r'url=([^"]*)"', text)
    assert match
    return match[1]


def resolve(stub, url):
    """``url``, relative to the redirect file ``stub``, from the output root."""
    parts = Path(stub).parent.parts
    while url.startswith("../"):
        url, parts = url[3:], parts[:-1]
    return "/".join([*parts, url])


def follow(outdir, stub):
    """Return the page and anchor the redirect file ``stub`` opens."""
    return resolve(stub, target(outdir, stub))


def write_inventory(path, project, entries):
    """Write an ``objects.inv`` with ``(name, objtype, uri, display)``
    entries of the mat domain.
    """
    header = (
        "# Sphinx inventory version 2\n"
        f"# Project: {project}\n# Version: 1.0\n"
        "# The remainder of this file is compressed using zlib.\n"
    )
    body = "".join(f"{n} mat:{t} 1 {u} {d}\n" for n, t, u, d in entries)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header.encode() + zlib.compress(body.encode()))


# --- consumer references ----------------------------------------------------

REFERENCES = {
    "path": ":mat:func:`util/scale.m`",
    "external": ":external:mat:func:`util/scale.m`",
    "named": ":external+lib:mat:func:`util/scale.m`",
    "prefixed": ":mat:func:`lib:util/scale.m`",
    "caption": ":mat:func:`Scale it <lib:util/scale.m>`",
    "class": ":mat:class:`+geom/Circle.m`",
    "method": ":mat:meth:`+geom/Circle.m.area`",
    "property": ":mat:attr:`+geom/Circle.m.Radius`",
    "folder": ":mat:folder:`+geom/`",
    "private": ":mat:func:`util/private/check.m`",
    "short": ":mat:func:`~+geom/+io/read.m`",
    "name_class": ":mat:class:`geom.Circle`",
    "name_function": ":mat:func:`geom.io.read`",
    "name_method": ":mat:meth:`geom.Circle.area`",
    "name_namespace": ":mat:folder:`geom`",
    "name_any": ":any:`geom.Circle`",
    "name_named": ":external+lib:mat:func:`scale`",
    "name_prefixed": ":mat:func:`lib:scale`",
    "name_caption": ":mat:class:`A circle <geom.Circle>`",
    "name_local": ":mat:func:`scale`",
    "name_private": ":mat:func:`check`",
    "name_ambiguous": ":mat:func:`helper`",
    "path_disambiguates": ":mat:func:`toolbox/helper.m`",
    "wrong_role": ":mat:func:`+geom/Circle.m`",
}
EXPECTED = {
    "path": ("#mat-util/scale.m", "util/scale.m()"),
    "external": (f"{BASE}mat/ref/util/scale.m.html", "scale"),
    "named": (f"{BASE}mat/ref/util/scale.m.html", "scale"),
    "prefixed": (f"{BASE}mat/ref/util/scale.m.html", "scale"),
    "caption": (f"{BASE}mat/ref/util/scale.m.html", "Scale it"),
    "class": (f"{BASE}mat/ref/%2Bgeom/Circle.m.html", "geom.Circle"),
    "method": (f"{BASE}mat/ref/%2Bgeom/Circle.m.area.html", "geom.Circle.area"),
    "property": (
        f"{BASE}mat/ref/%2Bgeom/Circle.m.Radius.html",
        "geom.Circle.Radius",
    ),
    "folder": (f"{BASE}mat/ref/%2Bgeom/index.html", "geom"),
    "private": (f"{BASE}mat/ref/util/private/check.m.html", "check"),
    "short": (f"{BASE}mat/ref/%2Bgeom/%2Bio/read.m.html", "geom.io.read"),
    "name_class": (f"{BASE}mat/ref/%2Bgeom/Circle.m.html", "geom.Circle"),
    "name_function": (f"{BASE}mat/ref/%2Bgeom/%2Bio/read.m.html", "geom.io.read"),
    "name_method": (
        f"{BASE}mat/ref/%2Bgeom/Circle.m.area.html",
        "geom.Circle.area",
    ),
    "name_namespace": (f"{BASE}mat/ref/%2Bgeom/index.html", "geom"),
    "name_any": (f"{BASE}mat/ref/%2Bgeom/Circle.m.html", "geom.Circle"),
    "name_named": (f"{BASE}mat/ref/util/scale.m.html", "scale"),
    "name_prefixed": (f"{BASE}mat/ref/util/scale.m.html", "scale"),
    "name_caption": (f"{BASE}mat/ref/%2Bgeom/Circle.m.html", "A circle"),
    # The consumer's own object wins over the library's.
    "name_local": ("#mat-util/scale.m", "scale()"),
    "name_private": (None, "check()"),
    "name_ambiguous": (None, "helper()"),
    "path_disambiguates": (f"{BASE}mat/ref/toolbox/helper.m.html", "helper"),
    # Intersphinx matches only the role's types.
    "wrong_role": (None, "+geom/Circle.m()"),
}


def test_consumer_links_to_the_library(make_app, tmp_path):
    outdir = build_library(make_app, tmp_path / "lib", private=True)
    mapping = {"lib": (BASE, str(outdir / "objects.inv"))}
    links, warnings = build_consumer(make_app, tmp_path / "app", mapping, REFERENCES)
    assert links == EXPECTED
    assert (
        "'helper' matches several objects: examples/helper.m, toolbox/helper.m; "
        "use a path reference [mat.ambiguous]" in warnings
    )
    # An ambiguous name gets no second "not found" warning.
    assert "target not found: helper" not in warnings
    assert "mat:func reference target not found: check" in warnings
    assert "mat:func reference target not found: +geom/Circle.m" in warnings
    assert warnings.count("WARNING") == 3
    # Every remote link opens a page of the library that has its anchor.
    for href, _ in links.values():
        if href and href.startswith(BASE):
            url = follow(outdir, href.removeprefix(BASE))
            assert url.partition("#")[2] in anchors(outdir, url)


def test_consumer_links_to_a_block_with_a_line_break(make_app, tmp_path):
    # The library's objects.inv names the block as a role writes its target
    # (spaces for the line break); the consumer resolves it to its stable page.
    from test_names_properties import _build

    outdir, _, _, _ = _build(make_app, tmp_path / "lib", ["Two\\nLines", "Plain"])
    mapping = {"lib": (BASE, str(outdir / "objects.inv"))}
    role = ":mat:simulink_library_block:`odd.mdl/Two Lines`"
    links, warnings = build_consumer(
        make_app, tmp_path / "app", mapping, {"block": role}
    )
    assert warnings == ""
    href, text = links["block"]
    assert href == f"{BASE}mat/ref/odd.mdl~2FTwo~0ALines.html"
    assert (outdir / unquote(href.removeprefix(BASE))).is_file()
    assert text == "odd/Two Lines"


def test_names_in_several_inventories(make_app, tmp_path):
    entries = {
        "one": [
            ("a/f.m", "function", "api.html#mat-a/f.m", "f"),
            ("a/g.m", "function", "api.html#mat-a/g.m", "g"),
            ("c/h.m", "function", "api.html#mat-c/h.m", "h"),
        ],
        "two": [
            ("b/f.m", "function", "api.html#mat-b/f.m", "f"),
            ("c/h.m", "function", "api.html#mat-c/h.m", "h"),
        ],
    }
    mapping = {}
    for name, items in entries.items():
        write_inventory(tmp_path / name / "objects.inv", name, items)
        uri = f"https://{name}.example.invalid/"
        mapping[name] = (uri, str(tmp_path / name / "objects.inv"))
    references = {
        "any": ":mat:func:`f`",
        "one": ":mat:func:`one:f`",
        "two": ":external+two:mat:func:`f`",
        "unique": ":mat:func:`g`",
        "missing": ":mat:func:`two:g`",
        # The same reference (and so name) in both: name the inventory.
        "same_path": ":mat:func:`c/h.m`",
        "same_name": ":mat:func:`h`",
        "same_path_named": ":mat:func:`two:c/h.m`",
        "same_name_named": ":external+one:mat:func:`h`",
    }
    links, warnings = build_consumer(make_app, tmp_path / "app", mapping, references)
    assert links == {
        "any": (None, "f()"),
        "one": ("https://one.example.invalid/api.html#mat-a/f.m", "f"),
        "two": ("https://two.example.invalid/api.html#mat-b/f.m", "f"),
        "unique": ("https://one.example.invalid/api.html#mat-a/g.m", "g"),
        "missing": (None, "two:g()"),
        "same_path": (None, "c/h.m()"),
        "same_name": (None, "h()"),
        "same_path_named": ("https://two.example.invalid/api.html#mat-c/h.m", "h"),
        "same_name_named": ("https://one.example.invalid/api.html#mat-c/h.m", "h"),
    }
    assert "'f' matches several objects: one:a/f.m, two:b/f.m; write one" in warnings
    assert "target not found: two:g" in warnings
    assert (
        "'c/h.m' matches several objects: one:c/h.m, two:c/h.m; write one of them"
        in warnings
    )
    assert "'h' matches several objects: one:c/h.m, two:c/h.m; write one" in warnings
    assert warnings.count("WARNING") == 4


# --- repaging (plan.md open items L1/L2) -------------------------------------

# (group, page size, page before, page after) of util/scale.m when
# util/alpha.m is added: it sorts first, so scale.m moves to the next page.
REPAGING = [
    ("namespace", 2, "api/global.html", "api/global-2.html"),
    ("folder", 1, "api/util/index.html", "api/util/index-2.html"),
]


@pytest.mark.parametrize(("group", "size", "before", "after"), REPAGING)
def test_links_follow_a_moved_object(make_app, tmp_path, group, size, before, after):
    ref = "util/scale.m"
    anchor = "mat-util/scale.m"
    stable = "mat/ref/util/scale.m.html"
    references = {
        "name": ":mat:class:`geom.Circle`",
        "path": f":mat:func:`lib:{ref}`",
    }
    lib = tmp_path / "lib"
    outdir = build_library(make_app, lib, group, size)
    inv_v1 = inventory(outdir)
    assert inv_v1[ref] == (stable, "scale")
    assert follow(outdir, stable) == f"{before}#{anchor}"
    shutil.copy(outdir / "objects.inv", tmp_path / "objects-v1.inv")
    pages_v1 = {p.relative_to(outdir).as_posix() for p in outdir.rglob("*.html")}
    mapping = {"lib": (BASE, str(outdir / "objects.inv"))}
    links, _ = build_consumer(make_app, tmp_path / "app", mapping, references)
    assert links["path"] == (f"{BASE}{stable}", "scale")

    outdir = build_library(make_app, lib, group, size, extra=["util/alpha.m"])
    inv_v2 = inventory(outdir)
    # Same inventory entry; the stable address opens another page.
    assert inv_v2[ref] == (stable, "scale")
    assert set(inv_v2) - set(inv_v1) == {"util/alpha.m"}
    assert follow(outdir, stable) == f"{after}#{anchor}"
    assert anchor in anchors(outdir, after)

    # Refreshed inventory: the same links.
    links, warnings = build_consumer(make_app, tmp_path / "app", mapping, references)
    assert links["path"] == (f"{BASE}{stable}", "scale")
    assert links["name"] == (f"{BASE}mat/ref/%2Bgeom/Circle.m.html", "geom.Circle")
    assert "WARNING" not in warnings

    # The page URL copied before the move still opens a page, without the
    # object.
    assert before in pages_v1
    assert (outdir / before).is_file()
    assert anchor not in anchors(outdir, before)

    # A stale inventory gives the same links, which open the moved object.
    stale = {"lib": (BASE, str(tmp_path / "objects-v1.inv"))}
    links, warnings = build_consumer(make_app, tmp_path / "app", stale, references)
    assert links["path"] == (f"{BASE}{stable}", "scale")
    assert "WARNING" not in warnings


@pytest.mark.parametrize(
    ("group", "split"), [("namespace", "global-4"), ("folder", "util/index-2")]
)
def test_separate_pages_keep_their_url_when_listings_split(
    make_app, tmp_path, group, split
):
    # With one page per file, the page of a file is named by its path; only
    # the listing pages split.
    url = "api/util/scale.m.html#mat-util/scale.m"
    stable = "mat/ref/util/scale.m.html"
    lib = tmp_path / "lib"
    outdir = build_library(make_app, lib, group, 1, separate=True)
    assert inventory(outdir)["util/scale.m"] == (stable, "scale")
    assert follow(outdir, stable) == url
    pages_v1 = {p.relative_to(outdir).as_posix() for p in outdir.rglob("*.html")}
    outdir = build_library(make_app, lib, group, 1, ["util/alpha.m"], separate=True)
    assert follow(outdir, stable) == url
    assert "mat-util/scale.m" in anchors(outdir, url)
    pages_v2 = {p.relative_to(outdir).as_posix() for p in outdir.rglob("*.html")}
    new = {p for p in pages_v2 - pages_v1 if not p.startswith("mat/")}
    assert new == {"api/util/alpha.m.html", f"api/{split}.html"}


# --- a deployed site under a URL prefix ----------------------------------------


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


@pytest.fixture
def site(tmp_path):
    """Serve ``tmp_path / "site"`` over HTTP; yield the folder and base URL."""
    root = tmp_path / "site"
    root.mkdir()
    handler = functools.partial(QuietHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield root, f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def test_inventory_from_a_deployed_site(make_app, tmp_path, site):
    root, server = site
    outdir = build_library(make_app, tmp_path / "lib", "namespace")
    shutil.copytree(outdir, root / "team" / "lib")
    base = f"{server}/team/lib/"
    references = {
        "name": ":mat:class:`geom.Circle`",
        "path": ":mat:func:`lib:util/scale.m`",
    }
    links, warnings = build_consumer(
        make_app, tmp_path / "app", {"lib": (base, None)}, references
    )
    assert "WARNING" not in warnings
    for key, page in (("name", "geom"), ("path", "global")):
        href = links[key][0]
        assert href.startswith(f"{base}mat/ref/")
        # The redirect file names the page; the server serves both.
        with urllib.request.urlopen(href) as response:
            redirect = response.read().decode("utf-8")
        match = re.search(r'url=\.\./(?:\.\./)*api/([^"#]*)#([^"]*)"', redirect)
        assert match
        assert match[1] == f"{page}.html"
        with urllib.request.urlopen(f"{base}api/{match[1]}") as response:
            assert f'id="{unquote(match[2])}"' in response.read().decode("utf-8")
