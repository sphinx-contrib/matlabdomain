from __future__ import annotations

import os
from os import path
from typing import Any, List, Sequence, cast

from docutils.statemachine import StringList

import sphinx
from sphinx.application import Sphinx
from sphinx.ext.autodoc.importer import import_module
from sphinx.ext.autodoc.mock import mock
from sphinx.locale import __
from sphinx.pycode import ModuleAnalyzer, PycodeError
from sphinx.util import logging, rst
import os
import pkgutil
from os import path
from typing import TYPE_CHECKING, Any, Sequence

from jinja2 import TemplateNotFound
from jinja2.sandbox import SandboxedEnvironment

import sphinx.locale
from sphinx import __display_version__, package_dir
from sphinx.application import Sphinx
from sphinx.builders import Builder
from sphinx.ext.autodoc.importer import import_module

from sphinx.locale import __
from sphinx.pycode import ModuleAnalyzer, PycodeError
from sphinx.util import logging, rst, split_full_qualified_name
from sphinx.util.inspect import getall
from sphinx.util.osutil import ensuredir
from sphinx.util.template import SphinxTemplateLoader
from sphinxcontrib.mat_types import (  # noqa: E401
    MatModule,
    MatObject,
    MatFunction,
    MatClass,
    MatProperty,
    MatMethod,
    MatScript,
    MatException,
    MatModuleAnalyzer,
    MatApplication,
    strip_package_prefix,
)

if TYPE_CHECKING:
    from gettext import NullTranslations
from sphinxcontrib.mat_types import entities_table, entities_name_map

logger = logging.getLogger(__name__)
from sphinx.ext.autosummary.generate import (
    find_autosummary_in_files,
    import_ivar_by_name,
    AutosummaryRenderer,
    ModuleScanner,
    _underline,
)


def get_objtype(obj: Any) -> str:
    if isinstance(obj, MatModule):
        return "module"
    elif isinstance(obj, MatClass):
        return "class"
    elif isinstance(obj, MatFunction):
        return "function"
    elif isinstance(obj, MatMethod):
        return "method"
    elif isinstance(obj, MatProperty):
        return "attribute"
    else:
        return "object"


class MatAutosummaryRenderer(AutosummaryRenderer):
    """A helper class for rendering."""

    def __init__(self, app: Sphinx) -> None:
        if isinstance(app, Builder):
            raise ValueError("Expected a Sphinx application object!")

        system_templates_path = [
            os.path.join(path.abspath(path.dirname(__file__)), "template"),
            os.path.join(package_dir, "ext", "autosummary", "templates"),
        ]
        loader = SphinxTemplateLoader(
            app.srcdir, app.config.templates_path, system_templates_path
        )

        self.env = SandboxedEnvironment(loader=loader)
        self.env.filters["escape"] = rst.escape
        self.env.filters["e"] = rst.escape
        self.env.filters["underline"] = _underline

        if app.translator:
            self.env.add_extension("jinja2.ext.i18n")
            self.env.install_gettext_translations(app.translator)

    def render(self, template_name: str, context: dict) -> str:
        """Render a template file."""
        try:
            template = self.env.get_template(template_name)
        except TemplateNotFound:
            try:
                # objtype is given as template_name
                template = self.env.get_template("mat%s.rst" % template_name)
            except TemplateNotFound:
                # fallback to base.rst
                template = self.env.get_template("matbase.rst")

        return template.render(context)


def generate_autosummary_content(
    name: str,
    obj: Any,
    parent: Any,
    template: MatAutosummaryRenderer,
    template_name: str,
    imported_members: bool,
    app: Any,
    recursive: bool,
    context: dict,
    modname: str | None = None,
    qualname: str | None = None,
) -> str:
    # doc = get_documenter(app, obj, parent)
    objtype = get_objtype(obj)

    def skip_member(obj: Any, name: str, objtype: str) -> bool:
        try:
            return app.emit_firstresult(
                "autodoc-skip-member", objtype, name, obj, False, {}
            )
        except Exception as exc:
            logger.warning(
                __(
                    "autosummary: failed to determine %r to be documented, "
                    "the following exception was raised:\n%s"
                ),
                name,
                exc,
                type="autosummary",
            )
            return False

    def get_class_members(obj: Any) -> dict[str, Any]:
        return entities_table

    def get_module_members(obj: Any) -> dict[str, Any]:
        return entities_table

    def get_all_members(obj: Any) -> dict[str, Any]:
        if objtype == "module":
            return get_module_members(obj)
        elif objtype == "class":
            return get_class_members(obj)
        return {}

    def get_members(
        obj: Any, types: set[str], include_public: list[str] = [], imported: bool = True
    ) -> tuple[list[str], list[str]]:
        items: list[str] = []
        public: list[str] = []

        all_members = get_all_members(obj)
        for name, value in all_members.items():
            # documenter = get_documenter(app, value, obj)
            objtype = get_objtype(value)
            if objtype in types:
                # skip imported members if expected
                if imported or getattr(value, "__module__", None) == obj.__package__:
                    skipped = skip_member(value, name, objtype)
                    if not name.startswith(obj.__package__ + "."):
                        continue
                    if skipped is True:
                        pass
                    elif skipped is False:
                        # show the member forcedly
                        items.append(name)
                        public.append(name)
                    else:
                        items.append(name)
                        if name in include_public or not name.startswith("_"):
                            # considers member as public
                            public.append(name)
        return public, items

    def get_module_attrs(members: Any) -> tuple[list[str], list[str]]:
        """Find module attributes with docstrings."""
        attrs, public = [], []
        try:
            analyzer = ModuleAnalyzer.for_module(name)
            attr_docs = analyzer.find_attr_docs()
            for namespace, attr_name in attr_docs:
                if namespace == "" and attr_name in members:
                    attrs.append(attr_name)
                    if not attr_name.startswith("_"):
                        public.append(attr_name)
        except PycodeError:
            pass  # give up if ModuleAnalyzer fails to parse code
        return public, attrs

    def get_modules(
        obj: Any, skip: Sequence[str], public_members: Sequence[str] | None = None
    ) -> tuple[list[str], list[str]]:
        items: list[str] = []
        public: list[str] = []
        for _, modname, _ispkg in pkgutil.iter_modules(obj.__path__):
            if modname in skip:
                # module was overwritten in __init__.py, so not accessible
                continue
            fullname = name + "." + modname
            try:
                module = import_module(fullname)
                if module and hasattr(module, "__sphinx_mock__"):
                    continue
            except ImportError:
                pass

            items.append(fullname)
            if public_members is not None:
                if modname in public_members:
                    public.append(fullname)
            else:
                if not modname.startswith("_"):
                    public.append(fullname)
        return public, items

    ns: dict[str, Any] = {}
    ns.update(context)

    if objtype == "module":
        scanner = ModuleScanner(app, obj)
        ns["members"] = scanner.scan(imported_members)

        respect_module_all = not app.config.autosummary_ignore_module_all
        imported_members = imported_members or (
            "__all__" in dir(obj) and respect_module_all
        )

        ns["functions"], ns["all_functions"] = get_members(
            obj, {"function"}, imported=imported_members
        )
        ns["classes"], ns["all_classes"] = get_members(
            obj, {"class"}, imported=imported_members
        )
        ns["exceptions"], ns["all_exceptions"] = get_members(
            obj, {"exception"}, imported=imported_members
        )
        ns["attributes"], ns["all_attributes"] = get_module_attrs(ns["members"])
        ispackage = hasattr(obj, "__path__")
        if ispackage and recursive:
            # Use members that are not modules as skip list, because it would then mean
            # that module was overwritten in the package namespace
            skip = (
                ns["all_functions"]
                + ns["all_classes"]
                + ns["all_exceptions"]
                + ns["all_attributes"]
            )

            # If respect_module_all and module has a __all__ attribute, first get
            # modules that were explicitly imported. Next, find the rest with the
            # get_modules method, but only put in "public" modules that are in the
            # __all__ list
            #
            # Otherwise, use get_modules method normally
            if respect_module_all and "__all__" in dir(obj):
                imported_modules, all_imported_modules = get_members(
                    obj, {"module"}, imported=True
                )
                skip += all_imported_modules
                imported_modules = [
                    name + "." + modname for modname in imported_modules
                ]
                all_imported_modules = [
                    name + "." + modname for modname in all_imported_modules
                ]
                public_members = getall(obj)
            else:
                imported_modules, all_imported_modules = [], []
                public_members = None

            modules, all_modules = get_modules(
                obj, skip=skip, public_members=public_members
            )
            ns["modules"] = imported_modules + modules
            ns["all_modules"] = all_imported_modules + all_modules
    elif objtype == "class":
        ns["members"] = dir(obj)
        ns["inherited_members"] = set(dir(obj)) - set(obj.__dict__.keys())
        ns["methods"], ns["all_methods"] = get_members(obj, {"method"}, ["__init__"])
        ns["attributes"], ns["all_attributes"] = get_members(
            obj, {"attribute", "property"}
        )

    if modname is None or qualname is None:
        modname, qualname = split_full_qualified_name(name)

    if objtype in ("method", "attribute", "property"):
        ns["class"] = qualname.rsplit(".", 1)[0]

    if objtype in ("class",):
        shortname = qualname
    else:
        shortname = qualname.rsplit(".", 1)[-1]

    ns["fullname"] = name
    ns["module"] = modname
    ns["objname"] = qualname
    ns["name"] = shortname

    ns["objtype"] = objtype
    ns["underline"] = len(name) * "="

    if template_name:
        return template.render(template_name, ns)
    else:
        return template.render(objtype, ns)


def import_by_name(
    name: str, prefixes: list[str | None] = [None]
) -> tuple[str, Any, Any, str]:
    try:
        obj = entities_table[name]
    except KeyError:
        raise ImportError(f"Could not import {name}")
    name_split = name.split(".")
    if len(name_split) == 1:
        parent = None
        modname = None
    else:
        modname = ".".join(name_split[:-1])
        parent = entities_table[modname]
    return name, obj, parent, modname


# -- Finding documented entries in files ---------------------------------------
from sphinx.ext.autosummary.generate import (
    AutosummaryEntry,
    find_autosummary_in_docstring,
)


def find_autosummary_in_files(filenames: list[str]) -> list[AutosummaryEntry]:
    """Find out what items are documented in source/*.rst.

    See `find_autosummary_in_lines`.
    """
    documented: list[AutosummaryEntry] = []
    for filename in filenames:
        with open(filename, encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()
            documented.extend(find_autosummary_in_lines(lines, filename=filename))
    return documented


import re


def find_autosummary_in_lines(
    lines: list[str],
    module: str | None = None,
    filename: str | None = None,
) -> list[AutosummaryEntry]:
    """Find out what items appear in autosummary:: directives in the
    given lines.

    Returns a list of (name, toctree, template) where *name* is a name
    of an object and *toctree* the :toctree: path of the corresponding
    autosummary directive (relative to the root of the file name), and
    *template* the value of the :template: option. *toctree* and
    *template* ``None`` if the directive does not have the
    corresponding options set.
    """
    autosummary_re = re.compile(r"^(\s*)\.\.\s+autosummary::\s*")
    automodule_re = re.compile(r"^\s*\.\.\s+automodule::\s*([A-Za-z0-9_.]+)\s*$")
    module_re = re.compile(r"^\s*\.\.\s+(current)?module::\s*([a-zA-Z0-9_.]+)\s*$")
    autosummary_item_re = re.compile(r"^\s+(~?[_a-zA-Z][a-zA-Z0-9_.+@]*)\s*.*?")
    recursive_arg_re = re.compile(r"^\s+:recursive:\s*$")
    toctree_arg_re = re.compile(r"^\s+:toctree:\s*(.*?)\s*$")
    template_arg_re = re.compile(r"^\s+:template:\s*(.*?)\s*$")

    documented: list[AutosummaryEntry] = []

    recursive = False
    toctree: str | None = None
    template = None
    current_module = module
    in_autosummary = False
    base_indent = ""

    for line in lines:
        if in_autosummary:
            m = recursive_arg_re.match(line)
            if m:
                recursive = True
                continue

            m = toctree_arg_re.match(line)
            if m:
                toctree = m.group(1)
                if filename:
                    toctree = os.path.join(os.path.dirname(filename), toctree)
                continue

            m = template_arg_re.match(line)
            if m:
                template = m.group(1).strip()
                continue

            if line.strip().startswith(":"):
                continue  # skip options

            m = autosummary_item_re.match(line)
            if m:
                name = m.group(1).strip()
                if name.startswith("~"):
                    name = name[1:]
                if current_module and not name.startswith(current_module + "."):
                    name = f"{current_module}.{name}"
                documented.append(AutosummaryEntry(name, toctree, template, recursive))
                continue

            if not line.strip() or line.startswith(base_indent + " "):
                continue

            in_autosummary = False

        m = autosummary_re.match(line)
        if m:
            in_autosummary = True
            base_indent = m.group(1)
            recursive = False
            toctree = None
            template = None
            continue

        m = automodule_re.search(line)
        if m:
            current_module = m.group(1).strip()
            # recurse into the automodule docstring
            documented.extend(
                find_autosummary_in_docstring(current_module, filename=filename)
            )
            continue

        m = module_re.match(line)
        if m:
            current_module = m.group(2)
            continue

    return documented


def generate_autosummary_docs(
    sources: list[str],
    output_dir: str | None = None,
    suffix: str = ".rst",
    base_path: str | None = None,
    imported_members: bool = False,
    app: Any = None,
    overwrite: bool = True,
    encoding: str = "utf-8",
) -> None:
    showed_sources = sorted(sources)
    if len(showed_sources) > 20:
        showed_sources = showed_sources[:10] + ["..."] + showed_sources[-10:]
    logger.info(
        __("[autosummary] generating autosummary for: %s") % ", ".join(showed_sources)
    )

    if output_dir:
        logger.info(__("[autosummary] writing to %s") % output_dir)

    if base_path is not None:
        sources = [os.path.join(base_path, filename) for filename in sources]

    template = MatAutosummaryRenderer(app)

    # read
    items = find_autosummary_in_files(sources)

    # keep track of new files
    new_files = []

    if app:
        filename_map = app.config.autosummary_filename_map
    else:
        filename_map = {}

    # write
    for entry in sorted(set(items), key=str):
        if entry.path is None:
            # The corresponding autosummary:: directive did not have
            # a :toctree: option
            continue

        path = output_dir or os.path.abspath(entry.path)
        ensuredir(path)

        try:
            name, obj, parent, modname = import_by_name(entry.name)
            if modname:
                qualname = name.replace(modname + ".", "")
            else:
                qualname = name
        except ImportError as exc:
            logger.warning(
                __("[mat_autosummary] failed to import %s.\nPossible hints:\n%s"),
                entry.name,
                exc,
            )
            continue

        context: dict[str, Any] = {}
        if app:
            context.update(app.config.autosummary_context)

        content = generate_autosummary_content(
            name,
            obj,
            parent,
            template,
            entry.template,
            imported_members,
            app,
            entry.recursive,
            context,
            modname,
            qualname,
        )

        filename = os.path.join(path, filename_map.get(name, name) + suffix)
        if os.path.isfile(filename):
            with open(filename, encoding=encoding) as f:
                old_content = f.read()

            if content == old_content:
                continue
            if overwrite:  # content has changed
                with open(filename, "w", encoding=encoding) as f:
                    f.write(content)
                new_files.append(filename)
        else:
            with open(filename, "w", encoding=encoding) as f:
                f.write(content)
            new_files.append(filename)

    # descend recursively to new files
    if new_files:
        generate_autosummary_docs(
            new_files,
            output_dir=output_dir,
            suffix=suffix,
            base_path=base_path,
            imported_members=imported_members,
            app=app,
            overwrite=overwrite,
        )


def process_generate_options(app: Sphinx) -> None:
    genfiles = app.config.autosummary_generate

    if genfiles is True:
        env = app.builder.env
        genfiles = [
            env.doc2path(x, base=False)
            for x in env.found_docs
            if os.path.isfile(env.doc2path(x))
        ]
    elif genfiles is False:
        pass
    else:
        ext = list(app.config.source_suffix)
        genfiles = [
            genfile + (ext[0] if not genfile.endswith(tuple(ext)) else "")
            for genfile in genfiles
        ]

        for entry in genfiles[:]:
            if not path.isfile(path.join(app.srcdir, entry)):
                logger.warning(__("autosummary_generate: file not found: %s"), entry)
                genfiles.remove(entry)

    if not genfiles:
        return

    suffix = get_rst_suffix(app)
    if suffix is None:
        logger.warning(
            __(
                "autosummary generats .rst files internally. "
                "But your source_suffix does not contain .rst. Skipped."
            )
        )
        return

    imported_members = app.config.autosummary_imported_members
    with mock(app.config.autosummary_mock_imports):
        generate_autosummary_docs(
            genfiles,
            suffix=suffix,
            base_path=app.srcdir,
            app=app,
            imported_members=imported_members,
            overwrite=app.config.autosummary_generate_overwrite,
            encoding=app.config.source_encoding,
        )


from sphinx.ext.autosummary import (
    Autosummary,
    get_rst_suffix,
    autosummary_noop,
    autosummary_table,
    autosummary_table_visit_html,
    autosummary_toc,
    autosummary_toc_visit_html,
    get_import_prefixes_from_env,
    mangle_signature,
)


class MatAutosummary(Autosummary):
    def import_by_name(
        self, name: str, prefixes: list[str | None]
    ) -> tuple[str, Any, Any, str]:
        return import_by_name(name, prefixes)

    def get_items(self, names: list[str]) -> list[tuple[str, str, str, str]]:
        """Try to import the given names, and return a list of
        ``[(name, signature, summary_string, real_name), ...]``.
        """
        prefixes = get_import_prefixes_from_env(self.env)

        items: list[tuple[str, str, str, str]] = []

        max_item_chars = 50

        for name in names:
            display_name = name
            if name.startswith("~"):
                name = name[1:]
                display_name = name.split(".")[-1]

            try:
                real_name, obj, parent, modname = self.import_by_name(
                    name, prefixes=prefixes
                )
            except ImportError as exc:
                logger.warning(
                    __("mat_autosummary: failed to import %s.\nPossible hints:\n%s"),
                    name,
                    exc,
                    location=self.get_location(),
                )
                continue

            self.bridge.result = StringList()  # initialize for each documenter
            full_name = real_name
            # if not isinstance(obj, ModuleType):
            #     # give explicitly separated module name, so that members
            #     # of inner classes can be documented
            #     full_name = modname + '::' + full_name[len(modname) + 1:]

            items.append((display_name, "", "", real_name))

            # try to also get a source code analyzer for attribute docs

            # -- Grab the signature

            # -- Grab the summary

            # bodge for ModuleDocumenter

        return items


def setup(app: Sphinx) -> dict[str, Any]:
    # sphinx.ext.autosummary
    app.setup_extension("sphinx.ext.autosummary")

    app.add_directive_to_domain("mat", "autosummary", MatAutosummary)

    # replace autosummary generate with our own
    for listener in app.events.listeners.get("builder-inited", []):
        if listener.handler.__name__ == "process_generate_options":
            app.disconnect(listener.id)
    app.connect("builder-inited", process_generate_options)

    return {"version": sphinx.__display_version__, "parallel_read_safe": True}
