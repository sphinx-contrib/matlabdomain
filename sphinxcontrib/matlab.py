"""sphinxcontrib.matlab.
~~~~~~~~~~~~~~~~~~~~

The MATLAB domain.

:copyright: Copyright by the sphinxcontrib-matlabdomain team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import re
import unicodedata

from docutils.parsers.rst import Directive, directives
from sphinx import addnodes
from sphinx.errors import ConfigError
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, Index, ObjType
from sphinx.locale import _ as translation
from sphinx.roles import XRefRole
from sphinx.util.docfields import Field, GroupedField, TypedField
from sphinx.util.logging import getLogger
from sphinx.util.nodes import make_refnode

from . import mat_api_check, mat_directives, mat_naming, mat_types
from . import mat_documenters as doc

logger = getLogger("matlab-domain")


# REs for MATLAB signatures: a MATLAB name or path reference, then optional
# arguments and return annotation.
mat_sig_re = re.compile(
    r"""^ (.+?) \s*                     # name
          (?: \(([^()]*)\)              # optional: arguments
           (?:\s* -> \s* (.*))?         #           return annotation
          )? $                          # and nothing more
          """,
    re.VERBOSE,
)


def _pseudo_parse_arglist(signode, arglist):
    """Parse a list of arguments separated by commas.

    Arguments can have "optional" annotations given by enclosing them in
    brackets.  Currently, this will split at any comma, even if it's inside a
    string literal (e.g. default argument value).
    """
    paramlist = addnodes.desc_parameterlist()
    stack = [paramlist]
    try:
        for argument in arglist.split(","):
            argument = argument.strip()
            ends_open = ends_close = 0
            while argument.startswith("["):
                stack.append(addnodes.desc_optional())
                stack[-2] += stack[-1]
                argument = argument[1:].strip()
            while argument.startswith("]"):
                stack.pop()
                argument = argument[1:].strip()
            while argument.endswith("]"):
                ends_close += 1
                argument = argument[:-1].strip()
            while argument.endswith("["):
                ends_open += 1
                argument = argument[:-1].strip()
            if argument:
                stack[-1] += addnodes.desc_parameter(argument, argument)
            while ends_open:
                stack.append(addnodes.desc_optional())
                stack[-2] += stack[-1]
                ends_open -= 1
            while ends_close:
                stack.pop()
                ends_close -= 1
        if len(stack) != 1:
            raise IndexError
    except IndexError:
        # if there are too few or too many elements on the stack, just give up
        # and treat the whole argument list as one argument, discarding the
        # already partially populated paramlist node
        signode += addnodes.desc_parameterlist()
        signode[-1] += addnodes.desc_parameter(arglist, arglist)
    else:
        signode += paramlist


class MatObject(ObjectDescription):
    """Description of a general MATLAB object."""

    option_spec = {
        "noindex": directives.flag,
        "no-index": directives.flag,
        "annotation": directives.unchanged,
        # Path reference of the object (written by the auto directives).
        "reference": directives.unchanged,
    }

    doc_field_types = [
        TypedField(
            "parameter",
            label=translation("Parameters"),
            names=(
                "param",
                "parameter",
                "arg",
                "argument",
                "keyword",
                "kwarg",
                "kwparam",
            ),
            typerolename="obj",
            typenames=("paramtype", "type"),
            can_collapse=True,
        ),
        TypedField(
            "variable",
            label=translation("Variables"),
            rolename="obj",
            names=("var", "ivar", "cvar"),
            typerolename="obj",
            typenames=("vartype",),
            can_collapse=True,
        ),
        GroupedField(
            "exceptions",
            label=translation("Raises"),
            # MATLAB errors are MException classes.
            rolename="class",
            names=("raises", "raise", "exception", "except"),
            can_collapse=True,
        ),
        Field(
            "returnvalue",
            label=translation("Returns"),
            has_arg=False,
            names=("returns", "return"),
        ),
        Field(
            "returntype",
            label=translation("Return type"),
            has_arg=False,
            names=("rtype",),
        ),
    ]

    def get_signature_prefix(self):
        """May return a prefix to put before the object name in the signature."""
        return ""

    def needs_arglist(self):
        """May return true if an empty argument list is to be generated even if
        the document contains none.
        """
        return False

    def handle_signature(self, sig, signode):
        """Transform a MATLAB signature into RST nodes.

        Return (path reference, display name). The display name is the
        MATLAB name (or the path reference of a file MATLAB cannot call).

        Inside a class, the class name is stripped from the displayed name
        and the member is registered below the class reference.
        """
        m = mat_sig_re.match(sig)
        if m is None:  # pragma: no cover - mat_sig_re matches any non-empty line
            raise ValueError
        name, arglist, retann = m.groups()

        cls = self.env.temp_data.get("mat:class")
        reference = self.options.get("reference")
        if cls:
            cls_ref, cls_display = cls
            if name.startswith(f"{cls_display}."):
                name = name[len(cls_display) + 1 :]
            ref = reference or f"{cls_ref}.{name}"
            display = f"{cls_display}.{name}"
            prefix, shown = mat_naming.split_display(name)
        else:
            if reference:
                ref, display = reference, name
            else:
                ref, display = self._source_reference(name)
            prefix, shown = mat_naming.split_display(display)
            if not self.env.config.add_module_names:
                prefix = ""

        signode["module"] = mat_naming.folder_of(ref)
        signode["class"] = cls[1] if cls else ""
        signode["fullname"] = display

        if sig_prefix := self.get_signature_prefix():
            signode += addnodes.desc_annotation(sig_prefix, sig_prefix)

        if prefix:
            signode += addnodes.desc_addname(prefix, prefix)

        anno = self.options.get("annotation")

        signode += addnodes.desc_name(shown, shown)
        if not arglist:
            if self.needs_arglist():
                # for callables, add an empty parameter list
                signode += addnodes.desc_parameterlist()
            if retann:
                signode += addnodes.desc_returns(retann, retann)
            if anno:
                signode += addnodes.desc_annotation(f" {anno}", f" {anno}")
            return ref, display

        _pseudo_parse_arglist(signode, arglist)
        if retann:
            signode += addnodes.desc_returns(retann, retann)
        if anno:
            signode += addnodes.desc_annotation(f" {anno}", f" {anno}")
        return ref, display

    def _source_reference(self, name):
        # A directive written by hand: use the source file it names, if any.
        dom = self.env.get_domain("mat")
        folder = self.env.temp_data.get("mat:folder")
        found = mat_types.find_source(dom, name, folder)
        if len(found) == 1:
            ref = found[0][0]
            return ref, mat_types.display_name(dom, ref)
        if found:
            logger.warning(
                "[sphinxcontrib-matlabdomain] %r matches several objects: %s; "
                "use a path reference",
                name,
                ", ".join(sorted(ref for ref, _ in found)),
                type="mat",
                subtype="ambiguous",
                location=(self.env.docname, self.lineno),
            )
        return (mat_naming.join_reference(folder, name) if folder else name), name

    def get_index_text(self, folder, name_cls):  # pragma: no cover - abstract
        """Return the text for the index entry of the object."""
        raise NotImplementedError("must be implemented in subclasses")

    @staticmethod
    def _is_same_object(node, fullname):
        return isinstance(node, addnodes.desc_signature) and fullname in node["names"]

    def add_target_and_index(self, name_cls, sig, signode):  # noqa: ARG002 - required by Sphinx API
        ref, display = name_cls
        target_id = mat_naming.make_target_id(ref)

        # note target
        if target_id not in self.state.document.ids:
            signode["names"].append(ref)
            signode["ids"].append(target_id)
            signode["first"] = not self.names
            self.state.document.note_explicit_target(signode)
            self.env.get_domain("mat").note_object(
                ref, self.objtype, display, location=(self.env.docname, self.lineno)
            )
        elif not self._is_same_object(self.state.document.ids[target_id], ref):
            logger.warning(
                "[sphinxcontrib-matlabdomain] %s and %s share the target id %r; "
                "%s is not linkable",
                ref,
                ", ".join(self.state.document.ids[target_id]["names"]) or "?",
                target_id,
                ref,
                location=(self.env.docname, self.lineno),
            )

        if indextext := self.get_index_text(mat_naming.folder_of(ref), name_cls):
            entry = ("single", indextext, target_id, "", None)
            self.indexnode["entries"].append(entry)

    def before_content(self):
        # needed for automatic qualification of members (reset in subclasses)
        self.clsname_set = False
        # Cross-references in the content resolve relative to the object's folder.
        self.previous_objfolder = self.env.temp_data.get("mat:objfolder")
        if self.names:
            self.env.temp_data["mat:objfolder"] = mat_naming.folder_of(
                self.names[0][0]
            )

    def after_content(self):
        if self.clsname_set:
            self.env.temp_data["mat:class"] = None
        self.env.temp_data["mat:objfolder"] = self.previous_objfolder


class MatModulelevel(MatObject):
    """Description of an object on folder level (functions, data, application)."""

    def needs_arglist(self):
        return self.objtype == "function"

    def get_index_text(self, folder, name_cls):
        if self.objtype == "function":
            return translation("%s() (function in %s)") % (name_cls[1], folder)
        elif self.objtype == "data":
            return translation("%s (data in %s)") % (name_cls[1], folder)
        elif self.objtype == "application":
            return translation("%s (application in %s)") % (name_cls[1], folder)
        else:
            return ""


class MatClasslike(MatObject):
    """Description of a class."""

    def _object_hierarchy_parts(self, sig):
        """Return a tuple of strings, one entry for each part of the object's \
           hierarchy (e.g. ``('package', 'Class')``).

        The returned tuple is used to properly nest children within parents in the
        table of contents, and can also be used within the
        :py:meth:`_toc_entry_name` method.

        This method must not be used without table of contents generation.
        """
        return tuple(sig.attributes.get("fullname").split("."))

    def _toc_entry_name(self, sig):
        # TODO respecting the configuration setting ``toc_object_entries_show_parents``
        return mat_naming.split_display(sig.attributes.get("fullname"))[1]

    def get_signature_prefix(self):
        return f"{self.objtype} "

    def get_index_text(self, folder, name_cls):
        return translation("%s (class in %s)") % (name_cls[1], folder)

    def before_content(self):
        MatObject.before_content(self)
        # A class signature always parses (mat_sig_re matches any line).
        if self.names:  # pragma: no branch
            self.env.temp_data["mat:class"] = self.names[0]
            self.clsname_set = True


class MatClassmember(MatObject):
    """Description of a class member (methods, attributes)."""

    def needs_arglist(self):
        return self.objtype.endswith("method")

    def get_signature_prefix(self):
        if self.objtype == "staticmethod":
            return "static "
        elif self.objtype == "classmethod":
            return "classmethod "
        return ""

    def get_index_text(self, folder, name_cls):  # noqa: ARG002
        name = name_cls[1]
        kind = {
            "method": translation("%s() (%s method)"),
            "staticmethod": translation("%s() (%s static method)"),
            "classmethod": translation("%s() (%s class method)"),
            "attribute": translation("%s (%s attribute)"),
        }[self.objtype]
        clsname, _, member = name.rpartition(".")
        if not clsname:
            return f"{name}()" if self.objtype.endswith("method") else name
        return kind % (member, clsname)

    def before_content(self):
        MatObject.before_content(self)
        if self.names and not self.env.temp_data.get("mat:class"):
            ref, display = self.names[-1]
            if "." in display:
                cls = (ref.rpartition(".")[0], display.rpartition(".")[0])
                self.env.temp_data["mat:class"] = cls
                self.clsname_set = True


class MatFolder(MatObject):
    """Description of a folder.

    A valid ``+`` folder shows ``namespace <MATLAB name>``; any other folder
    shows ``folder <path reference>``. ``@Class`` folders are documented
    through their class. Sets the current folder like ``mat:currentfolder``.
    """

    option_spec = {
        "platform": lambda x: x,
        "synopsis": lambda x: x,
        "noindex": directives.flag,
        "no-index": directives.flag,
        "deprecated": directives.flag,
    }

    def handle_signature(self, sig, signode):
        dom = self.env.get_domain("mat")
        ref = mat_types.folder_reference(
            dom, sig, location=(self.env.docname, self.lineno)
        )
        if ref.rstrip("/").rpartition("/")[2].startswith("@"):
            logger.warning(
                "[sphinxcontrib-matlabdomain] %s is a class folder; "
                "document its class instead",
                ref,
                location=(self.env.docname, self.lineno),
            )
            raise ValueError
        entity = dom.entities_table.get(ref)
        if entity is not None:
            namespace = getattr(entity, "matlab_name", None)
        elif ref != mat_naming.ROOT_REFERENCE:
            namespace = mat_naming.folder_namespace(
                ref.rstrip("/"),
                self.env.config.matlab_namelengthmax,
                self.env.config.matlab_version,
            )
        else:
            namespace = None
        kind, display = ("namespace", namespace) if namespace else ("folder", ref)

        signode["module"] = ref
        signode["class"] = ""
        signode["fullname"] = display
        signode += addnodes.desc_annotation(f"{kind} ", f"{kind} ")
        signode += addnodes.desc_name(display, display)
        return ref, display

    def get_index_text(self, folder, name_cls):  # noqa: ARG002
        ref, display = name_cls
        if display == ref:
            return translation("%s (folder)") % display
        return translation("%s (namespace)") % display

    def add_target_and_index(self, name_cls, sig, signode):  # noqa: ARG002 - required by Sphinx API
        ref, display = name_cls
        target_id = mat_naming.make_target_id(ref)
        if target_id not in self.state.document.ids:
            signode["names"].append(ref)
            signode["ids"].append(target_id)
            signode["first"] = not self.names
            self.state.document.note_explicit_target(signode)
        # Like the former module directive, a folder may be described on
        # several pages without a duplicate warning; the last one wins.
        dom = self.env.get_domain("mat")
        dom.note_object(ref, self.objtype, display)
        dom.data["folders"][ref] = (
            self.env.docname,
            self.options.get("synopsis", ""),
            self.options.get("platform", ""),
            "deprecated" in self.options,
        )
        entry = ("single", self.get_index_text(ref, name_cls), target_id, "", None)
        self.indexnode["entries"].append(entry)

    def run(self):
        result = super().run()
        if self.names:
            folder = self.names[0][0]
        else:
            folder = mat_types.folder_reference(
                self.env.get_domain("mat"), self.arguments[0]
            )
        self.env.temp_data["mat:folder"] = folder
        return result


class MatCurrentFolder(Directive):
    """Set the current folder for relative references without documenting it.

    ``None`` clears it; ``.`` is the project root.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {}

    def run(self):
        env = self.state.document.settings.env
        folder = self.arguments[0].strip()
        env.temp_data["mat:folder"] = (
            None
            if folder == "None"
            else mat_types.folder_reference(
                env.get_domain("mat"), folder, location=(env.docname, self.lineno)
            )
        )
        return []


def _short_title(title):
    # Last part of a MATLAB name or path reference (``~`` in a role).
    parens = "()" if title.endswith("()") else ""
    title = title.removesuffix(parens)
    file, members = mat_naming.parse_reference(title)
    if members:
        title = members[-1]
    elif file is not None:
        title = file.rstrip("/").rpartition("/")[2] or file
    else:
        title = title.rpartition(".")[2]
    return title + parens


class MatXRefRole(XRefRole):
    def process_link(self, env, refnode, has_explicit_title, title, target):
        refnode["mat:folder"] = env.temp_data.get("mat:objfolder") or env.temp_data.get(
            "mat:folder"
        )
        cls = env.temp_data.get("mat:class")
        refnode["mat:class"] = cls[0] if cls else None
        # A leading dot (except in the root folder "." or "./") searches by
        # suffix.
        specific = target[:1] == "." and target != "." and target[:2] != "./"
        if not has_explicit_title:
            if title != "." and not title.startswith("./"):
                title = title.lstrip(".")  # only has a meaning for the target
            target = target.lstrip("~")  # only has a meaning for the title
            # if the first character is a tilde, only display the last part
            if title[:1] == "~":
                title = _short_title(title[1:])

        if specific:
            target = target[1:]
            refnode["refspecific"] = True
        return title, target


class MATLABFolderIndex(Index):
    """Index subclass to provide the MATLAB folder index."""

    name = "folderindex"
    localname = translation("MATLAB Folder Index")
    shortname = translation("folder index")

    def generate(self, docnames=None):
        content = {}
        objects = self.domain.data["objects"]
        folders = sorted(
            self.domain.data["folders"].items(), key=lambda x: x[0].lower()
        )
        for ref, (docname, synopsis, platforms, deprecated) in folders:
            if docnames and docname not in docnames:
                continue
            display = objects.get(ref, (docname, "folder", ref))[2]
            qualifier = (deprecated and translation("Deprecated")) or ""
            content.setdefault(display[0].lower(), []).append(
                [
                    display,
                    0,
                    docname,
                    mat_naming.make_target_id(ref),
                    platforms,
                    qualifier,
                    synopsis,
                ]
            )
        return sorted(content.items()), False


class MATLABDomain(Domain):
    """MATLAB language domain."""

    name = "mat"
    label = "MATLAB"
    object_types = {
        "function": ObjType(translation("function"), "func", "obj"),
        "data": ObjType(translation("data"), "data", "obj"),
        "class": ObjType(translation("class"), "class", "obj"),
        "method": ObjType(translation("method"), "meth", "obj"),
        "classmethod": ObjType(translation("class method"), "meth", "obj"),
        "staticmethod": ObjType(translation("static method"), "meth", "obj"),
        "attribute": ObjType(translation("attribute"), "attr", "obj"),
        "folder": ObjType(translation("folder"), "folder", "obj"),
        "script": ObjType(translation("script"), "scpt", "obj"),
        "application": ObjType(translation("application"), "app", "obj"),
    }

    directives = {
        "function": MatModulelevel,
        "data": MatModulelevel,
        "class": MatClasslike,
        "method": MatClassmember,
        "classmethod": MatClassmember,
        "staticmethod": MatClassmember,
        "attribute": MatClassmember,
        "folder": MatFolder,
        "currentfolder": MatCurrentFolder,
        "script": MatModulelevel,
        "application": MatModulelevel,
    }
    roles = {
        "data": MatXRefRole(),
        "func": MatXRefRole(fix_parens=True),
        "class": MatXRefRole(),
        "const": MatXRefRole(),
        "attr": MatXRefRole(),
        "enum": MatXRefRole(),
        "meth": MatXRefRole(fix_parens=True),
        "folder": MatXRefRole(),
        "obj": MatXRefRole(),
        "scpt": MatXRefRole(),
        "app": MatXRefRole(),
    }
    initial_data = {
        # Per-document registrations (cleared/merged by docname).
        "objects": {},  # path reference -> docname, objtype, display name
        "folders": {},  # folder reference -> docname, synopsis, platform, deprecated
        "doc_sources": {},  # docname -> {source path: (mtime_ns, size)} it used
        # Shared source state, rebuilt by ``mat_types.analyze`` each build;
        # files are parsed lazily (see ``mat_types``).
        # source path -> {reference, type, mtime, size, warnings, unreadable,
        #                 matlab_name, private, scope}
        "index": {},
        "parse_cache": {},  # (path, mtime_ns, size) -> parsed MatObject
        "parse_warnings": {},  # (path, mtime_ns, size) -> parse-stage warnings
        "entities_table": {},  # path reference -> MatObject (files and folders)
        "matlab_names": {},  # MATLAB name -> path references
    }
    # Bump when the layout of ``initial_data`` (the pickled domain data) or the
    # parsed objects it caches change, so Sphinx drops stale cached environments.
    data_version = 14
    indices = [
        MATLABFolderIndex,
    ]

    def __init__(self, env):
        super().__init__(env)
        # display name -> references of documented objects (built lazily)
        self._displays = None
        # Documents read in this build (``env-before-read-docs``).
        self.read_docnames = ()
        self.reset_sources()

    def reset_sources(self):
        """Forget the in-process state of the previous index stage."""
        # path reference -> source path (built lazily from the index)
        self._sources = None
        # (path, mtime_ns, size) -> decoded text read by the index stage
        self.text_cache = {}
        # files or folders were added, removed or changed type
        self.index_changed = False

    def source_paths(self):
        """Path reference -> source path of every indexed file."""
        if self._sources is None:
            self._sources = {
                record["reference"]: path for path, record in self.data["index"].items()
            }
        return self._sources

    @property
    def entities_table(self):
        return self.data["entities_table"]

    def note_object(self, name, objtype, display=None, location=None):
        """Register a documented object (``name`` is its path reference).

        Warns on duplicates only when ``location`` is given.
        """
        objects = self.data["objects"]
        if name in objects and location is not None:
            logger.warning(
                "duplicate object description of %s, other instance in %s, "
                "use :noindex: for one of them",
                name,
                self.env.doc2path(objects[name][0]),
                location=location,
            )
        objects[name] = (self.env.docname, objtype, display or name)
        self._displays = None

    def clear_doc(self, docname):
        for ref, (fn, _, _) in list(self.data["objects"].items()):
            if fn == docname:
                del self.data["objects"][ref]
        for ref, (fn, _, _, _) in list(self.data["folders"].items()):
            if fn == docname:
                del self.data["folders"][ref]
        self.data["doc_sources"].pop(docname, None)
        self._displays = None

    def merge_domaindata(self, docnames, otherdata):
        # Merge per-document registrations from a parallel-read worker, and
        # the files it parsed, so the next build need not parse them again.
        # The index and the entities are built in the main process.
        for ref, data in otherdata["objects"].items():
            if data[0] in docnames:
                self.data["objects"][ref] = data
        for ref, data in otherdata["folders"].items():
            if data[0] in docnames:
                self.data["folders"][ref] = data
        for docname, used in otherdata["doc_sources"].items():
            if docname in docnames:
                self.data["doc_sources"][docname] = used
        index = self.data["index"]
        for name in ("parse_cache", "parse_warnings"):
            ours = self.data[name]
            for key, value in otherdata[name].items():
                record = index.get(key[0])
                if record is None or (record["mtime"], record["size"]) != key[1:]:
                    continue
                ours.setdefault(key, value)
        self._displays = None

    def _by_display(self, name):
        if self._displays is None:
            self._displays = {}
            for ref, (_, _, display) in self.data["objects"].items():
                self._displays.setdefault(display, []).append(ref)
        return self._displays.get(name, [])

    def _scope(self, reference):
        # Folder a documented object's MATLAB name is visible from.
        return mat_types.source_scope(self, reference)

    def find_obj(self, folder, cls, name, type, searchmode=0):
        """Find documented objects for ``name`` (plan.md Section 2.3).

        1. exact path reference; 2. relative to the class ``cls`` and the
        folder ``folder`` (a path below it or a MATLAB name visible from it,
        including its ``private/``); 3. a MATLAB name, excluding private
        files; 4. a folder path without its trailing ``/``. With
        ``searchmode`` 1 (``.name``), a non-private MATLAB-name suffix as last
        resort. Return a list of (reference, object entry) tuples; several
        entries mean the name is ambiguous.
        """
        if name[-2:] == "()":  # skip parens
            name = name[:-2]

        if not name:
            return []

        name = unicodedata.normalize("NFC", name)
        objects = self.data["objects"]
        objtypes = self.objtypes_for_role(type) if type else None

        if name == ".":
            name = mat_naming.ROOT_REFERENCE
        exact = [name]
        if cls:
            exact.append(f"{cls}.{name}")
        if folder:
            exact.append(mat_naming.join_reference(folder, name))
        # (candidates, first only): exact references are tried in order.
        steps = [([r for r in exact if r in objects], True)]
        if folder:
            steps.append(
                ([r for r in self._by_display(name) if self._scope(r) == folder], False)
            )
        steps.append(
            (
                [
                    r
                    for r in self._by_display(name)
                    if not mat_naming.is_private_reference(r)
                ],
                False,
            )
        )
        if not name.endswith("/"):
            folders = [f"{name}/"]
            if folder:
                folders.append(f"{mat_naming.join_reference(folder, name)}/")
            steps.append(([r for r in folders if r in objects], True))
        # Objects of the role's type first (``:class:`C``` inside class C is the
        # class, not its constructor), then any type.
        for typed in (True, False) if objtypes is not None else (False,):
            for refs, first_only in steps:
                if typed:
                    refs = [r for r in refs if objects[r][1] in objtypes]
                refs = list(dict.fromkeys(refs))[: 1 if first_only else None]
                if refs:
                    return [(r, objects[r]) for r in refs]
        if searchmode == 1:
            return [
                (ref, entry)
                for ref, entry in objects.items()
                if entry[2].endswith(f".{name}")
                and (objtypes is None or entry[1] in objtypes)
                and not mat_naming.is_private_reference(ref)
            ]
        return []

    def _refnode(self, builder, fromdocname, ref, entry, contnode):
        docname, objtype, title = entry
        if objtype == "folder" and ref in self.data["folders"]:
            _, synopsis, platform, deprecated = self.data["folders"][ref]
            if synopsis:
                title += f": {synopsis}"
            if deprecated:
                title += translation(" (deprecated)")
            if platform:
                title += f" ({platform})"
        return make_refnode(
            builder,
            fromdocname,
            docname,
            mat_naming.make_target_id(ref),
            contnode,
            title,
        )

    def resolve_xref(self, env, fromdocname, builder, type, target, node, contnode):  # noqa: ARG002 - required by Sphinx API
        searchmode = (node.hasattr("refspecific") and 1) or 0
        matches = self.find_obj(
            node.get("mat:folder"), node.get("mat:class"), target, type, searchmode
        )
        if not matches:
            return None
        if len(matches) > 1:
            self._warn_ambiguous(target, matches, node)
            # Unlinked, without a second "target not found" warning.
            return contnode
        ref, entry = matches[0]
        return self._refnode(builder, fromdocname, ref, entry, contnode)

    @staticmethod
    def _warn_ambiguous(target, matches, node):
        logger.warning(
            "[sphinxcontrib-matlabdomain] %r matches several objects: %s; "
            "use a path reference",
            target,
            ", ".join(sorted(match[0] for match in matches)),
            type="mat",
            subtype="ambiguous",
            location=node,
        )

    def get_objects(self):
        for ref, (docname, objtype, display) in self.data["objects"].items():
            yield (
                ref,
                display,
                objtype,
                docname,
                mat_naming.make_target_id(ref),
                0 if objtype == "folder" else 1,
            )

    def resolve_any_xref(self, env, fromdocname, builder, target, node, contnode):  # noqa: ARG002 - required by Sphinx API
        searchmode = (node.hasattr("refspecific") and 1) or 0
        matches = self.find_obj(
            node.get("mat:folder"), node.get("mat:class"), target, None, searchmode
        )
        if len(matches) > 1:
            self._warn_ambiguous(target, matches, node)
            role = self.role_for_objtype(matches[0][1][1])
            return [(f"mat:{role}", contnode)]
        return [
            (
                f"mat:{self.role_for_objtype(entry[1])}",
                self._refnode(builder, fromdocname, ref, entry, contnode),
            )
            for ref, entry in matches
        ]


def analyze(app):
    mat_types.analyze(app)


_REMOVED_OPTIONS = {
    "matlab_src_dir": (
        "use matlab_src_code_project_root (relative to the Sphinx source "
        "directory) and, to select files, matlab_src_include_patterns and "
        "matlab_src_exclusion_patterns"
    ),
    "matlab_keep_package_prefix": (
        "objects are referenced by path (which keeps '+') and signatures show "
        "MATLAB names (without '+')"
    ),
    "matlab_short_links": "signatures show MATLAB names by default",
}


def ensure_configuration(app, config):
    for name, reason in _REMOVED_OPTIONS.items():
        if getattr(config, name) is not None:
            raise ConfigError(
                f"{name} was removed: {reason}. Remove it from conf.py."
            )

    sources = mat_types.source_filter(config)
    if config.matlab_src_code_project_root is not None:
        root = mat_types.project_root(config, app.srcdir)
        mat_types.check_pattern_folders(sources, root)

    # Explicit matlab_namelengthmax wins; None derives it from matlab_version.
    try:
        config.matlab_namelengthmax = mat_naming.resolve_namelengthmax(
            config.matlab_version, config.matlab_namelengthmax
        )
    except ValueError as err:
        raise ConfigError(str(err)) from err


def check_encoding(app, config):  # noqa: ARG001
    if config.matlab_src_encoding is not None:
        try:
            # not b"".decode(): it skips the check for non-text codecs (rot13)
            "a".encode(config.matlab_src_encoding)
        except (LookupError, TypeError) as err:
            raise ConfigError(
                f"matlab_src_encoding {config.matlab_src_encoding!r} is not a "
                "known text encoding."
            ) from err


def _get_version():
    try:
        from importlib.metadata import version

        return version("sphinxcontrib-matlabdomain")
    except Exception:
        return "0.0.0"


def setup(app):
    # The mat:auto* directives read autodoc's config values.
    app.setup_extension("sphinx.ext.autodoc")
    app.connect("config-inited", ensure_configuration)
    app.connect("config-inited", check_encoding)
    app.connect("config-inited", mat_api_check.check_config)
    app.connect("builder-inited", analyze)
    app.connect("env-get-outdated", mat_types.outdated_docs)
    app.connect("env-before-read-docs", mat_types.note_read_docs)
    app.connect("env-updated", mat_types.warn_parsed_sources)
    app.connect("build-finished", mat_api_check.set_status)

    app.add_domain(MATLABDomain)
    app.add_builder(mat_api_check.MatlabApiCheckBuilder)
    # autodoc
    # Relative paths are relative to the Sphinx source directory.
    app.add_config_value("matlab_src_code_project_root", None, "env")
    # Globs relative to matlab_src_code_project_root; [] selects no files.
    app.add_config_value(
        "matlab_src_include_patterns",
        list(mat_types.DEFAULT_INCLUDE_PATTERNS),
        "env",
        [list, tuple],
    )
    app.add_config_value("matlab_src_exclusion_patterns", [], "env", [list, tuple])
    # Keep the text read by the index stage for the parse (this process only).
    app.add_config_value("matlab_src_cache_text", True, "", bool)
    # Removed: setting it raises ConfigError.
    app.add_config_value("matlab_src_dir", None, "env")
    app.add_config_value("matlab_src_encoding", None, "env")
    # Removed: setting it raises ConfigError.
    app.add_config_value("matlab_keep_package_prefix", None, "env")
    app.add_config_value("matlab_show_property_default_value", False, "env")
    app.add_config_value("matlab_show_property_specs", False, "env")
    # Removed: setting it raises ConfigError.
    app.add_config_value("matlab_short_links", None, "env")
    app.add_config_value("matlab_auto_link", None, "env")
    app.add_config_value("matlab_class_signature", False, "env")
    app.add_config_value("matlab_version", mat_naming.DEFAULT_MATLAB_VERSION, "env")
    # None: derived from matlab_version (2048 from R2025a on).
    app.add_config_value("matlab_namelengthmax", None, "env")
    # matlab-api-check: read by the builder only, so no page is read again.
    app.add_config_value("matlab_api_check_enabled", True, "", bool)
    # Rule -> severity, merged over mat_api_check.DEFAULT_RULES.
    app.add_config_value("matlab_api_check_rules", {}, "", dict)
    app.add_config_value("matlab_api_check_ignore_patterns", [], "", [list, tuple])

    app.registry.add_documenter("mat:folder", doc.MatFolderDocumenter)
    app.add_directive_to_domain(
        "mat", "autofolder", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:function", doc.MatFunctionDocumenter)
    app.add_directive_to_domain(
        "mat", "autofunction", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:class", doc.MatClassDocumenter)
    app.add_directive_to_domain(
        "mat", "autoclass", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:method", doc.MatMethodDocumenter)
    app.add_directive_to_domain(
        "mat", "automethod", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:script", doc.MatScriptDocumenter)
    app.add_directive_to_domain(
        "mat", "autoscript", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:attribute", doc.MatAttributeDocumenter)
    app.add_directive_to_domain(
        "mat", "autoattribute", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:enum", doc.MatAttributeDocumenter)
    app.add_directive_to_domain(
        "mat", "autoenum", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:data", doc.MatDataDocumenter)
    app.add_directive_to_domain(
        "mat", "autodata", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:application", doc.MatApplicationDocumenter)
    app.add_directive_to_domain(
        "mat", "autoapplication", mat_directives.MatlabAutodocDirective
    )

    app.add_autodoc_attrgetter(mat_types.MatModule, mat_types.MatModule.getter)
    app.add_autodoc_attrgetter(doc.MatClass, doc.MatClass.getter)

    return {
        "version": _get_version(),
        # Workers parse lazily; merge_domaindata collects what they parsed.
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
