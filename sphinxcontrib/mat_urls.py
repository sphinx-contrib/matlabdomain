"""sphinxcontrib.mat_urls
~~~~~~~~~~~~~~~~~~~~~~

Stable addresses of documented objects in HTML builds (plan.md Section 2.3).

API pages split into ``global.html``, ``global-2.html``, ... by
``matlab_apidoc_page_size``, so the page an object is on can change. Each
build writes small redirect files whose addresses do not depend on the pages:

- ``mat/ref/<path reference>.html`` for every object (folders:
  ``mat/ref/<folder>/index.html``);
- ``mat/name/<MATLAB name>.html`` for every MATLAB name of a non-private
  object: a redirect if one object has it, else a page that lists them all.

The "¶" link of an object points to its stable address: by MATLAB name if
it is unique, else by path reference; the ``mat`` entries of ``objects.inv``
point to the address by path reference, so another project's links follow an
object even with an old inventory. File names are escaped like the pages
of ``sphinx-matlab-apidoc``. Only files with ``MARKER`` are rewritten or
removed.
"""

from __future__ import annotations

import html
import json
import os
import re
import zlib
from urllib.parse import quote

from sphinx.util.logging import getLogger
from sphinx.util.osutil import relative_uri

from . import mat_naming
from .matlab_apidoc._names import docnames

logger = getLogger("matlab-domain")

ROOT = "mat"
MARKER = "<!-- sphinxcontrib-matlabdomain stable address -->"
_FRAGMENT_SAFE = "/+-._~:@!$()*,="
_PERMALINK = re.compile(r'(<a class="headerlink" href=")#(mat-[^"]*)(")')
# An objects.inv line: name, domain:type, priority, URI, display name.
_INVENTORY_LINE = re.compile(r"(.+?) (mat:\w+) (-?\d+) \S+ (.*)")


def enabled(app):
    builder = app.builder
    return (
        app.config.matlab_stable_urls
        and getattr(builder, "format", "") == "html"
        and not builder.name.startswith("epub")
    )


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


def _chooser(name, entries):
    items = "".join(
        f'<li><a href="{html.escape(target)}">{html.escape(ref)}</a> ({objtype})</li>\n'
        for ref, objtype, target in entries
    )
    title = html.escape(name)
    return (
        f'<!DOCTYPE html>\n{MARKER}\n<html><head><meta charset="utf-8">\n'
        f"<title>{title}</title></head><body>\n"
        f"<h1>{title}</h1>\n<p>Several objects are named <code>{title}</code>:</p>\n"
        f"<ul>\n{items}</ul>\n</body></html>\n"
    )


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
            f.readline()
            return f.readline().rstrip("\r\n") == MARKER
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
    files = {}
    for ref, stub in by_ref.items():
        files[stub] = _redirect(objects[ref][2], _target(builder, dom, stub, ref))
    for name, stub in by_name.items():
        refs = names[name]
        if len(refs) == 1:
            files[stub] = _redirect(name, _target(builder, dom, stub, refs[0]))
        else:
            entries = [
                (ref, objects[ref][1], _target(builder, dom, stub, ref)) for ref in refs
            ]
            files[stub] = _chooser(name, entries)
    outdir = str(builder.outdir)
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
    wanted = {os.path.normcase(os.path.join(outdir, *s.split("/"))) for s in files}
    for folder, _, names_in in os.walk(root, topdown=False):
        for file in names_in:
            path = os.path.join(folder, file)
            if os.path.normcase(path) not in wanted and _is_ours(path):
                os.remove(path)
        if folder != root and not os.listdir(folder):
            os.rmdir(folder)
    uris = {ref: quote(stub) for ref, stub in by_ref.items() if stub not in failed}
    rewrite_inventory(os.path.join(outdir, "objects.inv"), uris)
