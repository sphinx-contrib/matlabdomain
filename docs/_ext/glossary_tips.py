"""Hover tips for links to glossary terms.

A Sphinx extension of these docs only; it is not part of
sphinxcontrib-matlabdomain. Before the HTML builder writes any page, it
renders the definition of every glossary term as text and writes them,
sorted, into one ``_static/glossary-tips.js``, next to
``_static/glossary-tips.css``. It runs once, in the main process, so a
``-j`` build writes the same files as a serial one, and the same sources
give the same bytes. The tips need no network: the script is our own.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, cast

from docutils import nodes
from sphinx import addnodes

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.builders import Builder
    from sphinx.builders.html import StandaloneHTMLBuilder
    from sphinx.domains.std import StandardDomain
    from sphinx.util.typing import ExtensionMetadata

HERE = Path(__file__).parent
SCRIPT = "glossary-tips.js"
STYLE = "glossary-tips.css"
# Builders whose target URIs are page paths below the site root.
BUILDERS = {"html", "dirhtml"}
# Removed from a tip: they mark places, not text.
DROPPED = (addnodes.index, nodes.target, nodes.system_message, nodes.comment)
# Replaced by their text: a tip shows no links.
UNLINKED = (nodes.reference, addnodes.pending_xref, addnodes.download_reference)


def setup(app: Sphinx) -> ExtensionMetadata:
    app.connect("builder-inited", _add_assets)
    app.connect("write-started", _write_tips)
    return {"version": "1", "parallel_read_safe": True, "parallel_write_safe": True}


def _add_assets(app: Sphinx) -> None:
    if app.builder.name in BUILDERS:
        app.add_css_file(STYLE)
        app.add_js_file(SCRIPT, loading_method="defer")


def _write_tips(app: Sphinx, builder: Builder) -> None:
    """Write the tips before the pages, so their links carry a checksum."""
    if builder.name not in BUILDERS:
        return
    std = cast("StandardDomain", app.env.get_domain("std"))
    labels: dict[str, set[str]] = defaultdict(set)
    for (objtype, _name), (docname, labelid) in std.objects.items():
        if objtype == "term":
            labels[docname].add(labelid)
    tips: dict[str, str] = {}
    for docname, ids in labels.items():
        uri = builder.get_target_uri(docname)
        # A copy of the page, with its references resolved for their text.
        doctree = app.env.get_doctree(docname)
        app.env.apply_post_transforms(doctree, docname)
        for term in doctree.findall(nodes.term):
            for labelid in ids.intersection(term["ids"]):
                tips[f"{uri}#{labelid}"] = _render(builder, term)  # type: ignore[arg-type]
    static = Path(builder.outdir, "_static")
    static.mkdir(parents=True, exist_ok=True)
    data = json.dumps(tips, ensure_ascii=False, sort_keys=True)
    script = (HERE / "glossary_tips.js").read_text(encoding="utf-8")
    (static / SCRIPT).write_text(
        f"{script}\nglossaryTips({data});\n", encoding="utf-8", newline="\n"
    )
    style = (HERE / "glossary_tips.css").read_text(encoding="utf-8")
    (static / STYLE).write_text(style, encoding="utf-8", newline="\n")


def _render(builder: StandaloneHTMLBuilder, term: nodes.term) -> str:
    """Render a tip: the term, then its definition as text."""
    parts: list[nodes.Element] = [
        nodes.paragraph("", term.astext(), classes=["glossary-tip-term"])
    ]
    for item in term.parent.children:  # the term's definition_list_item
        if isinstance(item, nodes.definition):
            parts.extend(
                child.deepcopy()  # type: ignore[misc]
                for child in item.children
                if not isinstance(child, DROPPED)
            )
    html = []
    for part in parts:
        for node in list(part.findall(lambda n: isinstance(n, DROPPED))):
            node.parent.remove(node)
        for node in list(part.findall(lambda n: isinstance(n, UNLINKED))):
            link = cast("nodes.Element", node)
            link.replace_self(nodes.inline("", "", *link.children))
        for node in part.findall(nodes.Element):
            node["ids"] = []
        html.append(builder.render_partial(part)["fragment"])
    return "".join(html)
