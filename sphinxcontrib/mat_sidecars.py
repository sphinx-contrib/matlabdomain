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
- Simulink documentation files (``matlab_simulink_doc_suffixes``) are
  parsed the same way into the pages of Simulink files and library blocks
  (``simulink_documentation``).

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
from typing import TYPE_CHECKING, Any, cast

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
from .mat_handlers import handler_for

if TYPE_CHECKING:
    from .matlab import MATLABDomain

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


def _escape_glob(path: str):
    """``path`` as an ``exclude_patterns`` entry that matches only itself
    (``[`` also matches ``]``: ``[[]`` would be a nested set to ``re``).
    """
    replacements = {"*": "[*]", "?": "[?]", "[": "[][]"}
    return "".join(replacements.get(c, c) for c in path)


def check_config(app, config):
    """``config-inited``: check ``matlab_src_sidecar_suffixes`` and
    ``matlab_simulink_doc_suffixes`` (or ConfigError), and add the sidecar docs
    and Simulink documentation files in the Sphinx source folder to
    ``exclude_patterns`` so Sphinx does not also read them as documents. It
    must happen here: a later change makes Sphinx see a changed config and
    read every document again on every build.
    """
    suffixes = mat_types.sidecar_suffix_list(config.matlab_src_sidecar_suffixes)
    simulink = mat_types.simulink_doc_suffix_list(config.matlab_simulink_doc_suffixes)
    root = mat_types.project_root(config, app.srcdir)
    if suffixes and root is None:
        raise ConfigError(
            "matlab_src_sidecar_suffixes needs matlab_src_code_project_root."
        )
    if MARKDOWN in suffixes and "myst_parser" not in app.extensions:
        raise ConfigError(
            "matlab_src_sidecar_suffixes has '.md': add 'myst_parser' to extensions "
            "(pip install sphinxcontrib-matlabdomain[markdown])."
        )
    if root is None or not (suffixes or simulink):
        return
    srcdir = os.path.normpath(os.fspath(app.srcdir))
    if suffixes:
        mat_types.sidecar_layout_error(root, srcdir)
    if not same_drive(root, srcdir):
        if suffixes:
            _warn(
                "sidecar",
                f"matlab_src_code_project_root {root} is on another drive than the "
                "Sphinx source folder: relative paths in sidecar docs (images, "
                "downloads, includes) cannot be resolved.",
            )
        return
    if mat_types._within(root, srcdir):
        settings = mat_types.IndexSettings.from_config(config, srcdir)
        found = mat_types._documentation_files(settings)
        paths = [*found.sidecars, *found.simulink_docs]
    elif mat_types._within(srcdir, root):
        paths = _simulink_docs_below(srcdir, simulink)
    else:
        paths = []
    config.exclude_patterns = [
        *config.exclude_patterns,
        *(
            _escape_glob(os.path.relpath(path, srcdir).replace(os.sep, "/"))
            for path in paths
        ),
    ]


def _simulink_docs_below(folder, suffixes):
    """Simulink documentation files below ``folder`` (the Sphinx source
    folder inside the project root), without the index stage.
    """
    found = []
    build_dir = os.path.join(folder, mat_types.BUILD_FOLDER)
    for dirpath, dirnames, filenames in os.walk(folder):
        if dirpath != folder and (
            dirpath == build_dir
            or mat_types.sphinx_output(dirpath, dirnames + filenames)
        ):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        stems = {
            os.path.splitext(name)[0]
            for name in filenames
            if mat_naming.is_block_container(name)
            and handler_for(os.path.join(dirpath, name)) is not None
        }
        found += [
            os.path.join(dirpath, name)
            for name in filenames
            if os.path.splitext(name)[1] in suffixes
            and os.path.splitext(name)[0] in stems
        ]
    return found


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
    dom: "MATLABDomain"
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

    def rewrite_hyperlink(self, ref):
        """Resolve a hyperlink to a sidecar doc, code file or download."""
        target = ref.get("refuri")
        if not target:
            return
        found = self.link(target, ref.line or get_source_line(ref)[1])
        if found is None:
            return
        node = found[0]
        node["refdoc"] = self.dom.env.docname
        node["refexplicit"] = True
        node += nodes.inline("", "", *ref.children)
        ref.replace_self(node)

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

    def rewrite(self, tree):
        """Also resolve this sidecar doc's relative hyperlinks."""
        super().rewrite(tree)
        for ref in list(tree.findall(nodes.reference)):
            # Nested sidecar docs and help text resolve their own links.
            if get_source_line(ref)[0] == self.path:
                self.rewrite_hyperlink(ref)


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


#: source of the lines of help text (``MatlabDocumenter.add_content``), after
#: the path of its file (``<file>:docstring of <reference>``, as in Python)
HELP_SOURCE = "docstring of "


def help_source(ref, path=None):
    """Return the source of the help lines of the object ``ref`` in ``path``."""
    return f"{path}:{HELP_SOURCE}{ref}" if path else f"{HELP_SOURCE}{ref}"


def help_reference(source):
    """Return the reference of the object whose help has the ``source``, or None."""
    source = source or ""
    if source.startswith(HELP_SOURCE):
        return source[len(HELP_SOURCE) :]
    head, found, ref = source.rpartition(f":{HELP_SOURCE}")
    return ref if head and found else None


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
        if (ref := help_reference(source)) is None:
            return None
        folder = os.path.normpath(
            os.path.join(cast(str, self.root), *mat_naming.folder_of(ref).split("/"))
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
        if (rel := self.at(get_source_line(ref)[0])) is not None:
            rel.rewrite_hyperlink(ref)


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
            self._level_to_section = cast(Any, {0: self.current_node})
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
            self.document.setdefault("matlab_sidecar_slugs", {}).update(
                self._heading_slugs
            )
            earlier = getattr(self.document, "myst_slugs", None) or {}
            self._heading_slugs = {**earlier, **self._heading_slugs}
            super()._render_finalise()

        def render_link_unknown(self, token):
            sidecar = self.md_options["matlab_sidecar"]
            dest = self.md.normalizeLinkText(str(token.attrGet("href") or ""))
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
                cast(nodes.Element, node[-1]).append(nodes.Text(text))

    return SidecarRenderer


@contextmanager
def _reporting_at(reporter, path):
    """Make the roles and warnings of the sidecar doc ``path`` being parsed
    name its file and line (the reporter looks lines up in the document that
    includes it).
    """
    original = reporter.get_source_and_line
    reporter.get_source_and_line = lambda line=None: (path, line)
    try:
        yield
    finally:
        reporter.get_source_and_line = original


def parse_file(directive, path, ref):
    """Parse the ``.md`` or ``.rst`` file ``path`` (path reference ``ref``)
    in the document of ``directive``, with its relative paths resolved from
    its folder: its nodes and the ``_Sidecar`` that resolved the paths.
    Raises OSError when it cannot be read.
    """
    env = directive.env
    text = read_sidecar(path, ref)
    srcdir = os.path.normpath(os.fspath(env.srcdir))
    sidecar = _Sidecar(ref, path, srcdir, env.get_domain("mat"))
    container = nodes.Element()
    container.document = directive.state.document
    with (
        relative_includes(env, lambda: sidecar),
        _reporting_at(directive.state.document.reporter, path),
    ):
        if path.endswith(MARKDOWN):
            parser = _markdown_parser(env)
            parser.options["document"] = directive.state.document
            parser.options["current_node"] = container
            parser.options["matlab_sidecar"] = sidecar
            parser.render(text, {})
        else:
            lines = StringList(text.splitlines(), source=path)
            nested_parse_with_titles(directive.state, lines, container)
    sidecar.rewrite(container)
    return list(container.children), sidecar


def _markdown_parser(env):
    from myst_parser.parsers.mdit import create_md_parser

    return create_md_parser(cast(Any, env).myst_config, _renderer_class())


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
        dom = cast("MATLABDomain", self.env.get_domain("mat"))
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
            result, sidecar = parse_file(self, path, ref)
        except OSError as err:
            _warn("parse_error", f"{ref} cannot be read ({err.strerror or err}).")
            return []
        result, title = self._titled(result, sidecar)
        dom.note_sidecar(ref, title, sidecar.issues)
        return result

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


#: ``env.temp_data`` key: Simulink documentation files parsed in the document
_PARSED = "mat:simulink_docs"


def _heading_key(text):
    return " ".join(text.split())


@dataclass
class _SimulinkDoc:
    """A parsed Simulink documentation file without its title: the text
    before its first section, and its sections ``(key, rubric, body)`` with
    deeper headings as rubrics.
    """

    text: list
    sections: list


def _doc_paths(env, file_ref):
    """Return the Simulink documentation files of the file ``file_ref``, the
    one to use first (``matlab_simulink_doc_suffixes`` order).
    """
    dom = env.get_domain("mat")
    source = dom.source_paths().get(file_ref) if file_ref else None
    if source is None:
        return []
    stem = os.path.splitext(source)[0]
    docs = dom.data["simulink_docs"]
    suffixes = mat_types.simulink_doc_suffix_list(
        env.config.matlab_simulink_doc_suffixes
    )
    return [stem + suffix for suffix in suffixes if stem + suffix in docs]


#: a Markdown heading, and an underline of a reST one
_MD_HEADING = re.compile(r"#{1,6}\s+(.*?)(\s+#+)?\s*")
_RST_UNDERLINE = re.compile(r"([!-/:-@\[-`{-~])\1*\s*")


def documented_blocks(env, file_ref):
    """Heading keys of the Simulink documentation file of ``file_ref``, found
    without parsing it: ``:members:`` counts these blocks as documented.
    """
    paths = _doc_paths(env, file_ref)
    if not paths:
        return set()
    try:
        with open(paths[0], "rb") as f:
            lines = f.read().decode("utf-8-sig", errors="replace").splitlines()
    except OSError:
        return set()
    keys = set()
    for i, line in enumerate(lines):
        if paths[0].endswith(MARKDOWN):
            if match := _MD_HEADING.fullmatch(line):
                keys.add(_heading_key(match[1]))
        elif (
            line.strip()
            and i + 1 < len(lines)
            and _RST_UNDERLINE.fullmatch(lines[i + 1])
        ):
            keys.add(_heading_key(line))
    return keys


def simulink_documentation(directive, ref):
    """Nodes of the Simulink documentation file of the object ``ref``
    (``matlab_simulink_doc_suffixes``): all its text for a model or a
    subsystem file; for a library, its text but the sections of its blocks;
    for a library block, the text of its section. Headings below the title
    become rubrics.
    """
    env = directive.env
    dom = env.get_domain("mat")
    file_ref, members = mat_naming.parse_reference(ref)
    paths = _doc_paths(env, file_ref)
    if not paths:
        return []
    parsed = env.temp_data.setdefault(_PARSED, {})
    if paths[0] not in parsed:
        parsed[paths[0]] = _parse_simulink_doc(directive, file_ref, paths)
    doc = parsed[paths[0]]
    if doc is None:
        return []
    obj = mat_types.resolve(dom, file_ref)
    if members:
        key = _heading_key(members[0])
        found = [body for k, _rubric, body in doc.sections if k == key]
        return _copies(found[0] if found else [])
    if isinstance(obj, mat_types.MatLibrary):
        keys = _block_keys(obj)
        unmatched = [(r, b) for k, r, b in doc.sections if k not in keys]
        return _copies([*doc.text, *(n for r, b in unmatched for n in (r, *b))])
    return _copies([*doc.text, *(n for _k, r, b in doc.sections for n in (r, *b))])


def _copies(found):
    return [node.deepcopy() for node in found]


def _block_keys(library):
    """Keys of the headings of the documented blocks of a library."""
    blocks = library.diagram.library_blocks if library.diagram is not None else ()
    return {_heading_key(b.path): b.path for b in blocks if b.mask is not None}


def _parse_simulink_doc(directive, file_ref, paths):
    """Parse the first of ``paths``, the documentation files of ``file_ref``,
    and warn about the others, about headings that name no block of a
    library, and about blocks without a section.
    """
    env = directive.env
    dom = env.get_domain("mat")
    docs = dom.data["simulink_docs"]
    path, ref = paths[0], docs[paths[0]]["reference"]
    for other in paths[1:]:
        _warn(
            "simulink",
            f"{docs[other]['reference']} is not used: {ref} documents {file_ref} "
            "(see matlab_simulink_doc_suffixes).",
            f"{other}:1",
        )
    env.note_dependency(path)
    try:
        result, _sidecar = parse_file(directive, path, ref)
    except OSError as err:
        _warn("parse_error", f"{ref} cannot be read ({err.strerror or err}).")
        return None
    doc = _split(result)
    obj = mat_types.resolve(dom, file_ref)
    if isinstance(obj, mat_types.MatLibrary):
        keys = _block_keys(obj)
        for key, rubric, _body in doc.sections:
            if key not in keys:
                _warn(
                    "simulink",
                    f"{ref}: the heading {rubric.astext()!r} names no masked block "
                    f"of {file_ref}; its text goes with the library.",
                    f"{rubric.source}:{rubric.line}",
                )
        found = {key for key, _rubric, _body in doc.sections}
        missing = [repr(p) for k, p in keys.items() if k not in found]
        if missing:
            _warn(
                "simulink",
                f"{ref} has no section for the blocks {', '.join(missing)}.",
                f"{path}:1",
            )
    return doc


def _split(result):
    """Split the nodes of a documentation file into a ``_SimulinkDoc``: the
    first heading is the title (dropped); headings below it, and later ones
    at its level, start the sections.
    """
    first = next(
        (i for i, node in enumerate(result) if isinstance(node, nodes.section)),
        None,
    )
    if first is None:
        return _SimulinkDoc(result, [])
    text = list(result[:first])
    sections = []
    for child in [*result[first].children[1:], *result[first + 1 :]]:
        if isinstance(child, nodes.section):
            rubric = _rubric(child)
            key = _heading_key(rubric.astext())
            sections.append((key, rubric, _flat(child.children[1:])))
        else:
            text.append(child)
    return _SimulinkDoc(_flat(text), sections)


def _flat(children):
    """``children`` with each section as a rubric followed by its content."""
    out = []
    for node in children:
        if isinstance(node, nodes.section):
            out += [_rubric(node), *_flat(node.children[1:])]
        else:
            out.append(node)
    return out


def _rubric(section):
    title = section[0]
    rubric = nodes.rubric(title.rawsource, "", *title.children)
    rubric["ids"], rubric["names"] = section["ids"], section["names"]
    rubric.source, rubric.line = title.source, title.line
    return rubric
