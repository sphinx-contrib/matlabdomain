"""sphinxcontrib.mat_urls
~~~~~~~~~~~~~~~~~~~~~~

Stable addresses of documented objects in HTML builds (plan.md Section 2.3).

API pages split into ``global.html``, ``global-2.html``, ... by
``matlab_apidoc_page_size``, so the page an object is on can change. Each
build writes small redirect files whose addresses do not depend on the pages:

- ``mat/ref/<path reference>.html`` for every object (folders:
  ``mat/ref/<folder>/index.html``);
- ``mat/name/<MATLAB name>.html`` for every MATLAB name of a non-private
  object: a redirect if one object has it, else a page in the site's theme
  that lists them all.

The "¶" link of an object points to its stable address: by MATLAB name if
it is unique, else by path reference; the ``mat`` entries of ``objects.inv``
point to the address by path reference, so another project's links follow an
object even with an old inventory. File names are escaped like the pages
of ``scmd apidoc``. Only files this extension wrote (``MARKER``,
``JS_MARKER``) are rewritten or removed; any other file at one of these
addresses fails the build.

A page opened at the anchor of an object that is no longer on it (an
address copied from the browser), and the site's ``404.html``, send the
browser to the object's stable address (``SCRIPT``, ``mat/refs.js``).

Incremental builds (``pages_to_write``): pages whose ``scmd apidoc`` source
is gone are removed; when objects moved, every page that links to a MATLAB
object is written again; and an output that another builder on the same
doctree folder got out of step with writes every page once.

Chooser pages are rendered only when they may differ from the files on disk
(``chooser_pages``): when the build writes a document page (the navigation or
the theme may have changed), when the chooser data differs from ``STATE``
(written at the end of the build that rendered them), or when a chooser file
is missing. ``STATE`` is removed before any page or chooser page is written,
so a build that fails leaves none and the next build renders them all.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import zlib
from pathlib import Path
from urllib.parse import quote, urlsplit

import sphinx
from docutils import nodes
from sphinx.errors import ExtensionError
from sphinx.util.logging import getLogger
from sphinx.util.osutil import relative_uri

from . import mat_naming
from .matlab_apidoc._names import docnames

logger = getLogger("matlab-domain")

ROOT = "mat"
MARKER = "<!-- sphinxcontrib-matlabdomain stable address -->"
JS_MARKER = "/* sphinxcontrib-matlabdomain stable address */"
SCRIPT = "mat_urls.js"
REFS = f"{ROOT}/refs.js"
# The chooser data the chooser pages on disk were rendered from.
STATE = f"{ROOT}/choosers.json"
_FRAGMENT_SAFE = "/+-._~:@!$()*,="
_PERMALINK = re.compile(r'(<a class="headerlink" href=")#(mat-[^"]*)(")')
# An objects.inv line: name, domain:type, priority, URI, display name.
_INVENTORY_LINE = re.compile(r"(.+?) (mat:\w+) (-?\d+) \S+ (.*)")
_CHOOSER_LINE = re.compile(rf"\S+ mat:\w+ -1 {ROOT}/name/\S+ -")
_HOME = "sphinxcontrib-matlabdomain-home"
# Finds the site root (the page's, else each folder above it) by loading
# mat/refs.js there; then opens the stable address of the anchor's object and
# points the 404 page's start link to the root.
_JS = """\
/* sphinxcontrib-matlabdomain: open an object that moved to another page. */
(function () {
  "use strict";
  var anchor = "";
  try { anchor = decodeURIComponent(location.hash.slice(1)); } catch (e) {}
  var key = anchor.slice(0, 4) === "mat-" ? anchor.slice(4) : "";
  function roots() {
    var out = [];
    var root = document.documentElement.getAttribute("data-content_root");
    if (root) { out.push(new URL(root, location.href).href); }
    var depth = location.pathname.split("/").length - 1;
    for (var up = "./"; depth-- > 0; up += "../") {
      var url = new URL(up, location.href).href;
      if (out.indexOf(url) < 0) { out.push(url); }
    }
    return out;
  }
  var guard = "sphinxcontrib-matlabdomain:" + anchor;
  function moved(root, refs) {
    if (!key || !Object.prototype.hasOwnProperty.call(refs, key)) { return; }
    try {
      var last = Number(sessionStorage.getItem(guard));
      if (Date.now() - last < 10000) { sessionStorage.removeItem(guard); return; }
      sessionStorage.setItem(guard, String(Date.now()));
    } catch (e) {}
    location.replace(root + "mat/ref/" + (refs[key] || key) + ".html");
  }
  function find(list) {
    if (!list.length) { return; }
    window.matStableRefs = undefined;
    var script = document.createElement("script");
    script.src = list[0] + "mat/refs.js";
    script.charset = "utf-8";
    script.onload = function () {
      var refs = window.matStableRefs;
      if (!refs) { find(list.slice(1)); return; }
      var home = document.getElementById("@HOME@");
      if (home) { home.href = list[0] + home.getAttribute("data-page"); }
      moved(list[0], refs);
    };
    script.onerror = function () { find(list.slice(1)); };
    document.head.appendChild(script);
  }
  function run() {
    var home = document.getElementById("@HOME@");
    var here = key && document.getElementById(anchor);
    if (here) { try { sessionStorage.removeItem(guard); } catch (e) {} }
    if (home || (key && !here)) { find(roots()); }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
""".replace("@HOME@", _HOME)


def _html(app):
    return _html_builder(app.builder)


def _html_builder(builder):
    """Stable addresses are for builders that write ``<page>.html`` pages: not
    epub, and not ``json`` or ``pickle`` (``.fjson``, ``.fpickle``).
    """
    return (
        getattr(builder, "format", "") == "html"
        and getattr(builder, "out_suffix", None) == ".html"
        and not builder.name.startswith("epub")
    )


def enabled(app):
    return app.config.matlab_stable_urls and _html(app)


def _names(dom):
    """MATLAB name -> references of the non-private objects that have it.

    A Simulink block's display name is a Simulink path, not a MATLAB name.
    """
    out = {}
    for ref, (_, _, display) in dom.data["objects"].items():
        if (
            display != ref
            and "/" not in display
            and not mat_naming.is_private_reference(ref)
        ):
            out.setdefault(display, []).append(ref)
    return {name: sorted(refs) for name, refs in out.items()}


def addresses(dom):
    """``(by_ref, by_name, names, anchors)``: the stable file of every
    reference and MATLAB name (``/``-separated, below the output folder), the
    references of each MATLAB name, and the reference of each anchor.
    """
    if dom._stable_urls is None:
        refs = list(dom.data["objects"])
        ref_files, _ = docnames(refs, "html")
        names = _names(dom)
        name_files, _ = docnames(list(names), "html")
        dom._stable_urls = (
            {r: f"{ROOT}/ref/{f}.html" for r, f in ref_files.items()},
            {n: f"{ROOT}/name/{f}.html" for n, f in name_files.items()},
            names,
            {mat_naming.make_target_id(r): r for r in refs},
        )
    return dom._stable_urls


def permalink(dom, ref):
    """Return the stable file a "¶" link of ``ref`` points to."""
    by_ref, by_name, names, _ = addresses(dom)
    display = dom.data["objects"][ref][2]
    if names.get(display) == [ref]:
        return by_name[display]
    return by_ref[ref]


def chooser_link(dom, builder, fromdocname, refs, contnode):
    """Link ``contnode`` to the chooser page that lists all of ``refs`` (one
    MATLAB name), or return it unlinked when the build writes no such page.
    """
    if not (builder.config.matlab_stable_urls and _html_builder(builder)):
        return contnode
    _, by_name, names, _ = addresses(dom)
    name = dom.data["objects"][refs[0]][2]
    listed = names.get(name, [])
    if len(listed) < 2 or not set(refs) <= set(listed):
        return contnode
    uri = relative_uri(builder.get_target_uri(fromdocname), by_name[name])
    node = nodes.reference("", "", internal=True, refuri=uri, reftitle=name)
    node += contnode
    return node


def is_chooser_uri(uri):
    """Return True for the address of a chooser page of another site."""
    return f"/{ROOT}/name/" in "/" + urlsplit(uri).path


def rewrite_permalinks(app, pagename, templatename, context, doctree):  # noqa: ARG001
    """``html-page-context``: point the "¶" links of objects to their stable
    addresses. A document's page (one with a doctree; generated pages have
    none) also means that this build renders the chooser pages again.
    """
    if doctree is not None and not getattr(app.builder, "mat_wrote_page", False):
        # Main process: with -j, Sphinx writes the first page itself.
        app.builder.mat_wrote_page = True
        _remove_state(app.builder)
    body = context.get("body")
    if not body or not enabled(app):
        return
    dom = app.env.get_domain("mat")
    anchors = addresses(dom)[3]
    page = app.builder.get_target_uri(pagename)

    def replace(match):
        ref = anchors.get(match[2])
        if ref is None:
            return match[0]
        url = quote(relative_uri(page, permalink(dom, ref)))
        return f"{match[1]}{html.escape(url)}{match[3]}"

    context["body"] = _PERMALINK.sub(replace, body)


def _target(builder, dom, stub, ref):
    docname = dom.data["objects"][ref][0]
    fragment = quote(mat_naming.make_target_id(ref), safe=_FRAGMENT_SAFE)
    return f"{relative_uri(stub, builder.get_target_uri(docname))}#{fragment}"


def _redirect(title, target):
    url = html.escape(target)
    script = json.dumps(target).replace("</", "<\\/")
    return (
        f'<!DOCTYPE html>\n{MARKER}\n<html><head><meta charset="utf-8">\n'
        f"<title>{html.escape(title)}</title>\n"
        f'<meta http-equiv="refresh" content="0; url={url}">\n'
        f"<script>location.replace({script})</script>\n"
        f'</head><body><p><a href="{url}">{html.escape(title)}</a></p></body></html>\n'
    )


def _chooser_body(name, entries):
    """Return the list of the objects named ``name`` (``entries``: ref,
    objtype, target).
    """
    items = "".join(
        f'<li><p><a class="reference internal" href="{html.escape(target)}">'
        '<code class="xref mat docutils literal notranslate">'
        f'<span class="pre">{html.escape(ref)}</span></code></a> ({objtype})</p></li>\n'
        for ref, objtype, target in entries
    )
    title = html.escape(name)
    return (
        f'{MARKER}\n<section id="objects">\n<h1>{title}</h1>\n'
        '<p>Several objects are named <code class="docutils literal notranslate">'
        f'<span class="pre">{title}</span></code>:</p>\n'
        f'<ul class="simple">\n{items}</ul>\n</section>\n'
    )


def _chooser(name, entries):
    return (
        f'<!DOCTYPE html>\n{MARKER}\n<html><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(name)}</title>\n"
        "<style>body{font-family:system-ui,sans-serif;max-width:50rem;"
        "margin:2rem auto;padding:0 1rem;line-height:1.5}"
        "code{font-size:.95em}li{margin:.25rem 0}li p{margin:0}</style>\n"
        f"</head><body>\n{_chooser_body(name, entries)}</body></html>\n"
    )


def _entries(builder, dom, stub, refs):
    objects = dom.data["objects"]
    return [(ref, objects[ref][1], _target(builder, dom, stub, ref)) for ref in refs]


def _themed(app):
    """Return True when this build writes the chooser pages in the site's
    theme: builders that write ``<page>.html`` for page ``<page>``.
    """
    builder = app.builder
    probe = f"{ROOT}/name/x"
    return bool(
        enabled(app)
        and builder.get_target_uri(probe) == f"{probe}.html"
        and os.path.normcase(builder.get_outfilename(probe))
        == os.path.normcase(os.path.join(builder.outdir, ROOT, "name", "x.html"))
    )


def _choosers(app):
    """Return ``(choosers, state)``: ``(name, stub, entries)`` of each chooser
    page and the text of ``STATE`` for them. The state holds nothing that
    differs between an incremental and a clean build.
    """
    builder = app.builder
    dom = app.env.get_domain("mat")
    _, by_name, names, _ = addresses(dom)
    choosers = [
        (name, stub, _entries(builder, dom, stub, names[name]))
        for name, stub in sorted(by_name.items())
        if len(names[name]) > 1
    ]
    data = json.dumps(choosers, ensure_ascii=False, separators=(",", ":"))
    from .matlab import _get_version

    state = {
        "marker": MARKER,
        "builder": builder.name,
        "matlabdomain": _get_version(),
        "sphinx": sphinx.__display_version__,
        "pages": len(choosers),
        "sha256": hashlib.sha256(data.encode("utf-8")).hexdigest(),
    }
    return choosers, json.dumps(state, indent=1, sort_keys=True) + "\n"


def _cached(builder, choosers, state):
    """Return True when ``STATE`` is ``state`` and every chooser file exists."""
    outdir = str(builder.outdir)
    try:
        with open(os.path.join(outdir, *STATE.split("/")), "rb") as f:
            if f.read() != state.encode("utf-8"):
                return False
    except OSError:
        return False
    return all(
        os.path.isfile(os.path.join(outdir, *stub.split("/")))
        for _, stub, _ in choosers
    )


def _remove_state(builder):
    path = os.path.join(str(builder.outdir), *STATE.split("/"))
    if os.path.isfile(path) and _is_ours(path):
        os.remove(path)


def chooser_pages(app):
    """``html-collect-pages``: the pages that list the objects of a MATLAB
    name several objects have, in the site's theme. Only builders that write
    ``<page>.html`` for page ``<page>``; ``write_redirects`` writes the others.

    None when this build wrote no document page and the pages on disk are
    those of the same chooser data (``_cached``).
    """
    builder = app.builder
    builder.mat_chooser_pages = set()
    builder.mat_chooser_state = None
    if not _themed(app):
        return []
    choosers, state = _choosers(app)
    builder.mat_chooser_pages = {stub for _, stub, _ in choosers}
    builder.mat_chooser_state = state
    if not getattr(builder, "mat_wrote_page", True) and _cached(
        builder, choosers, state
    ):
        return []
    _remove_state(builder)
    pages = []
    for name, stub, entries in choosers:
        _check_owned(os.path.join(str(builder.outdir), *stub.split("/")))
        body = _chooser_body(name, entries)
        pages.append(
            (stub.removesuffix(".html"), {"title": name, "body": body}, "page.html")
        )
    return pages


def _kept_choosers(app):
    """Return the themed chooser stubs and ``STATE`` of a build that did not
    collect pages (Sphinx < 8.2 skips that when it writes nothing): those on
    disk if they are current, else none (``write_redirects`` writes plain
    ones).
    """
    if _themed(app):
        choosers, state = _choosers(app)
        if _cached(app.builder, choosers, state):
            return {stub for _, stub, _ in choosers}, state
    return set(), None


def rewrite_inventory(path, uris, choosers=()):
    """Point the ``mat`` entries of the ``objects.inv`` at ``path`` whose
    name is in ``uris`` (inventory name -> URI) to that URI, and add the
    ``choosers`` entries ``(MATLAB name, objtype, URI)``.
    """
    if not os.path.isfile(path):
        return
    with open(path, "rb") as f:
        data = f.read()
    *header, body = data.split(b"\n", 4)
    lines = zlib.decompress(body).decode("utf-8").split("\n")
    for i, line in enumerate(lines):
        match = _INVENTORY_LINE.fullmatch(line)
        if match and match[1] in uris:
            lines[i] = f"{match[1]} {match[2]} {match[3]} {uris[match[1]]} {match[4]}"
    # Priority -1: not offered by search; keyed by the name, which no path
    # reference equals. Entries of an earlier rewrite are replaced.
    lines = [line for line in lines if line and not _CHOOSER_LINE.fullmatch(line)]
    lines += [f"{name} mat:{objtype} -1 {uri} -" for name, objtype, uri in choosers]
    lines.append("")
    body = zlib.compress("\n".join(lines).encode("utf-8"), 9)
    _write(path, b"\n".join([*header, body]))


def _write(path, data):
    try:
        with open(path, "rb") as f:
            if f.read() == data:
                return
    except OSError:
        pass
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def _is_ours(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:  # pragma: no cover - defensive: unreadable file in mat/
        return False
    if MARKER in text or text.startswith(JS_MARKER):
        return True
    # Written without JS_MARKER by earlier versions.
    folder, name = os.path.split(os.path.normpath(path))
    if name == SCRIPT:
        return text.startswith(_JS.partition("\n")[0])
    if name == os.path.basename(STATE) and os.path.basename(folder) == ROOT:
        # A state cut short (empty, not JSON) is this extension's too.
        try:
            json.loads(text)
        except ValueError:
            return True
        return False
    return (
        name == os.path.basename(REFS)
        and os.path.basename(folder) == ROOT
        and text.startswith("window.matStableRefs = ")
    )


def _check_owned(path):
    if os.path.islink(path) or (os.path.isfile(path) and not _is_ours(path)):
        raise ExtensionError(
            f"stable URL output would overwrite an unowned file: {path}"
        )


def write_redirects(app, exception):
    """``build-finished``: write the stable address files, remove those of
    objects that are gone and point ``objects.inv`` to them.
    """
    if exception is not None or not enabled(app):
        return
    builder = app.builder
    dom = app.env.get_domain("mat")
    by_ref, by_name, names, _ = addresses(dom)
    objects = dom.data["objects"]
    themed = getattr(builder, "mat_chooser_pages", None)
    state = getattr(builder, "mat_chooser_state", None)
    if themed is None:
        themed, state = _kept_choosers(app)
    files = {}
    for ref, stub in by_ref.items():
        files[stub] = _redirect(objects[ref][2], _target(builder, dom, stub, ref))
    for name, stub in by_name.items():
        refs = names[name]
        if len(refs) == 1:
            files[stub] = _redirect(name, _target(builder, dom, stub, refs[0]))
        elif stub not in themed:
            files[stub] = _chooser(name, _entries(builder, dom, stub, refs))
    refs_map = {}
    for ref, stub in by_ref.items():
        key = mat_naming.make_target_id(ref)[4:]
        value = stub[len(ROOT) + 5 : -5]  # mat/ref/<value>.html
        refs_map[key] = "" if value == key else value
    files[REFS] = (
        f"{JS_MARKER}\nwindow.matStableRefs = {json.dumps(refs_map, sort_keys=True)};\n"
    )
    if state is not None:
        files[STATE] = state
    outdir = str(builder.outdir)
    not_found = os.path.join(outdir, "404.html")
    if not os.path.exists(not_found) or _is_ours(not_found):
        files["404.html"] = _not_found(builder.get_target_uri(app.config.root_doc))
    for stub in files:
        _check_owned(os.path.join(outdir, *stub.split("/")))
    failed = set()
    for stub, text in files.items():
        path = os.path.join(outdir, *stub.split("/"))
        try:
            _write(path, text.encode("utf-8"))
        except OSError as err:
            failed.add(stub)
            logger.warning(
                "[sphinxcontrib-matlabdomain] cannot write %s: %s",
                path,
                err,
                type="mat",
                subtype="stable_url",
            )
    root = os.path.join(outdir, ROOT)
    wanted = {
        os.path.normcase(os.path.join(outdir, *s.split("/"))) for s in [*files, *themed]
    }
    for folder, _, names_in in os.walk(root, topdown=False):
        for file in names_in:
            path = os.path.join(folder, file)
            if os.path.normcase(path) not in wanted and _is_ours(path):
                os.remove(path)
        if folder != root and not os.listdir(folder):
            os.rmdir(folder)
    uris = {}
    for ref, stub in by_ref.items():
        name = dom.inventory_name(ref)
        if name is not None and stub not in failed:
            uris[name] = quote(stub)
    choosers = [
        (name, objtype, quote(by_name[name]))
        for name, refs in sorted(names.items())
        if len(refs) > 1 and by_name[name] not in failed
        for objtype in sorted({objects[ref][1] for ref in refs})
    ]
    rewrite_inventory(os.path.join(outdir, "objects.inv"), uris, choosers)


def _not_found(home):
    return (
        f'<!DOCTYPE html>\n{MARKER}\n<html><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Page not found</title>\n"
        "<style>body{font-family:system-ui,sans-serif;max-width:50rem;"
        "margin:2rem auto;padding:0 1rem;line-height:1.5}</style>\n"
        f"<script>\n{_JS}</script>\n</head><body>\n<h1>Page not found</h1>\n"
        f'<p>This page does not exist. <a id="{_HOME}" '
        f'data-page="{html.escape(home)}" href="/">Start page</a></p>\n'
        "</body></html>\n"
    )


def add_script(app):
    """``builder-inited``: load ``SCRIPT`` on every page. Written now, before
    any page, so that a clean build's pages get its checksum (``?v=``) as an
    incremental build's do.
    """
    if enabled(app):
        app.add_js_file(SCRIPT)
        outdir = str(app.builder.outdir)
        # Fail before any page is written; the other stubs are checked later.
        for stub in (REFS, STATE):
            _check_owned(os.path.join(outdir, *stub.split("/")))
        path = os.path.join(outdir, "_static", SCRIPT)
        _check_owned(path)
        try:
            _write(path, f"{JS_MARKER}\n{_JS}".encode())
        except OSError as err:
            logger.warning(
                "[sphinxcontrib-matlabdomain] cannot write %s: %s",
                path,
                err,
                type="mat",
                subtype="stable_url",
            )


def builder_key(builder):
    """Return the output a build writes: its builder and output folder.
    ``html`` and ``dirhtml``, or two output folders, are different outputs.
    """
    return (builder.name, os.path.normcase(os.path.abspath(str(builder.outdir))))


def note_pages(app, env, added, changed, removed):  # noqa: ARG001
    """``env-get-outdated``: remember where each object was, and the removed
    documents, before this build reads anything.
    """
    dom = env.get_domain("mat")
    dom.objects_before = dict(dom.data["objects"])
    dom.removed_docs = set(removed)
    builder = app.builder
    builder.mat_wrote_page = False  # rewrite_permalinks
    builder.mat_chooser_pages = builder.mat_chooser_state = None  # chooser_pages
    return []


def pages_to_write(app, env):
    """``env-get-updated``: the pages this build writes besides those Sphinx
    writes anyway (the pages it read and those whose source is newer).

    Builders can share one doctree folder (``-d``) and so one environment.
    ``in_step`` (pickled) holds the outputs that have written everything the
    environment holds. A build that read or removed documents leaves only its
    own output in step. A build whose output is not in step writes every page
    once, without reading again: another builder read the changes it has not
    written. A build in step writes, when objects were added, removed or moved
    to other pages, every page that links to a MATLAB object. A build whose
    chooser pages on disk are not current writes the root document too, so
    that Sphinx < 8.2, which skips collecting pages when it writes nothing,
    renders them.

    Runs in the main process, after reading and before Sphinx pickles the
    environment (only when some page is to be written).
    """
    dom = env.get_domain("mat")
    data = dom.data
    key = builder_key(app.builder)
    remove_stale_pages(app, dom, key)
    if key not in data["in_step"]:
        docnames = sorted(env.found_docs)
    elif dom.objects_before != data["objects"]:
        docnames = sorted(data["xref_docs"])
    else:
        docnames = []
    root = app.config.root_doc
    if (
        root in env.found_docs
        and _themed(app)
        and not _cached(app.builder, *_choosers(app))
    ):
        docnames = sorted({*docnames, root})
    if dom.read_docnames or dom.removed_docs:
        data["in_step"].clear()
    data["in_step"].add(key)
    return docnames


def _api_prefix(app):
    """Return the docname prefix of ``matlab_apidoc_output_dir`` (``""`` for the
    source folder itself), or None when there is none below the source folder.
    """
    output_dir = app.config.matlab_apidoc_output_dir
    if not output_dir:
        return None
    srcdir = Path(app.srcdir).resolve()
    api = (srcdir / output_dir).resolve()
    if not api.is_relative_to(srcdir):
        return None
    prefix = api.relative_to(srcdir).as_posix()
    return "" if prefix == "." else prefix + "/"


def remove_stale_pages(app, dom, key):
    """Remove the HTML page (and its copied source) of each document below
    ``matlab_apidoc_output_dir`` that the output ``key`` has a page for and
    that is gone, which Sphinx keeps; then note the documents it has pages
    for now (``api_pages``, pickled).

    Another builder on the same doctree folder may have seen the removal, so
    this compares with the documents of the output's last build, not with
    the documents removed in this build. Only pages of documents this
    output's builds wrote are removed.
    """
    if not _html(app):
        return
    pages = dom.data["api_pages"]
    found = app.env.found_docs
    builder = app.builder
    outdir = str(builder.outdir)
    link_suffix = app.config.html_sourcelink_suffix
    for docname in sorted(pages.get(key, set()) - found):
        paths = [str(builder.get_outfilename(docname))]
        for suffix in app.config.source_suffix:
            name = docname + suffix
            if suffix != link_suffix:
                name += link_suffix
            paths.append(os.path.join(outdir, "_sources", *name.split("/")))
        for path in paths:
            if not os.path.isfile(path):
                continue
            os.remove(path)
            folder = os.path.dirname(path)
            while os.path.normcase(folder) != os.path.normcase(
                outdir
            ) and not os.listdir(folder):
                os.rmdir(folder)
                folder = os.path.dirname(folder)
    prefix = _api_prefix(app)
    pages[key] = set() if prefix is None else {d for d in found if d.startswith(prefix)}
