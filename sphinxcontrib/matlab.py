# -*- coding: utf-8 -*-
"""
    sphinxcontrib.matlab
    ~~~~~~~~~~~~~~~~~~~~

    The MATLAB domain.

    :copyright: Copyright 2007-2011 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
from . import mat_documenters as doc
from . import mat_directives
from . import mat_types

import re

from docutils import nodes
from docutils.parsers.rst import directives, Directive

from sphinx import addnodes
from sphinx.roles import XRefRole
from sphinx.locale import _
from sphinx.domains import Domain, ObjType, Index
from sphinx.directives import ObjectDescription
from sphinx.util.nodes import make_refnode
from sphinx.util.docfields import Field, GroupedField, TypedField
import sphinx.util

logger = sphinx.util.logging.getLogger("matlab-domain")


# REs for MATLAB signatures
mat_sig_re = re.compile(
    r"""^ ([+@]?[+@\w.]*\.)?            # class name(s)
          ([+@]?\w+)  \s*               # thing name
          (?: \((.*)\)                  # optional: arguments
           (?:\s* -> \s* (.*))?         #           return annotation
          )? $                          # and nothing more
          """,
    re.VERBOSE,
)


def _pseudo_parse_arglist(signode, arglist):
    """ "Parse" a list of arguments separated by commas.

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
    """
    Description of a general MATLAB object.
    """

    option_spec = {
        "noindex": directives.flag,
        "module": directives.unchanged,
        "annotation": directives.unchanged,
    }

    doc_field_types = [
        TypedField(
            "parameter",
            label=_("Parameters"),
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
            label=_("Variables"),
            rolename="obj",
            names=("var", "ivar", "cvar"),
            typerolename="obj",
            typenames=("vartype",),
            can_collapse=True,
        ),
        GroupedField(
            "exceptions",
            label=_("Raises"),
            rolename="exc",
            names=("raises", "raise", "exception", "except"),
            can_collapse=True,
        ),
        Field(
            "returnvalue",
            label=_("Returns"),
            has_arg=False,
            names=("returns", "return"),
        ),
        Field("returntype", label=_("Return type"), has_arg=False, names=("rtype",)),
    ]

    def get_signature_prefix(self, sig):
        """May return a prefix to put before the object name in the
        signature.
        """
        return ""

    def needs_arglist(self):
        """May return true if an empty argument list is to be generated even if
        the document contains none.
        """
        return False

    def handle_signature(self, sig, signode):
        """Transform a MATLAB signature into RST nodes.

        Return (fully qualified name of the thing, classname if any).

        If inside a class, the current class name is handled intelligently:
        * it is stripped from the displayed name if present
        * it is added to the full name (return value) if not present
        """
        m = mat_sig_re.match(sig)
        if m is None:
            raise ValueError
        name_prefix, name, arglist, retann = m.groups()

        # determine module and class name (if applicable), as well as full name
        modname = self.options.get("module", self.env.temp_data.get("mat:module"))

        if not self.env.config.matlab_keep_package_prefix:
            modname = mat_types.strip_package_prefix(modname)
            name_prefix = mat_types.strip_package_prefix(name_prefix)
            name = mat_types.strip_package_prefix(name)

        classname = self.env.temp_data.get("mat:class")
        if classname:
            add_module = False
            if name_prefix and name_prefix.startswith(classname):
                fullname = name_prefix + name
                # class name is given again in the signature
                name_prefix = name_prefix[len(classname) :].lstrip(".")
            elif name_prefix:
                # class name is given in the signature, but different
                # (shouldn't happen)
                fullname = classname + "." + name_prefix + name
            else:
                # class name is not given in the signature
                fullname = classname + "." + name
        else:
            add_module = True
            if name_prefix:
                classname = name_prefix.rstrip(".")
                fullname = name_prefix + name
            else:
                classname = ""
                fullname = name

        signode["module"] = modname
        signode["class"] = classname
        signode["fullname"] = fullname

        sig_prefix = self.get_signature_prefix(sig)
        if sig_prefix:
            signode += addnodes.desc_annotation(sig_prefix, sig_prefix)

        if name_prefix:
            signode += addnodes.desc_addname(name_prefix, name_prefix)
        # exceptions are a special case, since they are documented in the
        # 'exceptions' module.
        elif add_module and self.env.config.add_module_names:
            modname = self.options.get("module", self.env.temp_data.get("mat:module"))

            if self.env.config.matlab_short_links:
                # modname is only used for package names
                # - "target.+package" => "package"
                # - "target" => ""
                parts = modname.split(".")
                parts = [part for part in parts if part.startswith("+")]
                modname = ".".join(parts)

            # Consider adding the module name, except for "." and "exceptions"
            # - This avoids the ".." for root entities.
            if modname and (modname not in (".", "exceptions")):
                if not self.env.config.matlab_keep_package_prefix:
                    modname = mat_types.strip_package_prefix(modname)

                nodetext = modname + "."
                signode += addnodes.desc_addname(nodetext, nodetext)

        anno = self.options.get("annotation")

        signode += addnodes.desc_name(name, name)
        if not arglist:
            if self.needs_arglist():
                # for callables, add an empty parameter list
                signode += addnodes.desc_parameterlist()
            if retann:
                signode += addnodes.desc_returns(retann, retann)
            if anno:
                signode += addnodes.desc_annotation(" " + anno, " " + anno)
            return fullname, name_prefix

        _pseudo_parse_arglist(signode, arglist)
        if retann:
            signode += addnodes.desc_returns(retann, retann)
        if anno:
            signode += addnodes.desc_annotation(" " + anno, " " + anno)
        return fullname, name_prefix

    def get_index_text(self, modname, name):
        """Return the text for the index entry of the object."""
        raise NotImplementedError("must be implemented in subclasses")

    def add_target_and_index(self, name_cls, sig, signode):
        modname = self.options.get("module", self.env.temp_data.get("mat:module"))

        if self.env.config.matlab_short_links:
            # modname is only used for package names
            # - "target.+package" => "package"
            # - "target" => ""
            parts = modname.split(".")
            parts = [part for part in parts if part.startswith("+")]
            modname = ".".join(parts)

        fullname = (modname and modname + "." or "") + name_cls[0]
        fullname = fullname.lstrip(".")

        if not self.env.config.matlab_keep_package_prefix:
            modname_out = mat_types.strip_package_prefix(modname)
            fullname_out = (modname_out and modname_out + "." or "") + name_cls[0]
            fullname_out = fullname_out.lstrip(".")
        else:
            modname_out, fullname_out = modname, fullname

        # note target
        if fullname_out not in self.state.document.ids:
            signode["names"].append(fullname_out)
            signode["ids"].append(fullname_out)
            signode["first"] = not self.names
            self.state.document.note_explicit_target(signode)
            objects = self.env.domaindata["mat"]["objects"]
            if fullname_out in objects:
                self.state_machine.reporter.warning(
                    "duplicate object description of %s, " % fullname_out
                    + "other instance in "
                    + self.env.doc2path(objects[fullname_out][0])
                    + ", use :noindex: for one of them",
                    line=self.lineno,
                )
            objects[fullname_out] = (self.env.docname, self.objtype)

        indextext = self.get_index_text(modname_out, name_cls)
        if indextext:
            entry = ("single", indextext, fullname_out, "", None)
            self.indexnode["entries"].append(entry)

    def before_content(self):
        # needed for automatic qualification of members (reset in subclasses)
        self.clsname_set = False

    def after_content(self):
        if self.clsname_set:
            self.env.temp_data["mat:class"] = None


class MatModulelevel(MatObject):
    """
    Description of an object on module level (functions, data, application).
    """

    def needs_arglist(self):
        return self.objtype == "function"

    def get_index_text(self, modname, name_cls):
        if self.objtype == "function":
            if not modname:
                return _("%s() (built-in function)") % name_cls[0]
            return _("%s() (in module %s)") % (name_cls[0], modname)
        elif self.objtype == "data":
            if not modname:
                return _("%s (built-in variable)") % name_cls[0]
            return _("%s (in module %s)") % (name_cls[0], modname)
        elif self.objtype == "application":
            if not modname:
                return _("%s (built-in application)") % name_cls[0]
            return _("%s (in module %s)") % (name_cls[0], modname)
        else:
            return ""


class MatClasslike(MatObject):
    """
    Description of a class-like object (classes, interfaces, exceptions).
    """

    def get_signature_prefix(self, sig):
        return self.objtype + " "

    def get_index_text(self, modname, name_cls):
        if self.objtype == "class":
            if not modname:
                return _("%s (built-in class)") % name_cls[0]
            return _("%s (class in %s)") % (name_cls[0], modname)
        elif self.objtype == "exception":
            return name_cls[0]
        else:
            return ""

    def before_content(self):
        MatObject.before_content(self)
        if self.names:
            self.env.temp_data["mat:class"] = self.names[0][0]
            self.clsname_set = True


class MatClassmember(MatObject):
    """
    Description of a class member (methods, attributes).
    """

    def needs_arglist(self):
        return self.objtype.endswith("method")

    def get_signature_prefix(self, sig):
        if self.objtype == "staticmethod":
            return "static "
        elif self.objtype == "classmethod":
            return "classmethod "
        return ""

    def get_index_text(self, modname, name_cls):
        name, cls = name_cls
        add_modules = self.env.config.add_module_names
        if self.objtype == "method":
            try:
                clsname, methname = name.rsplit(".", 1)
            except ValueError:
                if modname:
                    return _("%s() (in module %s)") % (name, modname)
                else:
                    return "%s()" % name
            if modname and add_modules:
                return _("%s() (%s.%s method)") % (methname, modname, clsname)
            else:
                return _("%s() (%s method)") % (methname, clsname)
        elif self.objtype == "staticmethod":
            try:
                clsname, methname = name.rsplit(".", 1)
            except ValueError:
                if modname:
                    return _("%s() (in module %s)") % (name, modname)
                else:
                    return "%s()" % name
            if modname and add_modules:
                return _("%s() (%s.%s static method)") % (methname, modname, clsname)
            else:
                return _("%s() (%s static method)") % (methname, clsname)
        elif self.objtype == "classmethod":
            try:
                clsname, methname = name.rsplit(".", 1)
            except ValueError:
                if modname:
                    return _("%s() (in module %s)") % (name, modname)
                else:
                    return "%s()" % name
            if modname:
                return _("%s() (%s.%s class method)") % (methname, modname, clsname)
            else:
                return _("%s() (%s class method)") % (methname, clsname)
        elif self.objtype == "attribute":
            try:
                clsname, attrname = name.rsplit(".", 1)
            except ValueError:
                if modname:
                    return _("%s (in module %s)") % (name, modname)
                else:
                    return name
            if modname and add_modules:
                return _("%s (%s.%s attribute)") % (attrname, modname, clsname)
            else:
                return _("%s (%s attribute)") % (attrname, clsname)
        else:
            return ""

    def before_content(self):
        MatObject.before_content(self)
        lastname = self.names and self.names[-1][1]
        if lastname and not self.env.temp_data.get("mat:class"):
            self.env.temp_data["mat:class"] = lastname.strip(".")
            self.clsname_set = True


class MatDecoratorMixin(object):
    """
    Mixin for decorator directives.
    """

    def handle_signature(self, sig, signode):
        ret = super(MatDecoratorMixin, self).handle_signature(sig, signode)
        signode.insert(0, addnodes.desc_addname("@", "@"))
        return ret

    def needs_arglist(self):
        return False


class MatDecoratorFunction(MatDecoratorMixin, MatModulelevel):
    """
    Directive to mark functions meant to be used as decorators.
    """

    def run(self):
        # a decorator function is a function after all
        self.name = "mat:function"
        return MatModulelevel.run(self)


class MatDecoratorMethod(MatDecoratorMixin, MatClassmember):
    """
    Directive to mark methods meant to be used as decorators.
    """

    def run(self):
        self.name = "mat:method"
        return MatClassmember.run(self)


class MatModule(Directive):
    """
    Directive to mark description of a new module.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        "platform": lambda x: x,
        "synopsis": lambda x: x,
        "noindex": directives.flag,
        "deprecated": directives.flag,
    }

    def run(self):
        env = self.state.document.settings.env
        modname = self.arguments[0].strip()

        if not env.config.matlab_keep_package_prefix:
            modname_out = mat_types.strip_package_prefix(modname)
        else:
            modname_out = modname

        noindex = "noindex" in self.options
        env.temp_data["mat:module"] = modname
        ret = []
        if not noindex:
            env.domaindata["mat"]["modules"][modname] = (
                env.docname,
                self.options.get("synopsis", ""),
                self.options.get("platform", ""),
                "deprecated" in self.options,
            )
            # make a duplicate entry in 'objects' to facilitate searching for
            # the module in MATLABDomain.find_obj()
            env.domaindata["mat"]["objects"][modname] = (env.docname, "module")
            targetnode = nodes.target("", "", ids=["module-" + modname], ismod=True)
            self.state.document.note_explicit_target(targetnode)
            # the platform and synopsis aren't printed; in fact, they are only
            # used in the modindex currently
            ret.append(targetnode)
            indextext = _("%s (module)") % modname_out
            entry = ("single", indextext, "module-" + modname, "", None)
            inode = addnodes.index(entries=[entry])
            ret.append(inode)
        return ret


class MatCurrentModule(Directive):
    """
    This directive is just to tell Sphinx that we're documenting
    stuff in module foo, but links to module foo won't lead here.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    def run(self):
        env = self.state.document.settings.env
        modname = self.arguments[0].strip()
        if modname == "None":
            env.temp_data["mat:module"] = None
        else:
            env.temp_data["mat:module"] = modname
        return []


class MatXRefRole(XRefRole):
    def process_link(self, env, refnode, has_explicit_title, title, target):
        refnode["mat:module"] = env.temp_data.get("mat:module")
        refnode["mat:class"] = env.temp_data.get("mat:class")
        if not has_explicit_title:
            title = title.lstrip(".")  # only has a meaning for the target
            target = target.lstrip("~")  # only has a meaning for the title
            # if the first character is a tilde, don't display the module/class
            # parts of the contents
            if title[0:1] == "~":
                title = title[1:]
                dot = title.rfind(".")
                if dot != -1:
                    title = title[dot + 1 :]

            if not env.config.matlab_keep_package_prefix:
                title = mat_types.strip_package_prefix(title)

        # if the first character is a dot, search more specific namespaces first
        # else search builtins first
        if target[0:1] == ".":
            target = target[1:]
            refnode["refspecific"] = True
        return title, target


class MATLABModuleIndex(Index):
    """
    Index subclass to provide the MATLAB module index.
    """

    name = "modindex"
    localname = _("MATLAB Module Index")
    shortname = _("matlab index")

    def generate(self, docnames=None):
        content = {}
        # list of prefixes to ignore
        ignores = self.domain.env.config["modindex_common_prefix"]
        ignores = sorted(ignores, key=len, reverse=True)
        # list of all modules, sorted by module name
        modules = sorted(
            iter(self.domain.data["modules"].items()), key=lambda x: x[0].lower()
        )
        # sort out collapsable modules
        prev_modname = ""
        num_toplevels = 0
        for modname, (docname, synopsis, platforms, deprecated) in modules:
            if docnames and docname not in docnames:
                continue

            for ignore in ignores:
                if modname.startswith(ignore):
                    modname = modname[len(ignore) :]
                    stripped = ignore
                    break
            else:
                stripped = ""

            # we stripped the whole module name?
            if not modname:
                modname, stripped = stripped, ""

            # Create nice mod-name
            if not self.domain.env.config.matlab_keep_package_prefix:
                modname_out = mat_types.strip_package_prefix(modname)
            else:
                modname_out = modname

            entries = content.setdefault(modname_out[0].lower(), [])

            package = modname.split(".")[0]
            if package != modname:
                # it's a submodule
                if prev_modname == package:
                    # first submodule - make parent a group head
                    if entries:
                        entries[-1][1] = 1
                elif not prev_modname.startswith(package):
                    # submodule without parent in list, add dummy entry
                    entries.append([stripped + package, 1, "", "", "", "", ""])
                subtype = 2
            else:
                num_toplevels += 1
                subtype = 0

            qualifier = deprecated and _("Deprecated") or ""
            entries.append(
                [
                    stripped + modname_out,
                    subtype,
                    docname,
                    "module-" + stripped + modname,
                    platforms,
                    qualifier,
                    synopsis,
                ]
            )
            prev_modname = modname

        # apply heuristics when to collapse modindex at page load:
        # only collapse if number of toplevel modules is larger than
        # number of submodules
        collapse = len(modules) - num_toplevels < num_toplevels

        # sort by first letter
        content = sorted(content.items())

        return content, collapse


class MATLABDomain(Domain):
    """MATLAB language domain."""

    name = "mat"
    label = "MATLAB"
    object_types = {
        "function": ObjType(_("function"), "func", "obj"),
        "data": ObjType(_("data"), "data", "obj"),
        "class": ObjType(_("class"), "class", "obj"),
        "exception": ObjType(_("exception"), "exc", "obj"),
        "method": ObjType(_("method"), "meth", "obj"),
        "classmethod": ObjType(_("class method"), "meth", "obj"),
        "staticmethod": ObjType(_("static method"), "meth", "obj"),
        "attribute": ObjType(_("attribute"), "attr", "obj"),
        "module": ObjType(_("module"), "mod", "obj"),
        "script": ObjType(_("script"), "scpt", "obj"),
        "application": ObjType(_("application"), "app", "obj"),
    }

    directives = {
        "function": MatModulelevel,
        "data": MatModulelevel,
        "class": MatClasslike,
        "exception": MatClasslike,
        "method": MatClassmember,
        "classmethod": MatClassmember,
        "staticmethod": MatClassmember,
        "attribute": MatClassmember,
        "module": MatModule,
        "currentmodule": MatCurrentModule,
        "decorator": MatDecoratorFunction,
        "decoratormethod": MatDecoratorMethod,
        "script": MatModulelevel,
        "application": MatModulelevel,
    }
    roles = {
        "data": MatXRefRole(),
        "exc": MatXRefRole(),
        "func": MatXRefRole(fix_parens=True),
        "class": MatXRefRole(),
        "const": MatXRefRole(),
        "attr": MatXRefRole(),
        "meth": MatXRefRole(fix_parens=True),
        "mod": MatXRefRole(),
        "obj": MatXRefRole(),
        "scpt": MatXRefRole(),
        "app": MatXRefRole(),
    }
    initial_data = {
        "objects": {},  # fullname -> docname, objtype
        "modules": {},  # modname -> docname, synopsis, platform, deprecated
    }
    indices = [
        MATLABModuleIndex,
    ]

    def clear_doc(self, docname):
        for fullname, (fn, _) in list(self.data["objects"].items()):  # noqa: 401
            if fn == docname:
                del self.data["objects"][fullname]
        for modname, (fn, _, _, _) in list(self.data["modules"].items()):
            if fn == docname:
                del self.data["modules"][modname]

    def find_obj(self, env, modname, classname, name, type, searchmode=0):
        """Find a MATLAB object for "name", perhaps using the given module
        and/or classname.  Returns a list of (name, object entry) tuples.
        """
        # skip parens
        if name[-2:] == "()":
            name = name[:-2]

        if not name:
            return []

        objects = self.data["objects"]
        matches = []

        newname = None
        if searchmode == 1:
            objtypes = self.objtypes_for_role(type)
            if objtypes is not None:
                if modname and classname:
                    fullname = modname + "." + classname + "." + name
                    if fullname in objects and objects[fullname][1] in objtypes:
                        newname = fullname
                if not newname:
                    if (
                        modname
                        and modname + "." + name in objects
                        and objects[modname + "." + name][1] in objtypes
                    ):
                        newname = modname + "." + name
                    elif name in objects and objects[name][1] in objtypes:
                        newname = name
                    else:
                        # "fuzzy" searching mode
                        searchname = "." + name
                        matches = [
                            (oname, objects[oname])
                            for oname in objects
                            if oname.endswith(searchname)
                            and objects[oname][1] in objtypes
                        ]
        else:
            # NOTE: searching for exact match, object type is not considered
            if name in objects:
                newname = name
            elif type == "mod":
                # only exact matches allowed for modules
                return []
            elif classname and classname + "." + name in objects:
                newname = classname + "." + name
            elif modname and modname + "." + name in objects:
                newname = modname + "." + name
            elif (
                modname
                and classname
                and modname + "." + classname + "." + name in objects
            ):
                newname = modname + "." + classname + "." + name
            # special case: builtin exceptions have module "exceptions" set
            elif type == "exc" and "." not in name and "exceptions." + name in objects:
                newname = "exceptions." + name
            # special case: object methods
            elif (
                type in ("func", "meth")
                and "." not in name
                and "object." + name in objects
            ):
                newname = "object." + name
        if newname is not None:
            matches.append((newname, objects[newname]))
        return matches

    def resolve_xref(self, env, fromdocname, builder, type, target, node, contnode):
        modname = node.get("mat:module")
        clsname = node.get("mat:class")
        searchmode = node.hasattr("refspecific") and 1 or 0
        matches = self.find_obj(env, modname, clsname, target, type, searchmode)
        if not matches:
            return None
        elif len(matches) > 1:
            logger.warning(
                "[sphinxcontrib-matlabdomain] more than one target found for cross-reference %r: %s",
                target,
                ", ".join(match[0] for match in matches),
                type="ref",
                subtype="python",
                location=node,
            )

        name, obj = matches[0]

        if obj[1] == "module":
            # get additional info for modules
            docname, synopsis, platform, deprecated = self.data["modules"][name]
            assert docname == obj[0]
            title = name
            if synopsis:
                title += ": " + synopsis
            if deprecated:
                title += _(" (deprecated)")
            if platform:
                title += " (" + platform + ")"
            return make_refnode(
                builder, fromdocname, docname, "module-" + name, contnode, title
            )
        else:
            return make_refnode(builder, fromdocname, obj[0], name, contnode, name)

    def get_objects(self):
        for modname, info in self.data["modules"].items():
            yield (modname, modname, "module", info[0], "module-" + modname, 0)
        for refname, (docname, type) in self.data["objects"].items():
            yield (refname, refname, type, docname, refname, 1)

    def resolve_any_xref(self, env, fromdocname, builder, target, node, contnode):
        ret = []
        for role in self.roles:
            matrole = f"mat:{role}"
            element = self.resolve_xref(
                env, fromdocname, builder, matrole, target, node, contnode
            )
            if element:
                ret.append((matrole, element))
        return ret


def analyze(app):
    mat_types.analyze(app)


def ensure_configuration(app, env):
    if env.matlab_short_links:
        logger.info(
            "[sphinxcontrib-matlabdomain] matlab_short_links=True, forcing matlab_keep_package_prefix=False."
        )
        env.matlab_keep_package_prefix = False


def setup(app):
    app.connect("config-inited", ensure_configuration)
    app.connect("builder-inited", analyze)

    app.add_domain(MATLABDomain)
    # autodoc
    app.add_config_value("matlab_src_dir", None, "env")
    app.add_config_value("matlab_src_encoding", None, "env")
    app.add_config_value("matlab_keep_package_prefix", False, "env")
    app.add_config_value("matlab_show_property_default_value", False, "env")
    app.add_config_value("matlab_short_links", False, "env")
    app.add_config_value("matlab_auto_link", None, "env")

    app.registry.add_documenter("mat:module", doc.MatModuleDocumenter)
    app.add_directive_to_domain(
        "mat", "automodule", mat_directives.MatlabAutodocDirective
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

    app.registry.add_documenter("mat:exception", doc.MatExceptionDocumenter)
    app.add_directive_to_domain(
        "mat", "autoexception", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:attribute", doc.MatAttributeDocumenter)
    app.add_directive_to_domain(
        "mat", "autoattribute", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:data", doc.MatDataDocumenter)
    app.add_directive_to_domain(
        "mat", "autodata", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter(
        "mat:instanceattribute", doc.MatInstanceAttributeDocumenter
    )
    app.add_directive_to_domain(
        "mat", "autoinstanceattribute", mat_directives.MatlabAutodocDirective
    )

    app.registry.add_documenter("mat:application", doc.MatApplicationDocumenter)
    app.add_directive_to_domain(
        "mat", "autoapplication", mat_directives.MatlabAutodocDirective
    )

    app.add_autodoc_attrgetter(doc.MatModule, doc.MatModule.getter)
    app.add_autodoc_attrgetter(doc.MatClass, doc.MatClass.getter)

    return {"parallel_read_safe": False}
