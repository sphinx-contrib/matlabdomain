"""sphinxcontrib.mat_sidecars.
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sidecar docs (pages next to code; plan.md Section 2.11): ``.md`` and
``.rst`` files in the project, indexed with the code (``mat_types``) and
rendered into a document by ``mat:autosidecar``.

- Relative paths in a sidecar doc are relative to its folder: images and
  downloads are rewritten to source-folder-relative paths (``/`` +
  ``relpath(target, srcdir)``); ``literalinclude`` and ``include`` resolve
  from the sidecar doc's folder while it is parsed.
- Markdown links (myst-parser): a sidecar doc -> its document, an indexed
  code file -> its API entry, another existing file -> a download; anything
  else is myst-parser's.
- Broken relative links and missing images are recorded for
  ``matlab-api-check`` (``sidecar_issues``).

:copyright: Copyright by the sphinxcontrib-matlabdomain team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import functools
import glob
import os
import re
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass, field

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.statemachine import StringList
from docutils.utils import get_source_line
from sphinx import addnodes
from sphinx.errors import ConfigError
from sphinx.util.docutils import SphinxDirective
from sphinx.util.logging import getLogger
from sphinx.util.nodes import clean_astext, nested_parse_with_titles

from . import mat_naming, mat_types

logger = getLogger("matlab-domain")

MARKDOWN = ".md"
#: kinds of sidecar issues
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
    """``config-inited``: check ``matlab_src_sidecar_suffixes`` (or ConfigError)
    and, when the project root is inside the Sphinx source folder, add the
    sidecar docs to ``exclude_patterns`` so Sphinx does not also read them as
    documents. It must happen here: a later change makes Sphinx see a
    changed config and read every document again on every build.
    """
    suffixes = mat_types.sidecar_suffix_list(config.matlab_src_sidecar_suffixes)
    if not suffixes:
        return
    root = mat_types.project_root(config, app.srcdir)
    if root is None:
        raise ConfigError(
            "matlab_src_sidecar_suffixes needs matlab_src_code_project_root."
        )
    if MARKDOWN in suffixes and "myst_parser" not in app.extensions:
        raise ConfigError(
            "matlab_src_sidecar_suffixes has '.md': add 'myst_parser' to extensions "
            "(pip install sphinxcontrib-matlabdomain[markdown])."
        )
    srcdir = os.path.normpath(os.fspath(app.srcdir))
    mat_types.sidecar_layout_error(root, srcdir)
    if not same_drive(root, srcdir):
        _warn(
            "sidecar",
            f"matlab_src_code_project_root {root} is on another drive than the "
            "Sphinx source folder: relative paths in sidecar docs (images, downloads, "
            "includes) cannot be resolved.",
        )
    elif mat_types._within(root, srcdir):
        settings = mat_types.IndexSettings.from_config(config, srcdir)
        config.exclude_patterns = [
            *config.exclude_patterns,
            *(
                _escape_glob(os.path.relpath(path, srcdir).replace(os.sep, "/"))
                for path in mat_types.sidecar_paths(settings)
            ),
        ]


def read_sidecar(path, ref):
    """Return the text of a sidecar doc: UTF-8 (a byte-order mark is dropped);
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


#: a URI scheme (``mailto:``, ``matlab:``); one letter is a Windows drive
_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]+:")


def _external(target):
    """Return True for a URI with a scheme (a URL, ``mailto:``, a data URI)
    or an absolute path.
    """
    return (
        bool(_SCHEME.match(target)) or target.startswith("/") or os.path.isabs(target)
    )


def _exists(path):
    """Return True if ``path`` (an image path may end with ``.*``) exists."""
    if "*" in path:
        return bool(glob.glob(path))
    return os.path.isfile(path)


@dataclass
class _Relative:
    """Relative paths from ``folder``: a sidecar doc's or a code file's."""

    folder: str
    srcdir: str
    dom: object
    #: ``(kind, target, line)`` of broken relative links and missing images
    issues: list = field(default_factory=list)

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
        """``(node, text)`` for a link relative to ``folder``, or None to leave
        it as it is. ``text`` is shown for a link without text.
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
        if (sidecar := self.dom.data["sidecars"].get(path)) is not None:
            ref = sidecar["reference"]
            node = addnodes.pending_xref(
                "",
                refdomain="mat",
                reftype="sidecar",
                reftarget=ref,
                reftargetid=anchor,
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
        for node, key, kind in _path_nodes(tree):
            self.rewrite_node(node, key, kind)

    def rewrite_node(self, node, key, kind):
        target = node[key]
        if _external(target):
            return
        path = os.path.normpath(os.path.join(self.folder, target))
        if not _exists(path):
            self.issues.append((kind, target, node.line))
        source = self.source_path(path)
        if source is not None:
            node[key] = source


class _Sidecar(_Relative):
    """One sidecar doc being rendered into the current document."""

    def __init__(self, ref, path, srcdir, dom):
        super().__init__(os.path.dirname(path), srcdir, dom)
        self.ref, self.path = ref, path


def _path_nodes(tree):
    """``(node, attribute, kind)`` of the images and downloads in ``tree``."""
    targets = [(img, "uri", IMAGE) for img in tree.findall(nodes.image)]
    targets += [
        (ref, "reftarget", LINK) for ref in tree.findall(addnodes.download_reference)
    ]
    return targets


@contextmanager
def relative_includes(env, current):
    """Resolve relative names in ``literalinclude`` and ``include`` (which
    call ``env.relfn2path`` without a docname) from the folder of
    ``current()``, a ``_Relative``, or as usual when it is None.
    """
    # Sidecar docs and help text may nest: restore the outer wrapper.
    outer = env.__dict__.get("relfn2path")
    original = env.relfn2path

    def relfn2path(filename, docname=None):
        if docname is None and not _external(filename):
            if (rel := current()) is not None:
                source = rel.source_path(os.path.join(rel.folder, filename))
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


#: source of the lines of help text (``MatlabDocumenter.add_content``)
HELP_SOURCE = "docstring of "


class HelpPaths:
    """Relative paths in help text, resolved from the folder of its code
    file: images, downloads, ``literalinclude``, ``include`` and hyperlinks.
    """

    def __init__(self, env, document):
        self.env = env
        self.document = document
        # Help text exists only with a project root.
        self.root = mat_types.project_root(env.config, env.srcdir)
        self.srcdir = os.path.normpath(os.fspath(env.srcdir))
        self.dom = env.get_domain("mat")
        self._folders = {}

    def at(self, source):
        """Return the ``_Relative`` of the help text with ``source``, or None."""
        if not (source or "").startswith(HELP_SOURCE):
            return None
        ref = source[len(HELP_SOURCE) :]
        folder = os.path.normpath(
            os.path.join(self.root, *mat_naming.folder_of(ref).split("/"))
        )
        if folder not in self._folders:
            self._folders[folder] = _Relative(folder, self.srcdir, self.dom)
        return self._folders[folder]

    def parsing(self):
        """Context manager: includes resolve from the line being parsed."""
        return relative_includes(
            self.env, lambda: self.at(self.document.current_source)
        )

    def rewrite(self, result):
        """Resolve the relative paths of help text in the nodes ``result``."""
        for tree in result:
            for node, key, kind in _path_nodes(tree):
                if (rel := self.at(get_source_line(node)[0])) is not None:
                    rel.rewrite_node(node, key, kind)
            for ref in list(tree.findall(nodes.reference)):
                self._hyperlink(ref)

    def _hyperlink(self, ref):
        """Turn a relative hyperlink to a sidecar doc or code file into a
        reference to it, to another file into a download.
        """
        target = ref.get("refuri")
        if not target or (rel := self.at(get_source_line(ref)[0])) is None:
            return
        found = rel.link(target, ref.line)
        if found is None:
            return
        node = found[0]
        node["refdoc"] = self.env.docname
        node["refexplicit"] = True
        node += nodes.inline("", "", *ref.children)
        ref.replace_self(node)


@functools.cache
def _renderer_class():
    """myst-parser's Sphinx renderer, adapted to render one page into the
    current document (imported on first use: myst-parser is optional).
    """
    from myst_parser.mdit_to_docutils.sphinx_ import SphinxRenderer

    class SidecarRenderer(SphinxRenderer):
        def setup_render(self, options, env):
            super().setup_render(options, env)
            # Sections go below the directive's node, as in MyST's include.
            self._level_to_section = {0: self.current_node}
            env["temp_root_node"] = self.current_node

        def add_line_and_source_path(self, node, token):
            super().add_line_and_source_path(node, token)
            node.source = self.md_options["matlab_sidecar"].path

        def create_warning(
            self, message, subtype, *, wtype=None, line=None, append_to=None
        ):
            # At the sidecar doc's line, not the line of the rendering document.
            from myst_parser.warnings_ import create_warning

            where = nodes.Element()
            where.source, where.line = self.md_options["matlab_sidecar"].path, line
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
            # heading slugs add to those of sidecar docs rendered before.
            self.md_env.pop("wordcount", None)
            earlier = getattr(self.document, "myst_slugs", None) or {}
            self._heading_slugs = {**earlier, **self._heading_slugs}
            super()._render_finalise()

        def render_link_unknown(self, token):
            sidecar = self.md_options["matlab_sidecar"]
            dest = self.md.normalizeLinkText(token.attrGet("href") or "")
            explicit = token.info != "auto" and bool(token.children)
            found = sidecar.link(dest, token.map[0] if token.map else None)
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

    return SidecarRenderer


class AutoSidecar(SphinxDirective):
    """``.. mat:autosidecar:: <path reference>``: render a sidecar doc.

    Its headings become sections; the first is the sidecar doc's title (one
    without a heading gets its file name, with a warning). ``:no-title:``
    drops the first heading (a folder's README as the folder page's
    introduction).
    """

    required_arguments = 1
    final_argument_whitespace = True
    option_spec = {"no-title": directives.flag}

    def run(self):
        ref = unicodedata.normalize("NFC", self.arguments[0].strip())
        dom = self.env.get_domain("mat")
        path = dom.sidecar_paths().get(ref)
        if path is None:
            root = mat_types.project_root(self.config, self.env.srcdir)
            if root is not None:
                # Read again once the sidecar doc exists.
                self.env.note_dependency(os.path.join(root, *ref.split("/")))
            _warn(
                "sidecar",
                f"{ref} is not a sidecar doc (see matlab_src_sidecar_suffixes).",
                self.get_location(),
            )
            return []
        self.env.note_dependency(path)
        try:
            text = read_sidecar(path, ref)
        except OSError as err:
            _warn("parse_error", f"{ref} cannot be read ({err.strerror or err}).")
            return []
        sidecar = _Sidecar(ref, path, os.path.normpath(os.fspath(self.env.srcdir)), dom)
        container = nodes.Element()
        container.document = self.state.document
        with relative_includes(self.env, lambda: sidecar):
            if path.endswith(MARKDOWN):
                self._markdown(text, sidecar, container)
            else:
                lines = StringList(text.splitlines(), source=path)
                nested_parse_with_titles(self.state, lines, container)
        sidecar.rewrite(container)
        result, title = self._titled(list(container.children), sidecar)
        dom.note_sidecar(ref, title, sidecar.issues)
        return result

    def _markdown(self, text, sidecar, container):
        from myst_parser.parsers.mdit import create_md_parser

        parser = create_md_parser(self.env.myst_config, _renderer_class())
        parser.options["document"] = self.state.document
        parser.options["current_node"] = container
        parser.options["matlab_sidecar"] = sidecar
        parser.render(text, {})

    def _titled(self, result, sidecar):
        """``(nodes, title)``: the sidecar doc's nodes and its title text."""
        first = next(
            (i for i, node in enumerate(result) if isinstance(node, nodes.section)),
            None,
        )
        name = os.path.basename(sidecar.path)
        title = name if first is None else clean_astext(result[first][0])
        if "no-title" in self.options:
            if first is not None:
                result[first : first + 1] = result[first].children[1:]
            return result, title
        if first is None:
            _warn(
                "sidecar",
                f"{sidecar.ref} has no heading; its file name is its title.",
                f"{sidecar.path}:1",
            )
            section = nodes.section("", nodes.title(name, name), *result)
            section["names"].append(nodes.fully_normalize_name(name))
            self.state.document.note_implicit_target(section, section)
            result = [section]
        return result, title
