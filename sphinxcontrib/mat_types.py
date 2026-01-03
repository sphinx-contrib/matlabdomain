"""sphinxcontrib.mat_types.
~~~~~~~~~~~~~~~~~~~~~~~

Types for MATLAB.

:copyright: Copyright 2014-2024 by the sphinxcontrib-matlabdomain team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import builtins
import os
import xml.etree.ElementTree as ET
from importlib.metadata import version
from zipfile import ZipFile

from sphinx.util.logging import getLogger
from tree_sitter import Parser

from sphinxcontrib.mat_tree_sitter_parser import (
    ML_LANG,
    MatClassParser,
    MatFunctionParser,
    MatScriptParser,
)

logger = getLogger("matlab-domain")

__all__ = [
    "MatApplication",
    "MatClass",
    "MatEnumeration",
    "MatException",
    "MatFunction",
    "MatMethod",
    "MatModule",
    "MatModuleAnalyzer",
    "MatObject",
    "MatProperty",
    "MatScript",
]


# MATLAB attribute type dictionaries.

# From:
#  - http://www.mathworks.com/help/matlab/matlab_oop/class-attributes.html
MATLAB_CLASS_ATTRIBUTE_TYPES = {
    "Abstract": bool,
    "AllowedSubclasses": list,
    "ConstructOnLoad": bool,
    "HandleCompatible": bool,
    "Hidden": bool,
    "InferiorClasses": list,
    "Sealed": bool,
    "SharedTestFixtures": list,
    "TestTags": list,
}

# From:
#  - https://mathworks.com/help/matlab/matlab_oop/property-attributes.html
#  - https://mathworks.com/help/matlab/matlab_prog/define-property-attributes-1.htm
#  - https://mathworks.com/help/matlab/ref/matlab.unittest.testcase-class.html
MATLAB_PROPERTY_ATTRIBUTE_TYPES = {
    "AbortSet": bool,
    "Abstract": bool,
    "Access": list,
    "ClassSetupParameter": bool,
    "Constant": bool,
    "Dependent": bool,
    "DiscreteState": bool,
    "GetAccess": list,
    "GetObservable": bool,
    "Hidden": bool,
    "MethodSetupParameter": bool,
    "NonCopyable": bool,
    "Nontunable": bool,
    "PartialMatchPriority": bool,
    "SetAccess": list,
    "SetObservable": bool,
    "TestParameter": bool,
    "Transient": bool,
}

# From
#  - https://mathworks.com/help/matlab/matlab_oop/method-attributes.html
#  - https://mathworks.com/help/matlab/ref/matlab.unittest.testcase-class.html
MATLAB_METHOD_ATTRIBUTE_TYPES = {
    "Abstract": bool,
    "Access": list,
    "Hidden": bool,
    "ParameterCombination": bool,
    "Sealed": list,
    "Static": bool,
    "Test": bool,
    "TestClassSetup": bool,
    "TestClassTeardown": bool,
    "TestMethodSetup": bool,
    "TestMethodTeardown": bool,
    "TestTags": list,
}

# Dictionary containing all MATLAB entities that are found in `matlab_src_dir`.
# The dictionary keys are both the full dotted path, relative to the root.
# Further, "short names" are added. Example:
#   Given a dotted path of: target.+package.ClassBar
#   Will result in a short name of: package.ClassBar
entities_table = {}

# Dictionary containing a map of names WITHOUT '+' in package names to
# the corresponding names WITH '+' in the package name. This is only
# used if "matlab_auto_link" is on AND "matlab_keep_package_prefix"
# is True AND a docstring with "see also" is encountered.
entities_name_map = {}


def shortest_name(dotted_path):
    # Creates the shortest valid MATLAB name from a dotted path
    parts = dotted_path.split(".")
    if len(parts) == 1:
        return parts[0].lstrip("+")

    if "@" in dotted_path:
        return dotted_path

    parts_to_keep = []
    for part in parts[:-1]:
        if part.startswith("+"):
            parts_to_keep.append(part.lstrip("+"))
        elif len(parts_to_keep) > 0:
            parts_to_keep = []
    parts_to_keep.append(parts[-1].lstrip("+"))
    return ".".join(parts_to_keep)


def classfolder_class_name(dotted_path):
    # Returns a @ClassFolder classname if applicable, otherwise the dotted_path is returned
    #
    if "@" not in dotted_path:
        return dotted_path

    parts = dotted_path.split(".")
    if len(parts) == 1:
        return dotted_path

    stripped_parts = [part.lstrip("@") for part in parts]

    if stripped_parts[-1] == stripped_parts[-2]:
        return ".".join([*parts[0:-2], stripped_parts[-1]])
    else:
        return dotted_path


def recursive_find_all(obj):
    # Recursively finds all entities in all "modules" aka directories.
    for _, o in obj.entities:
        if isinstance(o, MatModule):
            o.safe_getmembers()
            if o.entities:
                recursive_find_all(o)


def recursive_log_debug(obj, indent=""):
    # Traverse the object hierarchy and log to debug
    for n, o in obj.entities:
        logger.debug(
            "[sphinxcontrib-matlabdomain] %s Name=%s, Entity=%s", indent, n, str(o)
        )
        if isinstance(o, MatModule):
            if o.entities:
                indent = indent + " "
                names = [n_ for n_, o_ in o.entities]
                logger.debug(
                    "[sphinxcontrib-matlabdomain] %s Names=%s", indent, str(names)
                )
                recursive_log_debug(o, indent)
                indent = indent[:-1]
        if isinstance(o, MatClass):
            logger.debug(
                "[sphinxcontrib-matlabdomain] %s -> name=%s, methods=%s",
                indent,
                str(o.name),
                str(o.methods),
            )


def populate_entities_table(obj, path=""):
    # Recursively scan the hiearachy of entities and populate the entities_table.
    for _n, o in obj.entities:
        fullpath = path + "." + o.name
        fullpath = fullpath.lstrip(".")
        entities_table[fullpath] = o
        entities_name_map[strip_package_prefix(fullpath)] = fullpath
        if isinstance(o, MatModule):
            if o.entities:
                populate_entities_table(o, fullpath)


def try_get_module_entity_or_default(entity_name):
    maybe_mod = entities_table.get(entity_name)
    if isinstance(maybe_mod, dict):
        return maybe_mod["mod"]
    return maybe_mod


def analyze(app):
    # Using the "MatObject.matlabify" and "MatModule.safe_getmembers" the
    # `matlab_src_dir` is recursively scanned for MATLAB objects only once.
    # All entities found are stored in globally available `entities_table`

    if app.env.config.matlab_src_dir is None:
        logger.debug(
            "[sphinxcontrib-matlabdomain] matlab_src_dir is None, skipping parsing."
        )
        return

    # Interpret `matlab_src_dir` relative to the sphinx source directory.
    basedir = os.path.normpath(
        os.path.join(app.env.srcdir, app.env.config.matlab_src_dir)
    )
    MatObject.basedir = basedir  # set MatObject base directory
    MatObject.sphinx_env = app.env  # pass env to MatObject cls
    MatObject.sphinx_app = app  # pass app to MatObject cls

    entities_table.clear()
    entities_name_map.clear()

    # Set the root object and get root members.
    root = MatObject.matlabify("")
    if not root:
        return
    root.safe_getmembers()
    recursive_find_all(root)

    # Print the hierarchy of entities to the log.
    logger.debug("[sphinxcontrib-matlabdomain] Found the following entities:")
    recursive_log_debug(root)

    populate_entities_table(root)
    entities_table["."] = root

    def isClassFolderModule(name, entity):
        if not isinstance(entity, MatModule):
            return False

        parts = name.split(".")
        return parts[-1].startswith("@")

    class_folder_modules = {
        k: v for k, v in entities_table.items() if isClassFolderModule(k, v)
    }
    # For each Class Folder module
    for cf_entity in class_folder_modules.values():
        # Find the class entity class.
        class_entities = [e for e in cf_entity.entities if isinstance(e[1], MatClass)]
        func_entities = [e for e in cf_entity.entities if isinstance(e[1], MatFunction)]

        if not class_entities:
            continue
        assert len(class_entities) == 1
        cls = class_entities[0][1]

        # Add functions to class
        for _func_name, func in func_entities:
            func.__class__ = MatMethod
            func.cls = cls
            # TODO: Find the method attributes defined in classfolder class definition.
            func.attrs = {}
            cls.methods[func.name] = func

    # Transform @ClassFolder names. Specifically
    class_folder_names = {}
    for name, entity in entities_table.items():
        alt_name = classfolder_class_name(name)
        if name != alt_name:
            class_folder_names[alt_name] = entity
    entities_table.update(class_folder_names)

    # Find alternative names to entities
    # target.+package.+sub.Class -> package.sub.Class
    # folder.subfolder.Class -> Class
    #
    # NOTE: Does not yet work with class folders
    short_names = {}
    long_names = entities_table.keys()
    for name, entity in entities_table.items():
        short_name = shortest_name(name)
        if (
            short_name != name and not (short_name in long_names and name in long_names)
        ) or (
            short_name in long_names
            and (entity.ref_role() == "func" or entity.ref_role() == "class")
            and entities_table[short_name].ref_role() == "mod"
        ):
            # Only handle the below special case when overwriting entries in entities_table will not
            # introduce conflicts
            if short_name in entities_table:
                # Special Case - ClassName/ClassName.m
                existing_entity = entities_table[short_name]
                short_names[short_name] = {
                    entity.ref_role(): entity,
                    existing_entity.ref_role(): existing_entity,
                }
            else:
                short_names[short_name] = entity
            entities_name_map[short_name] = short_name

    entities_table.update(short_names)


def strip_package_prefix(varname):
    """Remove the leading '+' prefix on package names."""
    if not varname:
        return varname

    return ".".join([s.lstrip("+") for s in varname.split(".")])


class MatObject:
    """Base MATLAB object to which all others are subclassed.

    :param name: Name of MATLAB object.
    :type name: str

    MATLAB objects can be :class:`MatModule`, :class:`MatFunction`,
    :class:`MatApplication` or :class:`MatClass`.
    :class:`MatModule` are just folders that define a pseudo
    namespace for :class:`MatFunction`, :class:`MatApplication`
    and :class:`MatClass` in that folder.
    :class:`MatFunction` and :class:`MatClass` must begin with either
    ``function`` or ``classdef`` keywords.
    :class:`MatApplication` must be a ``.mlapp`` file.
    """

    basedir = None
    encoding = None
    sphinx_env = None
    sphinx_app = None

    def __init__(self, name):
        #: name of MATLAB object
        self.name = name

    def ref_role(self):
        """Return role to use for references to this object (e.g. when generating auto-links)."""
        return "ref"

    @property
    def __name__(self):
        return self.name

    def __repr__(self):
        # __str__() method not required, if not given, then __repr__() used
        return f'<{self.__class__.__name__}: "{self.name}">'

    def getter(self, name, *defargs):
        if name == "__name__":
            return self.__name__
        elif len(defargs) == 0:
            logger.debug(
                '[sphinxcontrib-matlabdomain] Warning attribute "%s" was not found in %s.',
                name,
                self,
            )
            return None
        elif len(defargs) == 1:
            return defargs[0]
        else:
            return defargs

    @staticmethod
    def matlabify(objname):
        """Make a MatObject.

        :param objname: Name of object to matlabify without file extension.
        :type objname: str

        Assumes that object is contained in a folder described by a namespace
        composed of modules and packages connected by dots, and that the top-
        level module or package is in the Sphinx config value
        ``matlab_src_dir`` which is stored locally as
        :attr:`MatObject.basedir`. For example:
        ``my_project.my_package.sub_pkg.MyClass`` represents either a folder
        ``basedir/my_project/my_package/sub_pkg/MyClass`` or an mfile
        ``basedir/my_project/my_package/sub_pkg/ClassExample.m``. If there is both a
        folder and an mfile with the same name, the folder takes precedence
        over the mfile.
        """
        # no object name given
        logger.debug(f"[sphinxcontrib-matlabdomain] enter matlabify {objname=}.")

        if objname is None:
            return None
        if objname == "":
            path, name = os.path.split(MatObject.basedir)
            package = ""
            objname = name
            fullpath = MatObject.basedir
        else:
            # matlab modules are really packages
            objname = objname.lstrip(".")
            package = objname  # for packages it's namespace of __init__.py
            # convert namespace to path
            objname = objname.replace(".", os.sep)  # objname may have dots
            # separate path from file/folder name
            path, name = os.path.split(objname)

            # make a full path out of basedir and objname
            fullpath = os.path.join(MatObject.basedir, objname)  # objname fullpath

        logger.debug(
            f"[sphinxcontrib-matlabdomain] matlabify {package=}, {objname=}, {fullpath=}"
        )
        # package folders imported over mfile with same name
        if os.path.isdir(fullpath):
            if package.startswith("_") or package.startswith("."):
                return None
            mod = try_get_module_entity_or_default(package)
            if mod:
                logger.debug(
                    "[sphinxcontrib-matlabdomain] Module %s already loaded.", package
                )
                return mod
            else:
                logger.debug(
                    f"[sphinxcontrib-matlabdomain] matlabify MatModule {package=}, {fullpath=}"
                )
                return MatModule(name, fullpath, package)  # import package
        elif os.path.isfile(fullpath + ".m"):
            mfile = fullpath + ".m"
            logger.debug(
                f"[sphinxcontrib-matlabdomain] matlabify parse_mfile {package=}, {mfile=}"
            )
            return MatObject.parse_mfile(
                mfile, name, path, MatObject.encoding
            )  # parse mfile
        elif os.path.isfile(fullpath + ".mlapp"):
            mlappfile = fullpath + ".mlapp"
            logger.debug(
                f"[sphinxcontrib-matlabdomain] matlabify parse_mlappfile {package=}, {mlappfile=}"
            )
            return MatObject.parse_mlappfile(mlappfile, name, path)
        return None

    @staticmethod
    def parse_mfile(mfile, name, path, encoding=None):
        """Use Pygments to parse mfile to determine type: function or class.

        :param mfile: Full path of mfile.
        :type mfile: str
        :param name: Name of :class:`MatObject`.
        :type name: str
        :param path: Path of module containing :class:`MatObject`.
        :type path: str
        :param encoding: Encoding of the Matlab file to load (default = utf-8)
        :type encoding: str
        :returns: :class:`MatObject` that represents the type of mfile.

        Assumes that the first token in the file is either one of the keywords:
        "classdef" or "function" otherwise it is assumed to be a script.

        File encoding can be set using sphinx config ``matlab_src_encoding``
        Default behaviour : replaces parsing errors with ? chars
        """
        # use Pygments to parse mfile to determine type: function/classdef
        # read mfile code
        if encoding is None:
            encoding = "utf-8"
        with builtins.open(mfile, "rb") as code_f:
            code = code_f.read()

        # parse the file
        tree_sitter_ver = tuple([int(sec) for sec in version("tree_sitter").split(".")])
        if tree_sitter_ver[1] == 21:
            parser = Parser()
            parser.set_language(ML_LANG)
        else:
            parser = Parser(ML_LANG)
        tree = parser.parse(code)

        modname = path.replace(os.sep, ".")  # module name

        # assume that functions and classes always start with a keyword
        def isFunction(tree):
            q_is_function = ML_LANG.query(
                r"""(source_file [(comment) "\n"]* (function_definition))"""
            )
            matches = q_is_function.matches(tree.root_node)
            return bool(matches)

        def isClass(tree):
            q_is_class = ML_LANG.query("(class_definition)")
            matches = q_is_class.matches(tree.root_node)
            return bool(matches)

        if isClass(tree):
            logger.debug(
                "[sphinxcontrib-matlabdomain] parsing classdef %s from %s.",
                name,
                modname,
            )
            return MatClass(name, modname, tree.root_node, encoding)
        elif isFunction(tree):
            logger.debug(
                "[sphinxcontrib-matlabdomain] parsing function %s from %s.",
                name,
                modname,
            )
            return MatFunction(name, modname, tree.root_node, encoding)
        else:
            return MatScript(name, modname, tree.root_node, encoding)

    @staticmethod
    def parse_mlappfile(mlappfile, name, path):
        """Use ZipFile to read the metadata/appMetadata.xml file and
        the metadata/coreProperties.xml file description tags.
        Parses XML content using ElementTree.

        :param mlappfile: Full path of ``.mlapp`` file.
        :type mlappfile: str
        :param name: Name of :class:`MatApplication`.
        :type name: str
        :param path: Path of module containing :class:`MatApplication`.
        :type path: str
        :returns: :class:`MatApplication` representing the application.
        """
        # Read contents of meta-data file
        # This might change in different Matlab versions
        # Note: `code` is a verbatim copy of the MATLAB source inside the App
        #       Variable `codeText` will contain the source.
        with ZipFile(mlappfile, "r") as mlapp:
            meta = ET.fromstring(mlapp.read("metadata/appMetadata.xml"))
            core = ET.fromstring(mlapp.read("metadata/coreProperties.xml"))

        metaNs = {"ns": "http://schemas.mathworks.com/appDesigner/app/2017/appMetadata"}
        coreNs = {
            "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
            "dc": "http://purl.org/dc/elements/1.1/",
            "dcmitype": "http://purl.org/dc/dcmitype/",
            "dcterms": "http://purl.org/dc/terms/",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        }

        coreDesc = core.find("dc:description", coreNs)
        metaDesc = meta.find("ns:description", metaNs)

        doc = []
        if coreDesc is not None and coreDesc.text is not None:
            doc.append(coreDesc.text)
        if metaDesc is not None and metaDesc.text is not None:
            doc.append(metaDesc.text)
        docstring = "\n\n".join(doc)

        modname = path.replace(os.sep, ".")  # module name

        return MatApplication(name, modname, docstring)


# TODO: get docstring and __all__ from contents.m if exists
class MatModule(MatObject):
    """All MATLAB modules are packages. A package is a folder that serves as the
    namespace for any :class:`MatObjects` in the package folder. Sphinx will
    treats objects without a namespace as builtins, so all MATLAB projects
    should be packaged in a folder so that they will have a namespace. This
    can also be accomplished by using the MATLAB +folder package scheme.

    :param name: Name of :class:`MatObject`.
    :type name: str
    :param path: Path of folder containing :class:`MatObject`.
    :type path: str
    """

    def __init__(self, name, path, package):
        super().__init__(name)
        #: Path to module on disk, path to package's __init__.py
        self.path = path
        #: name of package (full path from basedir to module)
        self.package = package
        #: entities found in the module: class, function, module (subpath and +package)
        self.entities = []

    def ref_role(self):
        """Return role to use for references to this object (e.g. when generating auto-links)."""
        return "mod"

    def safe_getmembers(self):
        logger.debug(
            f"[sphinxcontrib-matlabdomain] MatModule.safe_getmembers {self.name=}, {self.path=}, {self.package=}"
        )
        if self.entities:
            return self.entities

        results = []
        for key in os.listdir(self.path):
            # make full path
            path = os.path.join(self.path, key)
            # Do not visit directories starting with:
            # 1) "." (VCS and Editors)
            # 2) "_" (build/temp folders in Sphinx)
            if os.path.isdir(path) and (key.startswith(".") or key.startswith("_")):
                continue
            # Only visit MATLAB files
            if os.path.isfile(path) and not (
                key.endswith(".m") or key.endswith(".mlapp")
            ):
                continue
            # trim file extension
            if os.path.isfile(path):
                key, _ = os.path.splitext(key)
            if not results or key not in next(zip(*results, strict=False)):
                value = self.getter(key, None)
                if value:
                    results.append((key, value))
        self.entities = results

        return results

    @property
    def __doc__(self):
        return None

    @property
    def __all__(self):
        return self.entities

    @property
    def __path__(self):
        return [self.path]

    @property
    def __file__(self):
        return self.path

    @property
    def __package__(self):
        return self.package

    def getter(self, name):
        """:class:`MatModule` ``getter`` method to get attributes."""
        if name == "__name__":
            return self.__name__
        elif name == "__doc__":
            return self.__doc__
        elif name == "__all__":
            return self.__all__
        elif name == "__file__":
            return self.__file__
        elif name == "__path__":
            return self.__path__
        elif name == "__package__":
            return self.__package__
        elif name == "__module__":
            logger.debug(
                "[sphinxcontrib-matlabdomain] mod %s is a package does not have __module__.",
                self,
            )
            return None
        else:
            # Search if we already has this entity
            for entity_name, entity_content in self.entities:
                if name == entity_name:
                    logger.debug(
                        "[sphinxcontrib-matlabdomain] mod %s already has entity %s.",
                        self,
                        name,
                    )
                    return entity_content
            # If not - try to MATLABIFY it.
            entity = MatObject.matlabify(f"{self.package}.{name}")
            if entity:
                self.entities.append((name, entity))
                logger.debug(
                    f"[sphinxcontrib-matlabdomain] entity {name=} imported from {self=}"
                )
                return entity


class MatFunction(MatObject):
    """A MATLAB function.

    :param name: Name of :class:`MatObject`.
    :type name: str
    :param modname: Name of folder containing :class:`MatObject`.
    :type modname: str
    :param tokens: List of tokens parsed from mfile by Pygments.
    :type tokens: list
    """

    def __init__(self, name, modname, tokens, encoding):
        super().__init__(name)
        parsed_function = MatFunctionParser(tokens, encoding)
        #: Path of folder containing :class:`MatObject`.
        self.module = modname
        #: docstring
        self.docstring = parsed_function.docstring
        #: output args
        self.retv = parsed_function.retv
        #: input args
        self.args = parsed_function.args
        #: remaining tokens after main function is parsed
        self.rem_tks = None

    def ref_role(self):
        """Return role to use for references to this object (e.g. when generating auto-links)."""
        return "func"

    @property
    def __doc__(self):
        return self.docstring

    @property
    def __module__(self):
        return self.module

    def getter(self, name, *defargs):
        if name == "__name__":
            return self.__name__
        elif name == "__doc__":
            return self.__doc__
        elif name == "__module__":
            return self.__module__
        else:
            super().getter(name, *defargs)


class MatClass(MatObject):
    """A MATLAB class definition.

    :param name: Name of :class:`MatObject`.
    :type name: str
    :param path: Path of folder containing :class:`MatObject`.
    :type path: str
    :param tokens: List of tokens parsed from mfile by Pygments.
    :type tokens: list
    """

    def __init__(self, name, modname, tokens, encoding):
        super().__init__(name)
        parsed_class = MatClassParser(tokens, encoding)
        #: Path of folder containing :class:`MatObject`.
        self.module = modname
        #: dictionary of class attributes
        self.attrs = parsed_class.attrs
        #: list of class superclasses
        self.bases = parsed_class.supers
        #: docstring
        self.docstring = parsed_class.docstring
        #: dictionary of class properties
        self.properties = parsed_class.properties
        #: dictionary of class methods
        self.methods = {
            name: MatMethod(name, parsed_fun, modname, self)
            for (name, parsed_fun) in parsed_class.methods.items()
        }
        #:
        self.enumerations = parsed_class.enumerations
        #: remaining tokens after main class definition is parsed
        self.rem_tks = None

    def ref_role(self):
        """Return role to use for references to this object (e.g. when generating auto-links)."""
        return "class"

    def fullname(self, env):
        """Return full name for class object, for use as link target."""
        modname = self.__module__
        classname = self.name
        if env.config.matlab_short_links:
            # modname is only used for package names
            # - "target.+package" => "package"
            # - "target" => ""
            parts = modname.split(".")
            parts = [part for part in parts if part.startswith("+")]
            modname = ".".join(parts)

        if not env.config.matlab_keep_package_prefix:
            modname = strip_package_prefix(modname)

        return f"{modname}.{classname}".lstrip(".")

    def link(self, env, name=None):
        """Return link for class object."""
        target = self.fullname(env)
        if name:
            return f":class:`{name} <{target}>`"
        else:
            return f":class:`{target}`"

    @property
    def __module__(self):
        return self.module

    @property
    def __doc__(self):
        return self.docstring

    @property
    def __bases__(self):
        bases_ = dict.fromkeys(list(self.bases))  # make copy of bases

        class_entity_table = {
            name: entity
            for name, entity in entities_table.items()
            if isinstance(entity, MatClass) or "@" in name
        }

        for base in bases_:
            if base in class_entity_table:
                bases_[base] = class_entity_table[base]

        return bases_

    def getter(self, name, *defargs):
        """:class:`MatClass` ``getter`` method to get attributes."""
        if name == "__name__":
            return self.__name__
        elif name == "__doc__":
            return self.__doc__
        elif name == "__module__":
            return self.__module__
        elif name == "__bases__":
            return self.__bases__
        elif name in self.properties:
            return MatProperty(name, self, self.properties[name])
        elif name in self.enumerations:
            return MatEnumeration(name, self, self.enumerations[name])
        elif name in self.methods:
            return self.methods[name]
        elif name in self.enumerations:
            return
        elif name == "__dict__":
            objdict = {pn: self.getter(pn) for pn in self.properties}
            objdict.update(self.methods)
            objdict.update({en: self.getter(en) for en in self.enumerations})
            return objdict
        else:
            super().getter(name, *defargs)


class MatProperty(MatObject):
    def __init__(self, name, cls, attrs):
        super().__init__(name)
        self.cls = cls
        self.attrs = attrs["attrs"]
        self.default = attrs["default"]
        self.docstring = attrs["docstring"]
        self.size = attrs["size"]
        self.type = attrs["type"]
        self.validators = attrs["validators"]

    def ref_role(self):
        """Return role to use for references to this object (e.g. when generating auto-links)."""
        return "attr"

    @property
    def __module__(self):
        return self.cls.module

    @property
    def __doc__(self):
        return self.docstring


class MatEnumeration(MatObject):
    def __init__(self, name, cls, attrs):
        super().__init__(name)
        self.cls = cls
        self.docstring = attrs["docstring"]

    def ref_role(self):
        """Return role to use for references to this object (e.g. when generating auto-links)."""
        return "enum"

    @property
    def __module__(self):
        return self.cls.module

    @property
    def __doc__(self):
        return self.docstring


class MatMethod(MatFunction):
    def __init__(self, name, parsed_function, modname, cls):
        self.name = name
        #: Path of folder containing :class:`MatObject`.
        self.module = modname
        #: docstring
        self.docstring = parsed_function.docstring
        #: output args
        self.retv = parsed_function.retv
        #: input args
        self.args = parsed_function.args
        self.cls = cls
        self.attrs = parsed_function.attrs

    def ref_role(self):
        """Return role to use for references to this object (e.g. when generating auto-links)."""
        return "meth"

    @property
    def __module__(self):
        return self.module

    @property
    def __doc__(self):
        return self.docstring


class MatScript(MatObject):
    def __init__(self, name, modname, tks, encoding):
        super().__init__(name)
        parsed_script = MatScriptParser(tks, encoding)
        #: Path of folder containing :class:`MatScript`.
        self.module = modname
        #: List of tokens parsed from mfile by Pygments.
        self.tokens = tks
        #: docstring
        self.docstring = parsed_script.docstring

    @property
    def __doc__(self):
        return self.docstring

    @property
    def __module__(self):
        return self.module


class MatApplication(MatObject):
    """Representation of the documentation in a Matlab Application.

    :param name: Name of :class:`MatObject`.
    :type name: str
    :param modname: Name of folder containing :class:`MatObject`.
    :type modname: str
    :param desc: Summary and description string.
    :type desc: str
    """

    def __init__(self, name, modname, desc):
        super().__init__(name)
        #: Path of folder containing :class:`MatApplication`.
        self.module = modname
        #: docstring
        self.docstring = desc

    @property
    def __doc__(self):
        return self.docstring

    @property
    def __module__(self):
        return self.module


class MatException(MatObject):
    def __init__(self, name, path, tks):
        super().__init__(name)
        self.path = path
        self.tks = tks
        self.docstring = ""

    @property
    def __doc__(self):
        return self.docstring


class MatcodeError(Exception):
    def __str__(self):
        res = self.args[0]
        if len(self.args) > 1:
            res += f" (exception was: {self.args[1]!r})"
        return res


class MatModuleAnalyzer:
    # cache for analyzer objects -- caches both by module and file name
    cache = {}

    @classmethod
    def for_folder(cls, dirname, modname):
        if ("folder", dirname) in cls.cache:
            return cls.cache["folder", dirname]
        obj = cls(None, modname, dirname, True)
        cls.cache["folder", dirname] = obj
        return obj

    @classmethod
    def for_module(cls, modname):
        if ("module", modname) in cls.cache:
            entry = cls.cache["module", modname]
            if isinstance(entry, MatcodeError):
                raise entry
            return entry
        mod = try_get_module_entity_or_default(modname)
        if isinstance(mod, MatModule):
            obj = cls.for_folder(mod.path, modname)
        elif isinstance(mod, MatClass):
            obj = cls.for_folder(mod.module, modname)
        else:
            err = MatcodeError(f"error importing {modname!r}")
            cls.cache["module", modname] = err
            raise err
        cls.cache["module", modname] = obj
        return obj

    def __init__(self, source, modname, srcname):
        # name of the module
        self.modname = modname
        # name of the source file
        self.srcname = srcname
        # file-like object yielding source lines
        self.source = source
        # cache the source code as well
        self.encoding = None
        self.code = None
        # will be filled by tokenize()
        self.tokens = None
        # will be filled by parse()
        self.parsetree = None
        # will be filled by find_attr_docs()
        self.attr_docs = None
        self.tagorder = None
        # will be filled by find_tags()
        self.tags = None

    def find_attr_docs(self):
        """Find class and module-level attributes and their documentation."""
        if self.attr_docs is not None:
            return self.attr_docs
        attr_visitor_collected = {}
        attr_visitor_tagorder = {}
        tagnumber = 0
        mod = try_get_module_entity_or_default(self.modname)

        # walk package tree
        for k, v in mod.safe_getmembers():
            if hasattr(v, "docstring"):
                attr_visitor_collected[mod.package, k] = v.docstring
                attr_visitor_tagorder[k] = tagnumber
                tagnumber += 1
            if isinstance(v, MatClass):
                for mk, mv in v.getter("__dict__").items():
                    namespace = f"{mod.package}.{k}"
                    namespace = namespace.lstrip(".")
                    tagname = f"{k}.{mk}"
                    tagname = tagname.lstrip(".")
                    attr_visitor_collected[namespace, mk] = mv.docstring
                    attr_visitor_tagorder[tagname] = tagnumber
                    tagnumber += 1
        self.attr_docs = attr_visitor_collected
        self.tagorder = attr_visitor_tagorder
        return attr_visitor_collected
