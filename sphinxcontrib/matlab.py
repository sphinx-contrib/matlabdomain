"""sphinxcontrib.matlab.
~~~~~~~~~~~~~~~~~~~~

The MATLAB domain.

:copyright: Copyright by the sphinxcontrib-matlabdomain team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import functools
import itertools
import json
import re
import unicodedata
from typing import cast

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from sphinx import addnodes
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, Index, ObjType
from sphinx.errors import ConfigError
from sphinx.locale import _ as translation
from sphinx.roles import XRefRole
from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx.util.docfields import Field, GroupedField, TypedField
from sphinx.util.logging import getLogger
from sphinx.util.nodes import make_refnode

from . import (
    mat_api_check,
    mat_config,
    mat_directives,
    mat_naming,
    mat_sidecars,
    mat_types,
    mat_urls,
)
from . import mat_documenters as doc

# Public: a conf.py extends it (matlab_external_names = [*DEFAULT_EXTERNAL_NAMES, ...]).
from .mat_config import DEFAULT_EXTERNAL_NAMES as DEFAULT_EXTERNAL_NAMES
from .mat_simulink import _linker as simulink_linker

logger = getLogger("matlab-domain")


class MatTypedField(TypedField):
    """A typed field whose types link when documented and are text otherwise.

    MATLAB types in help (``double``, ``(1,1) string``) are rarely documented
    objects, so an unresolved type gives no "target not found" warning.
    """

    def make_xref(
        self,
        rolename,
        domain,
        target,
        innernode=addnodes.literal_emphasis,
        *args,
        **kwargs,
    ):
        is_type = innernode is addnodes.literal_emphasis
        node = super().make_xref(rolename, domain, target, innernode, *args, **kwargs)
        if is_type:
            for xref in node.findall(addnodes.pending_xref):
                xref["mat:type"] = True
        return node


def keep_unresolved_references(app, env, node, contnode):
    # Runs after intersphinx (priority 900), so other projects' names still link.
    if node.get("refdomain") != "mat":
        return None
    external = _external_names(tuple(app.config.matlab_external_names))
    if (
        node.get("mat:type")
        or node.get("mat:ambiguous")
        or external.fullmatch(node.get("reftarget", ""))
        or _outside_simulink_file(env, node)
    ):
        return contnode
    return None


def _outside_simulink_file(env, node):
    """Return True for a Simulink role whose target names no Simulink file of
    the project (a MathWorks library such as ``simulink/Sources``).
    """
    if node.get("reftype") not in SIMULINK_LABELS:
        return False
    target = node.get("reftarget", "")
    file, _ = mat_naming.parse_reference(target)
    if file and mat_naming.is_block_container(file.rpartition("/")[2]):
        return False  # a path reference
    refs = env.get_domain("mat").data["matlab_names"].get(target.split("/", 1)[0], ())
    return not any(
        mat_naming.is_block_container(ref.rpartition("/")[2]) for ref in refs
    )


def check_inventories(app, env, node, contnode):
    """``missing-reference``, before intersphinx: a reference that several
    inventories have at different addresses stays unlinked with a
    ``mat.ambiguous`` warning (intersphinx would pick one of them). So does
    a MATLAB name of several objects of one inventory (its chooser page)
    unless ``matlab_link_shadowed_files_to_chooser_pages`` accepts them.
    """
    if node.get("refdomain") != "mat" or "sphinx.ext.intersphinx" not in app.extensions:
        return None
    return _check_inventories(env, node, contnode)


class CheckExternalReferences(SphinxPostTransform):
    """``check_inventories`` for the ``:external:`` roles, which intersphinx
    resolves before the ``missing-reference`` event.
    """

    default_priority = 8  # before intersphinx's IntersphinxRoleResolver (9)

    def run(self, **kwargs):  # noqa: ARG002
        for node in list(self.document.findall(addnodes.pending_xref)):
            if "intersphinx" in node and node.get("refdomain") == "mat":
                contnode = node[0].deepcopy()
                if _check_inventories(self.env, node, contnode) is not None:
                    node.replace_self(contnode)


def _check_inventories(env, node, contnode):
    from sphinx.ext.intersphinx import InventoryAdapter

    inventories = InventoryAdapter(env).named_inventory
    target = node["reftarget"]
    named = node.get("inventory")
    prefix, colon, rest = target.partition(":")
    if named is None and colon and prefix in inventories:
        named, target = prefix, rest
    names = [named] if named is not None else sorted(inventories)
    objtypes = env.get_domain("mat").objtypes_for_role(node["reftype"]) or ()
    found = {}
    for name in names:
        for objtype in objtypes:
            item = inventories.get(name, {}).get(f"mat:{objtype}", {}).get(target)
            if item is not None:
                # Sphinx < 8.2: (project, version, uri, display name)
                found.setdefault(getattr(item, "uri", None) or item[2], name)
    if len(found) > 1:
        node["mat:ambiguous"] = True
        labels = [f"{name}:{target}" for name in found.values()]
        mat_types.warn_ambiguous(target, labels, node, "write one of them")
        return contnode
    if not found:
        return None
    uri, found_in = next(iter(found.items()))
    if (
        env.config.matlab_link_shadowed_files_to_chooser_pages
        or not mat_urls.is_chooser_uri(uri)
    ):
        return None
    refs = {
        ref
        for objtype in objtypes
        for ref, item in inventories[found_in].get(f"mat:{objtype}", {}).items()
        # Sphinx < 8.2: (project, version, uri, display name)
        if ref != target
        and (getattr(item, "display_name", None) or item[3]) == target
        and not mat_naming.is_private_reference(ref)
    }
    prefix = "" if len(names) == 1 else f"{found_in}:"
    node["mat:ambiguous"] = True
    mat_types.warn_ambiguous(target, [prefix + ref for ref in refs], node)
    return contnode


@functools.cache
def _external_names(patterns):
    # (?!) matches nothing: no patterns.
    return re.compile("|".join(f"(?:{p})" for p in patterns) or "(?!)")


def check_external_names(app, config):  # noqa: ARG001
    names = config.matlab_external_names
    if isinstance(names, str) or not isinstance(names, (list, tuple)):
        raise ConfigError(f"matlab_external_names must be a list, not {names!r}.")
    for pattern in names:
        if not isinstance(pattern, str):
            raise ConfigError(f"matlab_external_names: {pattern!r} must be a str.")
        try:
            re.compile(pattern)
        except re.error as err:
            raise ConfigError(
                f"matlab_external_names: {pattern!r} is not a regular "
                f"expression ({err})."
            ) from err


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
    stack: list[nodes.Element] = [paramlist]
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


class MatObjectDirective(ObjectDescription):
    """Description of a general MATLAB object."""

    option_spec = {
        "noindex": directives.flag,
        "no-index": directives.flag,
        "annotation": directives.unchanged,
        # Path reference of the object (written by the auto directives).
        "reference": directives.unchanged,
    }

    doc_field_types = [
        MatTypedField(
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
        MatTypedField(
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

    def flag_prefix(self):
        """Return the attribute flags given as options (``:abstract:``) as a prefix."""
        return "".join(f"{flag} " for flag in self.flags if flag in self.options)

    #: attribute flag options, in the order of the signature prefix
    flags: tuple[str, ...] = ()

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
            if not self.env.config.matlab_add_namespace_names:
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

    def _source_reference(self, name, accept=mat_types.is_code_object):
        # A directive written by hand: use the source file it names, if any.
        dom = self.env.get_domain("mat")
        folder = self.env.temp_data.get("mat:folder")
        location = (self.env.docname, self.lineno)
        found = mat_types.find_one(dom, name, folder, accept, location)
        if found:
            return found[0], mat_types.display_name(dom, found[0])
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
            cast(MATLABDomain, self.env.get_domain("mat")).note_object(
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
                type="mat",
                subtype="duplicate",
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
            self.env.temp_data["mat:objfolder"] = mat_naming.folder_of(self.names[0][0])

    def after_content(self):
        if self.clsname_set:
            self.env.temp_data["mat:class"] = None
        self.env.temp_data["mat:objfolder"] = self.previous_objfolder


class MatModulelevel(MatObjectDirective):
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


class MatSimulinkObject(MatObjectDirective):
    """Description of a Simulink model, library, subsystem file or library
    block. The signature is its name as Simulink shows it, without
    arguments; a ``:reference:`` with a newline is written as JSON text.
    """

    doc_field_types = [
        *MatObjectDirective.doc_field_types,
        TypedField(
            "maskparameter",
            label=translation("Mask parameters"),
            names=("maskparam",),
            typenames=("maskparamtype",),
            can_collapse=True,
        ),
    ]

    def handle_signature(self, sig, signode):
        sig = sig.strip()
        reference = self.options.get("reference")
        if reference:
            ref = json.loads(reference) if reference[:1] == '"' else reference
            display = sig
        else:
            accept = mat_types.simulink_accepts(
                mat_types.SIMULINK_CLASSES[self.objtype]
            )
            ref, display = self._source_reference(sig, accept)
            display = display.replace("\n", " ")
        _, members = mat_naming.parse_reference(ref)
        shown = members[0].replace("\n", " ") if members else ""
        if shown and display.endswith(shown) and len(display) > len(shown):
            prefix, shown = display[: -len(shown)], shown
        else:
            prefix, shown = mat_naming.split_display(display)

        signode["module"] = mat_naming.folder_of(ref)
        signode["class"] = ""
        signode["fullname"] = display
        label = f"{SIMULINK_LABELS[self.objtype]} "
        signode += addnodes.desc_annotation(label, label)
        if prefix:
            signode += addnodes.desc_addname(prefix, prefix)
        signode += addnodes.desc_name(shown, shown)
        return ref, display

    def transform_content(self, content_node):
        """Put the Simulink documentation file where the autodoc directive's
        placeholder comment is.
        """
        super().transform_content(content_node)
        for node in content_node.children:
            if (
                isinstance(node, nodes.comment)
                and node.astext() == doc.SIMULINK_DOC_PLACEHOLDER
            ):
                found = []
                if self.names:  # pragma: no branch - autodoc gives a reference
                    ref = self.names[0][0]
                    found = mat_sidecars.simulink_documentation(self, ref)
                content_node.replace(node, found)
                return

    def get_index_text(self, folder, name_cls):
        return translation("%s (%s in %s)") % (
            name_cls[1],
            SIMULINK_LABELS[self.objtype],
            folder,
        )


#: object type -> what its signature calls it
SIMULINK_LABELS = {
    "simulink_model": translation("Simulink model"),
    "simulink_library": translation("Simulink library"),
    "simulink_subsystem_reference": translation("Simulink subsystem reference"),
    "simulink_library_block": translation("Simulink library block"),
}


class MatClasslike(MatObjectDirective):
    """Description of a class."""

    flags = ("abstract", "sealed")
    option_spec = {
        **MatObjectDirective.option_spec,
        **dict.fromkeys(flags, directives.flag),
    }

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
        return f"{self.flag_prefix()}{self.objtype} "

    def get_index_text(self, folder, name_cls):
        return translation("%s (class in %s)") % (name_cls[1], folder)

    def before_content(self):
        MatObjectDirective.before_content(self)
        # A class signature always parses (mat_sig_re matches any line).
        if self.names:  # pragma: no branch
            self.env.temp_data["mat:class"] = self.names[0]
            self.clsname_set = True


class MatClassmember(MatObjectDirective):
    """Description of a class member (methods, attributes)."""

    def needs_arglist(self):
        return self.objtype.endswith("method")

    def get_signature_prefix(self):
        static = "static " if self.objtype == "staticmethod" else ""
        return f"{self.flag_prefix()}{static}"

    def get_index_text(self, folder, name_cls):  # noqa: ARG002
        name = name_cls[1]
        kind = {
            "method": translation("%s() (%s method)"),
            "staticmethod": translation("%s() (%s static method)"),
            "attribute": translation("%s (%s attribute)"),
            "event": translation("%s (%s event)"),
        }[self.objtype]
        clsname, _, member = name.rpartition(".")
        if not clsname:
            return f"{name}()" if self.objtype.endswith("method") else name
        return kind % (member, clsname)

    def before_content(self):
        MatObjectDirective.before_content(self)
        if self.names and not self.env.temp_data.get("mat:class"):
            ref, display = self.names[-1]
            if "." in display:
                cls = (ref.rpartition(".")[0], display.rpartition(".")[0])
                self.env.temp_data["mat:class"] = cls
                self.clsname_set = True


class MatMethodlike(MatClassmember):
    """Description of a method."""

    flags = ("abstract", "sealed")
    option_spec = {
        **MatObjectDirective.option_spec,
        **dict.fromkeys(flags, directives.flag),
    }


class MatAttributelike(MatClassmember):
    """Description of a property or enumeration value."""

    flags = ("abstract", "constant", "dependent", "read-only")
    option_spec = {
        **MatObjectDirective.option_spec,
        **dict.fromkeys(flags, directives.flag),
    }


class MatFolder(MatObjectDirective):
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
        dom = cast(MATLABDomain, self.env.get_domain("mat"))
        ref = mat_types.folder_reference(
            dom, sig, location=(self.env.docname, self.lineno)
        )
        if ref.rstrip("/").rpartition("/")[2].startswith("@"):
            logger.warning(
                "[sphinxcontrib-matlabdomain] %s is a class folder; "
                "document its class instead",
                ref,
                type="mat",
                subtype="directive",
                location=(self.env.docname, self.lineno),
            )
            raise ValueError
        entity = dom.entities_table.get(ref)
        if entity is not None:
            namespace = getattr(entity, "matlab_name", None)
        elif ref != mat_naming.ROOT_REFERENCE:
            namespace = mat_naming.folder_namespace(
                ref.rstrip("/"),
                mat_naming.default_namelengthmax(self.env.config.matlab_version),
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
        dom = cast(MATLABDomain, self.env.get_domain("mat"))
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
        "staticmethod": ObjType(translation("static method"), "meth", "obj"),
        "attribute": ObjType(translation("attribute"), "attr", "obj"),
        "event": ObjType(translation("event"), "event", "obj"),
        "folder": ObjType(translation("folder"), "folder", "obj"),
        "script": ObjType(translation("script"), "scpt", "obj"),
        "application": ObjType(translation("application"), "app", "obj"),
        **{
            objtype: ObjType(label, objtype, "obj")
            for objtype, label in SIMULINK_LABELS.items()
        },
    }

    directives = {
        "function": MatModulelevel,
        "data": MatModulelevel,
        "class": MatClasslike,
        "method": MatMethodlike,
        "staticmethod": MatMethodlike,
        "attribute": MatAttributelike,
        "event": MatClassmember,
        "folder": MatFolder,
        "currentfolder": MatCurrentFolder,
        "script": MatModulelevel,
        "application": MatModulelevel,
        **dict.fromkeys(SIMULINK_LABELS, MatSimulinkObject),
    }
    roles = {
        "data": MatXRefRole(),
        "func": MatXRefRole(fix_parens=True),
        "class": MatXRefRole(),
        "const": MatXRefRole(),
        "attr": MatXRefRole(),
        "enum": MatXRefRole(),
        "event": MatXRefRole(),
        "meth": MatXRefRole(fix_parens=True),
        "folder": MatXRefRole(),
        "obj": MatXRefRole(),
        "scpt": MatXRefRole(),
        "app": MatXRefRole(),
        **{objtype: MatXRefRole() for objtype in SIMULINK_LABELS},
        # A sidecar doc, by path reference; the text is its title.
        "sidecar": XRefRole(),
    }
    initial_data = {
        # Per-document registrations (cleared/merged by docname).
        "objects": {},  # path reference -> docname, objtype, display name
        "folders": {},  # folder reference -> docname, synopsis, platform, deprecated
        "doc_sources": {},  # docname -> {source path: (mtime_ns, size)} it used
        "sidecar_docs": {},  # docname -> {sidecar reference: title} it renders
        # docname -> [(sidecar reference, kind, target, line)]: broken relative
        # links and missing images in the sidecar docs it renders
        "sidecar_issues": {},
        # docname -> True: it has a reference to a MATLAB object
        "xref_docs": {},
        # Shared source state, rebuilt by ``mat_types.analyze`` each build;
        # files are parsed lazily (see ``mat_types``).
        # source path -> {reference, type, mtime, size, warnings, unreadable,
        #                 matlab_name, private, scope}
        "index": {},
        "sidecars": {},  # sidecar doc path -> {reference, mtime, size}
        # Simulink documentation file path -> {reference, mtime, size}
        "simulink_docs": {},
        "parse_cache": {},  # (path, mtime_ns, size) -> parsed MatObject
        "parse_warnings": {},  # (path, mtime_ns, size) -> parse-stage warnings
        "entities_table": {},  # path reference -> MatObject (files and folders)
        "matlab_names": {},  # MATLAB name -> path references
        # Build state of the outputs that share this environment (one doctree
        # folder), by (builder name, normalized absolute output folder);
        # main process only (``mat_urls.pages_to_write``).
        # the outputs that have written everything the environment holds
        "in_step": set(),
        # HTML outputs -> documents below matlab_apidoc_output_dir they have
        # pages for
        "api_pages": {},
    }
    # Bump when the layout of ``initial_data`` (the pickled domain data) or the
    # parsed objects it caches change, so Sphinx drops stale cached environments.
    data_version = 29
    indices = [
        MATLABFolderIndex,
    ]

    def __init__(self, env):
        super().__init__(env)
        # display name -> references of documented objects (built lazily)
        self._displays = None
        self._spaced: dict[str, str] = {}  # built with _displays
        # mat_urls.addresses (built lazily)
        self._stable_urls = None
        # sidecar reference -> the first document that renders it (built lazily)
        self._sidecar_docs = None
        # reference -> documents of parallel-read workers that describe it,
        # noted by merge_domaindata and warned by check_consistency
        self._duplicates = {}
        # Documents read in this build (``env-before-read-docs``).
        self.read_docnames = ()
        # Objects and removed documents before this build read
        # (``mat_urls.note_pages``).
        self.objects_before = {}
        self.removed_docs = set()
        self.reset_sources()

    def reset_sources(self):
        """Forget the in-process state of the previous index stage."""
        # path reference -> source path (built lazily from the index)
        self._sources = None
        # sidecar reference -> sidecar path (built lazily from the sidecar docs)
        self._sidecars = None
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

    def sidecar_paths(self):
        """Path reference -> path of every indexed sidecar doc."""
        if self._sidecars is None:
            self._sidecars = {
                record["reference"]: path
                for path, record in self.data["sidecars"].items()
            }
        return self._sidecars

    def note_sidecar(self, ref, title, issues):
        """Record that the document being read renders the sidecar doc ``ref``."""
        docname = self.env.docname
        self.data["sidecar_docs"].setdefault(docname, {})[ref] = title
        self.data["sidecar_issues"].setdefault(docname, []).extend(
            (ref, *issue) for issue in issues
        )
        self._sidecar_docs = None

    def sidecar_doc(self, ref):
        """Return the document that renders the sidecar doc ``ref`` (the first by
        name, so serial and parallel builds agree), or None.
        """
        if self._sidecar_docs is None:
            self._sidecar_docs = {}
            for docname in sorted(self.data["sidecar_docs"]):
                for sidecar in self.data["sidecar_docs"][docname]:
                    self._sidecar_docs.setdefault(sidecar, docname)
        return self._sidecar_docs.get(ref)

    @property
    def entities_table(self):
        return self.data["entities_table"]

    def note_object(self, name, objtype, display=None, location=None):
        """Register a documented object (``name`` is its path reference).

        Warns on duplicates only when ``location`` is given.
        """
        objects = self.data["objects"]
        if name in objects and location is not None:
            self._warn_duplicate(name, objects[name][0], location)
        objects[name] = (self.env.docname, objtype, display or name)
        self._displays = self._stable_urls = None

    def _warn_duplicate(self, name, other, location):
        logger.warning(
            "[sphinxcontrib-matlabdomain] duplicate object description of %s, "
            "other instance in %s, use :no-index: for one of them",
            name,
            self.env.doc2path(other),
            type="mat",
            subtype="duplicate",
            location=location,
        )

    def clear_doc(self, docname):
        for ref, (fn, _, _) in list(self.data["objects"].items()):
            if fn == docname:
                del self.data["objects"][ref]
        for ref, (fn, _, _, _) in list(self.data["folders"].items()):
            if fn == docname:
                del self.data["folders"][ref]
        self.data["doc_sources"].pop(docname, None)
        self.data["sidecar_docs"].pop(docname, None)
        self.data["sidecar_issues"].pop(docname, None)
        self.data["xref_docs"].pop(docname, None)
        self._displays = self._stable_urls = None
        self._sidecar_docs = None

    def process_doc(self, env, docname, document):
        if slugs := document.get("matlab_sidecar_slugs"):
            metadata = env.metadata[docname]
            metadata["myst_slugs"] = {**slugs, **metadata.get("myst_slugs", {})}
        if any(
            node.get("refdomain") == "mat" or node.get("reftype") == "any"
            for node in document.findall(addnodes.pending_xref)
        ):
            self.data["xref_docs"][docname] = True

    def merge_domaindata(self, docnames, otherdata):
        # Merge per-document registrations from a parallel-read worker, and
        # the files it parsed, so the next build need not parse them again.
        # The index and the entities are built in the main process, and the
        # build state ("in_step", "api_pages") is kept there.
        # An object or folder that another worker described too: the later in
        # reading order wins, as in a serial build, whatever the merge order.
        order = {docname: i for i, docname in enumerate(self.read_docnames)}
        for name in ("objects", "folders"):
            ours = self.data[name]
            for ref, data in otherdata[name].items():
                if data[0] not in docnames:
                    continue
                old = ours.get(ref)
                if old is not None and old[0] in order and data[0] in order:
                    # a folder description warns in neither build (note_object)
                    if name == "objects" and data[1] != "folder":
                        self._duplicates.setdefault(ref, set()).update(
                            (old[0], data[0])
                        )
                    data = max(old, data, key=lambda entry: order[entry[0]])
                ours[ref] = data
        for name in ("doc_sources", "sidecar_docs", "sidecar_issues", "xref_docs"):
            for docname, value in otherdata[name].items():
                if docname in docnames:
                    self.data[name][docname] = value
        index = self.data["index"]
        for name in ("parse_cache", "parse_warnings"):
            ours = self.data[name]
            for key, value in otherdata[name].items():
                record = index.get(key[0])
                if record is None or (record["mtime"], record["size"]) != key[1:]:
                    continue
                ours.setdefault(key, value)
        self._displays = self._stable_urls = None
        self._sidecar_docs = None

    def check_consistency(self):
        # Duplicates that parallel-read workers could not see: warn as a serial
        # build does, each description about the one read before it.
        order = {docname: i for i, docname in enumerate(self.read_docnames)}
        for ref, docs in sorted(self._duplicates.items()):
            pairs = itertools.pairwise(sorted(docs, key=order.__getitem__))
            for earlier, later in pairs:
                self._warn_duplicate(ref, earlier, (later, None))
        self._duplicates = {}

    def _by_display(self, name):
        if self._displays is None:
            self._displays = {}
            # a block with a line break in its name, by its reference with
            # spaces; the first of those that collapse to one form (in sorted
            # order) has it
            self._spaced = {}
            # by reference: the merge order of a parallel read does not matter
            for ref, (_, _, display) in sorted(self.data["objects"].items()):
                self._displays.setdefault(display, []).append(ref)
            for ref in sorted(self.data["objects"]):
                if mat_naming.has_line_break(ref):
                    self._spaced.setdefault(mat_naming.collapse_space(ref), ref)
        return self._displays.get(name, [])

    def _documented(self, ref):
        """Return the documented reference ``ref`` names: itself, or the block
        it names with spaces for line breaks (as a role's target writes it).
        """
        if ref in self.data["objects"]:
            return ref
        self._by_display("")
        return self._spaced.get(ref, ref)

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
        exact = [self._documented(r) for r in exact]
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
            return sorted(
                (ref, entry)
                for ref, entry in objects.items()
                if entry[2].endswith(f".{name}")
                and (objtypes is None or entry[1] in objtypes)
                and not mat_naming.is_private_reference(ref)
            )
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

    def resolve_xref(self, env, fromdocname, builder, type, target, node, contnode):
        if type == "sidecar":
            return self._resolve_sidecar(
                env, fromdocname, builder, target, node, contnode
            )
        searchmode = (node.hasattr("refspecific") and 1) or 0
        matches = self.find_obj(
            node.get("mat:folder"), node.get("mat:class"), target, type, searchmode
        )
        if not matches:
            return None
        if len(matches) > 1:
            if self._shadowed(matches):
                refs = [ref for ref, _ in matches]
                return mat_urls.chooser_link(self, builder, fromdocname, refs, contnode)
            mat_types.warn_ambiguous(target, [m[0] for m in matches], node)
            # Unlinked, without a second "target not found" warning.
            return contnode
        ref, entry = matches[0]
        return self._refnode(builder, fromdocname, ref, entry, contnode)

    def _resolve_sidecar(self, env, fromdocname, builder, target, node, contnode):
        # A link to a sidecar doc goes to the document that renders it; without
        # text of its own it shows the sidecar doc's title.
        ref = unicodedata.normalize("NFC", target)
        docname = self.sidecar_doc(ref)
        if docname is None:
            return None
        if not node.get("refexplicit"):
            title = self.data["sidecar_docs"][docname][ref]
            contnode = nodes.inline(title, title, classes=contnode["classes"])
        # A Markdown heading's slug (myst_heading_anchors) names its section.
        anchor = node.get("reftargetid") or ""
        slugs = env.metadata.get(docname, {}).get("myst_slugs", {})
        if anchor in slugs:
            anchor = slugs[anchor][1]
        return make_refnode(builder, fromdocname, docname, anchor, contnode)

    def _shadowed(self, matches):
        """Return True for objects of one MATLAB name that the project accepts
        (``matlab_link_shadowed_files_to_chooser_pages``).
        """
        return (
            self.env.config.matlab_link_shadowed_files_to_chooser_pages
            and len({entry[2] for _, entry in matches}) == 1
        )

    def get_full_qualified_name(self, node):
        """Return the path reference of an intersphinx target that is a MATLAB
        name, or None.

        Intersphinx calls this when no inventory has the target as written
        (inventories name objects by path reference). The target is the
        MATLAB name (inventory display name) of exactly one non-private
        object of the role's types, in the inventory the reference names
        (``:external+lib:`` or ``lib:``) or else in any inventory. Several,
        also the same reference in several inventories: a ``mat.ambiguous``
        warning, and the target stays unlinked.
        """
        from sphinx.ext.intersphinx import InventoryAdapter

        if node.get("mat:ambiguous"):  # check_inventories warned
            return None
        inventories = InventoryAdapter(self.env).named_inventory
        target = unicodedata.normalize("NFC", node["reftarget"]).removesuffix("()")
        named = node.get("inventory")
        prefix, colon, rest = target.partition(":")
        if named is None and colon and prefix in inventories:
            named, target = prefix, rest
        names = [named] if named is not None else sorted(inventories)
        role = node["reftype"]
        objtypes = self.object_types if role == "any" else self.objtypes_for_role(role)
        found = {}
        for name in names:
            for objtype in objtypes or ():
                for ref, item in inventories[name].get(f"mat:{objtype}", {}).items():
                    # Sphinx < 8.2: (project, version, uri, display name)
                    display = getattr(item, "display_name", None) or item[3]
                    # ``ref == target``: a chooser page's entry
                    if (
                        display != target
                        or ref == target
                        or mat_naming.is_private_reference(ref)
                    ):
                        continue
                    label = f"{name}:{ref}" if len(names) > 1 else ref
                    found.setdefault((name, ref), label)
        if len(found) > 1:
            node["mat:ambiguous"] = True
            # One site's duplicates: its chooser page, if it has one, was
            # found before this.
            if self.env.config.matlab_link_shadowed_files_to_chooser_pages and (
                len({name for name, _ in found}) == 1
            ):
                return None
            hint = "write one of them" if len(names) > 1 else "use a path reference"
            mat_types.warn_ambiguous(target, found.values(), node, hint)
            return None
        return next(iter(found), (None, None))[1]

    def inventory_name(self, ref):
        """Return the name of ``ref`` in ``objects.inv``, or None when it has
        none. That is ``ref``, but with spaces for the line breaks of a block's
        name (one line of the file per entry): the form a role's target has.
        When that form is another object's reference or the form of an earlier
        block, the block has no entry.
        """
        if not mat_naming.has_line_break(ref):
            return ref
        name = mat_naming.collapse_space(ref)
        return name if self._documented(name) == ref else None

    def get_objects(self):
        for ref, (docname, objtype, display) in self.data["objects"].items():
            name = self.inventory_name(ref)
            if name is None:
                continue
            if mat_naming.has_line_break(display):
                display = mat_naming.collapse_space(display)
            yield (
                name,
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
            role = self.role_for_objtype(matches[0][1][1])
            if self._shadowed(matches):
                refs = [ref for ref, _ in matches]
                link = mat_urls.chooser_link(self, builder, fromdocname, refs, contnode)
                return [(f"mat:{role}", link)]
            mat_types.warn_ambiguous(target, [m[0] for m in matches], node)
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


def check_config_names(app, config):  # noqa: ARG001
    # vars(config): names another extension set earlier (sphinx-multiproject).
    names = {*config._raw_config, *vars(config)}
    mat_types.check_config_names(names, config._options)


def ensure_configuration(app, config):
    mat_config.check_sources(config, app.srcdir)
    if config.matlab_auto_link not in (None, "basic", "all"):
        raise ConfigError("matlab_auto_link must be None, 'basic', or 'all'.")


def _get_version():
    try:
        from importlib.metadata import version

        return version("sphinxcontrib-matlabdomain")
    except Exception:
        return "0.0.0"


def setup(app):
    # The mat:auto* directives read autodoc's config values.
    app.setup_extension("sphinx.ext.autodoc")
    app.connect("config-inited", check_config_names)
    app.connect("config-inited", ensure_configuration)
    app.connect("config-inited", check_external_names)
    app.connect("config-inited", mat_sidecars.check_config)
    app.connect("config-inited", mat_api_check.check_config)
    app.connect("config-inited", simulink_linker.check_config)
    app.connect("builder-inited", analyze)
    app.connect("env-get-outdated", mat_types.outdated_docs)
    app.connect("env-before-read-docs", mat_types.note_read_docs)
    app.connect("env-updated", mat_types.warn_parsed_sources)
    app.connect("build-finished", mat_api_check.set_status)
    app.connect("missing-reference", check_inventories, priority=400)
    app.add_post_transform(CheckExternalReferences)
    app.connect("missing-reference", keep_unresolved_references, priority=900)
    app.connect("html-page-context", mat_urls.rewrite_permalinks)
    app.connect("html-collect-pages", mat_urls.chooser_pages)
    app.connect("builder-inited", mat_urls.add_script)
    app.connect("env-get-outdated", mat_urls.note_pages)
    app.connect("env-get-updated", mat_urls.pages_to_write)
    app.connect("build-finished", mat_urls.write_redirects)
    app.connect("build-finished", simulink_linker.write_settings)

    app.add_domain(MATLABDomain)
    app.add_builder(mat_api_check.MatlabApiCheckBuilder)
    mat_config.add_config_values(app.add_config_value)

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

    app.registry.add_documenter("mat:event", doc.MatEventDocumenter)
    app.add_directive_to_domain(
        "mat", "autoevent", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:data", doc.MatDataDocumenter)
    app.add_directive_to_domain(
        "mat", "autodata", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:application", doc.MatApplicationDocumenter)
    app.add_directive_to_domain(
        "mat", "autoapplication", mat_directives.MatlabAutodocDirective
    )

    for documenter in doc.SIMULINK_DOCUMENTERS:
        app.registry.add_documenter(f"mat:{documenter.objtype}", documenter)
        app.add_directive_to_domain(
            "mat", f"auto{documenter.objtype}", mat_directives.MatlabAutodocDirective
        )

    app.add_autodoc_attrgetter(mat_types.MatModule, mat_types.MatModule.getter)
    app.add_autodoc_attrgetter(doc.MatClass, doc.MatClass.getter)
    app.add_directive_to_domain("mat", "autosidecar", mat_sidecars.AutoSidecar)

    return {
        "version": _get_version(),
        # Workers parse lazily; merge_domaindata collects what they parsed.
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
