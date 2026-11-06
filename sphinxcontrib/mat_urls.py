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
of ``sphinx-matlab-apidoc``. Only files with ``MARKER`` are rewritten or
removed.

A page opened at the anchor of an object that is no longer on it (an
address copied from the browser), and the site's ``404.html``, send the
browser to the object's stable address (``SCRIPT``, ``mat/refs.js``).

Incremental builds: pages whose ``sphinx-matlab-apidoc`` source is gone are
removed, and when objects moved, every page that links to a MATLAB object is
written again.
"""

from __future__ import annotations

import html
import json
import os
import re
import zlib
from pathlib import Path
from urllib.parse import quote

from sphinx.util.logging import getLogger
from sphinx.util.osutil import relative_uri

from . import mat_naming
from .matlab_apidoc._names import docnames

logger = getLogger("matlab-domain")

ROOT = "mat"
MARKER = "<!-- sphinxcontrib-matlabdomain stable address -->"
SCRIPT = "mat_urls.js"
REFS = f"{ROOT}/refs.js"
_FRAGMENT_SAFE = "/+-._~:@!$()*,="
_PERMALINK = re.compile(r'(<a class="headerlink" href=")#(mat-[^"]*)(")')
# An objects.inv line: name, domain:type, priority, URI, display name.
_INVENTORY_LINE = re.compile(r"(.+?) (mat:\w+) (-?\d+) \S+ (.*)")
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
    builder = app.builder
    return getattr(builder, "format", "") == "html" and not builder.name.startswith(
        "epub"
    )


def enabled(app):
    return app.config.matlab_stable_urls and _html(app)


def _names(dom):
    """MATLAB name -> references of the non-private objects that have it."""
    out = {}
    for ref, (_, _, display) in dom.data["objects"].items():
        if display != ref and not mat_naming.is_private_reference(ref):
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


def rewrite_permalinks(app, pagename, templatename, context, doctree):  # noqa: ARG001
    """``html-page-context``: point the "¶" links of objects to their stable
    addresses.
    """
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


def chooser_pages(app):
    """``html-collect-pages``: the pages that list the objects of a MATLAB
    name several objects have, in the site's theme. Only builders that write
    ``<page>.html`` for page ``<page>``; ``write_redirects`` writes the others.
    """
    builder = app.builder
    builder.mat_chooser_pages = set()
    probe = f"{ROOT}/name/x"
    if not enabled(app) or (
        builder.get_target_uri(probe) != f"{probe}.html"
        or os.path.normcase(builder.get_outfilename(probe))
        != os.path.normcase(os.path.join(builder.outdir, ROOT, "name", "x.html"))
    ):
        return []
    dom = app.env.get_domain("mat")
    _, by_name, names, _ = addresses(dom)
    pages = []
    for name, stub in sorted(by_name.items()):
        if len(names[name]) > 1:
            body = _chooser_body(name, _entries(builder, dom, stub, names[name]))
            pages.append(
                (stub.removesuffix(".html"), {"title": name, "body": body}, "page.html")
            )
            builder.mat_chooser_pages.add(stub)
    return pages


def rewrite_inventory(path, uris):
    """Point the ``mat`` entries of the ``objects.inv`` at ``path`` whose
    name is in ``uris`` (reference -> URI) to that URI.
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
            return MARKER in f.read()
    except OSError:  # pragma: no cover - defensive: unreadable file in mat/
        return False


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
    themed = getattr(builder, "mat_chooser_pages", set())
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
    files[REFS] = f"window.matStableRefs = {json.dumps(refs_map, sort_keys=True)};\n"
    outdir = str(builder.outdir)
    not_found = os.path.join(outdir, "404.html")
    if not os.path.exists(not_found) or _is_ours(not_found):
        files["404.html"] = _not_found(builder.get_target_uri(app.config.root_doc))
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
    uris = {ref: quote(stub) for ref, stub in by_ref.items() if stub not in failed}
    rewrite_inventory(os.path.join(outdir, "objects.inv"), uris)


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
        path = os.path.join(str(app.builder.outdir), "_static", SCRIPT)
        try:
            _write(path, _JS.encode("utf-8"))
        except OSError as err:
            logger.warning(
                "[sphinxcontrib-matlabdomain] cannot write %s: %s",
                path,
                err,
                type="mat",
                subtype="stable_url",
            )


def note_pages(app, env, added, changed, removed):  # noqa: ARG001
    """``env-get-outdated``: remember where each object was, and the removed
    documents, before this build reads anything.
    """
    dom = env.get_domain("mat")
    dom.objects_before = dict(dom.data["objects"])
    dom.removed_docs = set(removed)
    return []


def relink(app, env):  # noqa: ARG001
    """``env-get-updated``: if objects were added, removed or moved to other
    pages, write again every page that links to a MATLAB object (Sphinx writes
    only the pages it read).
    """
    dom = env.get_domain("mat")
    if dom.objects_before == dom.data["objects"]:
        return []
    return sorted(dom.data["xref_docs"])


def remove_stale_pages(app, exception):
    """``build-finished``: remove the HTML page (and its copied source) of each
    removed document below ``matlab_apidoc_output_dir``, which Sphinx keeps.
    """
    dom = app.env.get_domain("mat")
    output_dir = app.config.matlab_apidoc_output_dir
    if exception is not None or not _html(app) or not output_dir:
        return
    srcdir = Path(app.srcdir).resolve()
    api = (srcdir / output_dir).resolve()
    if not api.is_relative_to(srcdir):
        return
    prefix = api.relative_to(srcdir).as_posix()
    prefix = "" if prefix == "." else prefix + "/"
    builder = app.builder
    outdir = str(builder.outdir)
    link_suffix = app.config.html_sourcelink_suffix
    for docname in sorted(dom.removed_docs):
        if not docname.startswith(prefix):
            continue
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
