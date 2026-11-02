"""sphinxcontrib.mat_pages.
~~~~~~~~~~~~~~~~~~~~~~~

Pages next to code (plan.md Section 2.11): ``.md`` and ``.rst`` files in
the project, indexed with the code (``mat_types``) and rendered into a
document by ``mat:autopage``.

- Relative paths in a page are relative to the page's folder: images and
  downloads are rewritten to source-folder-relative paths (``/`` +
  ``relpath(target, srcdir)``); ``literalinclude`` and ``include`` resolve
  from the page's folder while it is parsed.
- Markdown links (myst-parser): a page -> its document, an indexed code
  file -> its API entry, another existing file -> a download; anything else
  is myst-parser's.
- Broken relative links and missing images are recorded for
  ``matlab-api-check`` (``page_issues``).

:copyright: Copyright by the sphinxcontrib-matlabdomain team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import functools
import glob
import os
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass, field

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.statemachine import StringList
from sphinx import addnodes
from sphinx.errors import ConfigError
from sphinx.util.docutils import SphinxDirective
from sphinx.util.logging import getLogger
from sphinx.util.nodes import clean_astext, nested_parse_with_titles

from . import mat_types

logger = getLogger("matlab-domain")

MARKDOWN = ".md"
#: kinds of page issues
LINK, IMAGE = "link", "image"


def _warn(subtype, message, location=None):
    logger.warning(
        "[sphinxcontrib-matlabdomain] %s",
        message,
        type="mat",
        subtype=subtype,
        location=location,
    )


def same_drive(a, b):
    """Return True if the paths ``a`` and ``b`` are on the same drive."""
    return os.path.normcase(os.path.splitdrive(a)[0]) == os.path.normcase(
        os.path.splitdrive(b)[0]
    )


def _escape_glob(path):
    """``path`` as an ``exclude_patterns`` entry that matches only itself
    (``[`` also matches ``]``: ``[[]`` would be a nested set to ``re``).
    """
    return "".join({"*": "[*]", "?": "[?]", "[": "[][]"}.get(c, c) for c in path)


def check_config(app, config):
    """``config-inited``: check ``matlab_src_page_suffixes`` (or ConfigError)
    and, when the project root is inside the Sphinx source folder, add the
    pages to ``exclude_patterns`` so Sphinx does not also read them as
    documents. It must happen here: a later change makes Sphinx see a
    changed config and read every document again on every build.
    """
    suffixes = mat_types.page_suffix_list(config.matlab_src_page_suffixes)
    if not suffixes:
        return
    root = mat_types.project_root(config, app.srcdir)
    if root is None:
        raise ConfigError(
            "matlab_src_page_suffixes needs matlab_src_code_project_root."
        )
    if MARKDOWN in suffixes and "myst_parser" not in app.extensions:
        raise ConfigError(
            "matlab_src_page_suffixes has '.md': add 'myst_parser' to extensions "
            "(pip install sphinxcontrib-matlabdomain[markdown])."
        )
    srcdir = os.path.normpath(os.fspath(app.srcdir))
    mat_types.page_layout_error(root, srcdir)
    if not same_drive(root, srcdir):
        _warn(
            "page",
            f"matlab_src_code_project_root {root} is on another drive than the "
            "Sphinx source folder: relative paths in pages (images, downloads, "
            "includes) cannot be resolved.",
        )
    elif mat_types._within(root, srcdir):
        settings = mat_types.IndexSettings.from_config(config, srcdir)
        config.exclude_patterns = [
            *config.exclude_patterns,
            *(
                _escape_glob(os.path.relpath(path, srcdir).replace(os.sep, "/"))
                for path in mat_types.page_paths(settings)
            ),
        ]


def read_page(path, ref):
    """Return the text of a page: UTF-8 (a byte-order mark is dropped);
    invalid bytes are replaced, with one ``mat.encoding`` warning.
    """
    with open(path, "rb") as f:
        data = f.read()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as err:
        row = data[: err.start].count(b"\n") + 1
        _warn(
            "encoding",
            f"{ref} is not valid UTF-8; the invalid bytes are replaced.",
            f"{path}:{row}",
        )
        return data.decode("utf-8-sig", errors="replace")


def _external(target):
    """Return True for a URL, a data URI or an absolute path."""
    return "://" in target or target.startswith(("/", "data:")) or os.path.isabs(target)


def _exists(path):
    """Return True if ``path`` (an image path may end with ``.*``) exists."""
    if "*" in path:
        return bool(glob.glob(path))
    return os.path.isfile(path)


@dataclass
class _Page:
    """One page being rendered into the current document."""

    ref: str
    path: str
    srcdir: str
    dom: object
    #: ``(kind, target, line)`` of broken relative links and missing images
    issues: list = field(default_factory=list)

    @property
    def folder(self):
        return os.path.dirname(self.path)

    def source_path(self, target):
        """``target`` (absolute) as Sphinx's source-folder-relative path
        (``/`` + relpath), or None on another drive.
        """
        try:
            rel = os.path.relpath(target, self.srcdir)
        except ValueError:
            return None
        return "/" + rel.replace(os.sep, "/")

    def link(self, dest, line):
        """``(node, text)`` for a Markdown link relative to the page, or None
        for myst-parser to handle. ``text`` is shown for a link without text.
        """
        target, _, anchor = dest.partition("#")
        if not target or _external(target):
            return None
        path = os.path.normpath(os.path.join(self.folder, target))
        if not os.path.isfile(path):
            self.issues.append((LINK, target, line))
            # Read the document again once the file exists.
            self.dom.env.note_dependency(path)
            return None
        if (page := self.dom.data["pages"].get(path)) is not None:
            ref = page["reference"]
            node = addnodes.pending_xref(
                "", refdomain="mat", reftype="page", reftarget=ref, reftargetid=anchor
            )
            return node, ref
        if (record := self.dom.data["index"].get(path)) is not None:
            ref = record["reference"]
            node = addnodes.pending_xref(
                "", refdomain="mat", reftype="obj", reftarget=ref
            )
            return node, mat_types.display_name(self.dom, ref)
        source = self.source_path(path)
        if source is None:
            return None
        node = addnodes.download_reference(
            "", refdomain=None, reftype="myst", reftarget=source
        )
        return node, None

    def rewrite(self, tree):
        """Make relative image and download paths source-folder-relative;
        record missing targets.
        """
        targets = [(img, "uri", IMAGE) for img in tree.findall(nodes.image)]
        targets += [
            (ref, "reftarget", LINK)
            for ref in tree.findall(addnodes.download_reference)
        ]
        for node, key, kind in targets:
            target = node[key]
            if _external(target):
                continue
            path = os.path.normpath(os.path.join(self.folder, target))
            if not _exists(path):
                self.issues.append((kind, target, node.line))
            source = self.source_path(path)
            if source is not None:
                node[key] = source


@functools.cache
def _renderer_class():
    """myst-parser's Sphinx renderer, adapted to render one page into the
    current document (imported on first use: myst-parser is optional).
    """
    from myst_parser.mdit_to_docutils.sphinx_ import SphinxRenderer

    class PageRenderer(SphinxRenderer):
        def setup_render(self, options, env):
            super().setup_render(options, env)
            # Sections go below the directive's node, as in MyST's include.
            self._level_to_section = {0: self.current_node}
            env["temp_root_node"] = self.current_node

        def add_line_and_source_path(self, node, token):
            super().add_line_and_source_path(node, token)
            node.source = self.md_options["matlab_page"].path

        def create_warning(
            self, message, subtype, *, wtype=None, line=None, append_to=None
        ):
            # At the page's line, not the line of the rendering document.
            from myst_parser.warnings_ import create_warning

            where = nodes.Element()
            where.source, where.line = self.md_options["matlab_page"].path, line
            return create_warning(
                self.document,
                message,
                subtype,
                wtype=wtype,
                node=where,
                append_to=append_to,
            )

        def _render_finalise(self):
            # The word count is the document's (a MyST document adds its own);
            # heading slugs add to those of pages rendered before.
            self.md_env.pop("wordcount", None)
            earlier = getattr(self.document, "myst_slugs", None) or {}
            self._heading_slugs = {**earlier, **self._heading_slugs}
            super()._render_finalise()

        def render_link_unknown(self, token):
            page = self.md_options["matlab_page"]
            dest = self.md.normalizeLinkText(token.attrGet("href") or "")
            explicit = token.info != "auto" and bool(token.children)
            found = page.link(dest, token.map[0] if token.map else None)
            if found is None:
                return super().render_link_unknown(token)
            node, text = found
            node["refdoc"] = self.sphinx_env.docname
            node["refexplicit"] = explicit
            classes = ["xref", "myst"]
            if isinstance(node, addnodes.download_reference):
                classes.insert(1, "download")
            self._process_wrap_node(node, token, explicit, classes, dest)
            if not explicit and text is not None:
                node[-1] += nodes.Text(text)

    return PageRenderer


class AutoPage(SphinxDirective):
    """``.. mat:autopage:: <path reference>``: render a page next to code.

    Its headings become sections; the first is the page title (a page
    without one gets its file name, with a warning). ``:no-title:`` drops
    the first heading (a folder's README as the folder page's
    introduction).
    """

    required_arguments = 1
    final_argument_whitespace = True
    option_spec = {"no-title": directives.flag}

    def run(self):
        ref = unicodedata.normalize("NFC", self.arguments[0].strip())
        dom = self.env.get_domain("mat")
        path = dom.page_paths().get(ref)
        if path is None:
            root = mat_types.project_root(self.config, self.env.srcdir)
            if root is not None:
                # Read again once the page exists.
                self.env.note_dependency(os.path.join(root, *ref.split("/")))
            _warn(
                "page",
                f"{ref} is not a page next to code (see matlab_src_page_suffixes).",
                self.get_location(),
            )
            return []
        self.env.note_dependency(path)
        try:
            text = read_page(path, ref)
        except OSError as err:
            _warn("parse_error", f"{ref} cannot be read ({err.strerror or err}).")
            return []
        page = _Page(ref, path, os.path.normpath(os.fspath(self.env.srcdir)), dom)
        container = nodes.Element()
        container.document = self.state.document
        with self._relative_to(page):
            if path.endswith(MARKDOWN):
                self._markdown(text, page, container)
            else:
                lines = StringList(text.splitlines(), source=path)
                nested_parse_with_titles(self.state, lines, container)
        page.rewrite(container)
        result, title = self._titled(list(container.children), page)
        dom.note_page(ref, title, page.issues)
        return result

    @contextmanager
    def _relative_to(self, page):
        """Resolve relative names in ``literalinclude`` and ``include`` (which
        call ``env.relfn2path`` without a docname) from the page's folder.
        """
        env = self.env
        # A page may render another page: restore the outer one's wrapper.
        outer = env.__dict__.get("relfn2path")
        original = env.relfn2path

        def relfn2path(filename, docname=None):
            if docname is None and not _external(filename):
                source = page.source_path(os.path.join(page.folder, filename))
                if source is not None:
                    filename = source
            return original(filename, docname)

        env.relfn2path = relfn2path
        try:
            yield
        finally:
            if outer is None:
                del env.relfn2path
            else:
                env.relfn2path = outer

    def _markdown(self, text, page, container):
        from myst_parser.parsers.mdit import create_md_parser

        parser = create_md_parser(self.env.myst_config, _renderer_class())
        parser.options["document"] = self.state.document
        parser.options["current_node"] = container
        parser.options["matlab_page"] = page
        parser.render(text, {})

    def _titled(self, result, page):
        """``(nodes, title)``: the page's nodes and its title text."""
        first = next(
            (i for i, node in enumerate(result) if isinstance(node, nodes.section)),
            None,
        )
        name = os.path.basename(page.path)
        title = name if first is None else clean_astext(result[first][0])
        if "no-title" in self.options:
            if first is not None:
                result[first : first + 1] = result[first].children[1:]
            return result, title
        if first is None:
            _warn(
                "page",
                f"{page.ref} has no heading; its file name is its title.",
                f"{page.path}:1",
            )
            section = nodes.section("", nodes.title(name, name), *result)
            section["names"].append(nodes.fully_normalize_name(name))
            self.state.document.note_implicit_target(section, section)
            result = [section]
        return result, title
