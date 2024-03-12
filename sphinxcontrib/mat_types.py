"""
    sphinxcontrib.mat_types
    ~~~~~~~~~~~~~~~~~~~~~~~

    Types for MATLAB.

    :copyright: Copyright 2014-2024 by the sphinxcontrib-matlabdomain team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from io import open  # for opening files with encoding in Python 2
import os
from copy import copy
import sphinx.util
from sphinxcontrib.mat_lexer import MatlabLexer
from pygments.token import Token
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import sphinxcontrib.mat_parser as mat_parser

logger = sphinx.util.logging.getLogger("matlab-domain")

__all__ = [
    "MatObject",
    "MatModule",
    "MatFunction",
    "MatClass",
    "MatProperty",
    "MatMethod",
    "MatScript",
    "MatException",
    "MatModuleAnalyzer",
    "MatApplication",
]

# MATLAB keywords that increment keyword-end pair count
MATLAB_KEYWORD_REQUIRES_END = list(
    zip(
        (Token.Keyword,) * 7,
        ("arguments", "for", "if", "switch", "try", "while", "parfor"),
    )
)


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
        return ".".join(parts[0:-2] + [stripped_parts[-1]])
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
                # print(indent + f"{names=}")
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
    for n, o in obj.entities:
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

    # Transform Class Folders classes from
    #
    # @ClassFolder (Module)
    #     ClassFolder (Class)
    #     method1 (Function)
    #     method2 (Function)
    #
    # To
    #
    # ClassFolder (Class) with the method1 and method2 add to the ClassFolder Class.

    def isClassFolderModule(name, entity):
        if not isinstance(entity, MatModule):
            return False

        parts = name.split(".")
        return parts[-1].startswith("@")

    class_folder_modules = {
        k: v for k, v in entities_table.items() if isClassFolderModule(k, v)
    }
    # For each Class Folder module
    for cf_name, cf_entity in class_folder_modules.items():
        # Find the class entity class.
        class_entities = [e for e in cf_entity.entities if isinstance(e[1], MatClass)]
        func_entities = [e for e in cf_entity.entities if isinstance(e[1], MatFunction)]

        if not class_entities:
            continue
        assert len(class_entities) == 1
        cls = class_entities[0][1]

        # Add functions to class
        for func_name, func in func_entities:
            func.__class__ = MatMethod
            func.cls = cls
            # TODO: Find the method attributes defined in classfolder class defintion.
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
            short_name != name
            and not (short_name in long_names and name in long_names)
            or short_name in long_names
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
    """Remove the leading '+' prefix on package names"""

    if not varname:
        return varname

    return ".".join([s.lstrip("+") for s in varname.split(".")])


class MatObject(object):
    """
    Base MATLAB object to which all others are subclassed.

    :param name: Name of MATLAB object.
    :type name: str

    MATLAB objects can be :class:`MatModule`, :class:`MatFunction`,
    :class:`MatApplication` or :class:`MatClass`.
    :class:`MatModule` are just folders that define a psuedo
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
        """Returns role to use for references to this object (e.g. when generating auto-links)"""
        return "ref"

    @property
    def __name__(self):
        return self.name

    def __repr__(self):
        # __str__() method not required, if not given, then __repr__() used
        return '<%s: "%s">' % (self.__class__.__name__, self.name)

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
        """
        Makes a MatObject.

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
        """
        Use Pygments to parse mfile to determine type: function or class.

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
        with open(mfile, "r", encoding=encoding, errors="replace") as code_f:
            code = code_f.read().replace("\r\n", "\n")

        full_code = code

        # remove the top comment header (if there is one) from the code string
        code = mat_parser.remove_comment_header(code)
        code = mat_parser.remove_line_continuations(code)
        code = mat_parser.fix_function_signatures(code)

        tks = list(MatlabLexer().get_tokens(code))

        modname = path.replace(os.sep, ".")  # module name

        # assume that functions and classes always start with a keyword
        def isFunction(token):
            return token == (Token.Keyword, "function")

        def isClass(token):
            return token == (Token.Keyword, "classdef")

        if isClass(tks[0]):
            logger.debug(
                "[sphinxcontrib-matlabdomain] parsing classdef %s from %s.",
                name,
                modname,
            )
            return MatClass(name, modname, tks)
        elif isFunction(tks[0]):
            logger.debug(
                "[sphinxcontrib-matlabdomain] parsing function %s from %s.",
                name,
                modname,
            )
            return MatFunction(name, modname, tks)
        else:
            # it's a script file retoken with header comment
            tks = list(MatlabLexer().get_tokens(full_code))
            return MatScript(name, modname, tks)
        return None

    @staticmethod
    def parse_mlappfile(mlappfile, name, path):
        """
        Uses ZipFile to read the metadata/appMetadata.xml file and
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
            # code = ET.fromstring(mlapp.read("matlab/document.xml"))

        metaNs = {"ns": "http://schemas.mathworks.com/appDesigner/app/2017/appMetadata"}
        coreNs = {
            "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
            "dc": "http://purl.org/dc/elements/1.1/",
            "dcmitype": "http://purl.org/dc/dcmitype/",
            "dcterms": "http://purl.org/dc/terms/",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        }
        # codeNs = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

        coreDesc = core.find("dc:description", coreNs)
        metaDesc = meta.find("ns:description", metaNs)
        # codeDesc = code.find(".//w:t", codeNs)
        # codeText = codeDesc.text

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
    """
    All MATLAB modules are packages. A package is a folder that serves as the
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
        super(MatModule, self).__init__(name)
        #: Path to module on disk, path to package's __init__.py
        self.path = path
        #: name of package (full path from basedir to module)
        self.package = package
        #: entities found in the module: class, function, module (subpath and +package)
        self.entities = []

    def ref_role(self):
        """Returns role to use for references to this object (e.g. when generating auto-links)"""
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
            # - "." (VCS and Editors)
            # - "_" (build/temp folders in Sphinx)
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
            if not results or key not in list(zip(*results))[0]:
                value = self.getter(key, None)
                if value:
                    results.append((key, value))
        self.entities = results
        # results.sort()
        return results

    @property
    def __doc__(self):
        return None

    @property
    def __all__(self):
        return self.entities
        # results = self.safe_getmembers()
        # if results:
        #     results = list(zip(*self.safe_getmembers()))[0]
        # return results

    @property
    def __path__(self):
        return [self.path]

    @property
    def __file__(self):
        return self.path

    @property
    def __package__(self):
        return self.package

    def getter(self, name, *defargs):
        """
        :class:`MatModule` ``getter`` method to get attributes.
        """
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
            entity = MatObject.matlabify(".".join([self.package, name]))
            if entity:
                self.entities.append((name, entity))
                logger.debug(
                    f"[sphinxcontrib-matlabdomain] entity {name=} imported from {self=}"
                )
                return entity


class MatMixin(object):
    """
    Methods to comparing and manipulating tokens in :class:`MatFunction` and
    :class:`MatClass`.
    """

    def _tk_eq(self, idx, token):
        """
        Returns ``True`` if token keys are the same and values are equal.

        :param idx: Index of token in :class:`MatObject`.
        :type idx: int
        :param token: Comparison token.
        :type token: tuple
        """
        return self.tokens[idx][0] is token[0] and self.tokens[idx][1] == token[1]

    def _tk_ne(self, idx, token):
        """
        Returns ``True`` if token keys are not the same or values are not
        equal.

        :param idx: Index of token in :class:`MatObject`.
        :type idx: int
        :param token: Comparison token.
        :type token: tuple
        """
        return self.tokens[idx][0] is not token[0] or self.tokens[idx][1] != token[1]

    def _eotk(self, idx):
        """
        Returns ``True`` if end of tokens is reached.
        """
        return idx >= len(self.tokens)

    def _blanks(self, idx):
        """
        Returns number of blank text tokens.

        :param idx: Token index.
        :type idx: int
        """
        # idx0 = idx  # original index
        # while self._tk_eq(idx, (Token.Text, ' ')): idx += 1
        # return idx - idx0  # blanks
        return self._indent(idx)

    def _whitespace(self, idx):
        """
        Returns number of whitespaces text tokens, including blanks, newline
        and tabs.

        :param idx: Token index.
        :type idx: int
        """
        idx0 = idx  # original index
        while (
            self.tokens[idx][0] is Token.Text
            or self.tokens[idx][0] is Token.Text.Whitespace
        ) and self.tokens[idx][1] in [" ", "\n", "\t"]:
            idx += 1
        return idx - idx0  # whitespace

    def _indent(self, idx):
        """
        Returns indentation tabs or spaces. No indentation is zero.

        :param idx: Token index.
        :type idx: int
        """
        idx0 = idx  # original index
        while self.tokens[idx][0] is Token.Text and self.tokens[idx][1] in [" ", "\t"]:
            idx += 1
        return idx - idx0  # indentation

    def _propspec(self, idx):
        """
        Returns number of "property" specification tokens

        :param idx: Token index.
        :type idx: int
        """
        idx0 = idx  # original index
        while (
            self._tk_eq(idx, (Token.Punctuation, "@"))
            or self._tk_eq(idx, (Token.Punctuation, "("))
            or self._tk_eq(idx, (Token.Punctuation, ")"))
            or self._tk_eq(idx, (Token.Punctuation, ","))
            or self._tk_eq(idx, (Token.Punctuation, ":"))
            or self.tokens[idx][0] == Token.Literal.Number.Integer
            or self._tk_eq(idx, (Token.Punctuation, "{"))
            or self._tk_eq(idx, (Token.Punctuation, "}"))
            or self._tk_eq(idx, (Token.Punctuation, "["))
            or self._tk_eq(idx, (Token.Punctuation, "]"))
            or self._tk_eq(idx, (Token.Punctuation, "."))
            or self.tokens[idx][0] == Token.Literal.String
            or self.tokens[idx][0] == Token.Name
            or (self.tokens[idx][0] == Token.Text and self.tokens[idx][1] != "\n")
        ):
            idx += 1
        return idx - idx0  # property spec count.

    def _is_newline(self, idx):
        """Returns true if the token at index is a newline"""
        return (
            self.tokens[idx][0] in (Token.Text, Token.Text.Whitespace)
            and self.tokens[idx][1] == "\n"
        )


def skip_whitespace(tks):
    """Eats whitespace from list of tokens"""
    while tks and (
        tks[-1][0] == Token.Text.Whitespace
        or tks[-1][0] == Token.Text
        and tks[-1][1] in [" ", "\t"]
    ):
        tks.pop()


class MatFunction(MatObject):
    """
    A MATLAB function.

    :param name: Name of :class:`MatObject`.
    :type name: str
    :param modname: Name of folder containing :class:`MatObject`.
    :type modname: str
    :param tokens: List of tokens parsed from mfile by Pygments.
    :type tokens: list
    """

    def __init__(self, name, modname, tokens):
        super(MatFunction, self).__init__(name)
        #: Path of folder containing :class:`MatObject`.
        self.module = modname
        #: List of tokens parsed from mfile by Pygments.
        self.tokens = tokens
        #: docstring
        self.docstring = ""
        #: output args
        self.retv = None
        #: input args
        self.args = None
        #: remaining tokens after main function is parsed
        self.rem_tks = None
        # =====================================================================
        # parse tokens
        # XXX: Pygments always reads MATLAB function signature as:
        # [(Token.Keyword, 'function'),  # any whitespace is stripped
        #  (Token.Text.Whitesapce, ' '),  # spaces and tabs are concatenated
        #  (Token.Text, '[o1, o2]'),  # if there are outputs, they're all
        #                               concatenated w/ or w/o brackets and any
        #                               trailing whitespace
        #  (Token.Punctuation, '='),  # possibly an equal sign
        #  (Token.Text.Whitesapce, ' '),  # spaces and tabs are concatenated
        #  (Token.Name.Function, 'myfun'),  # the name of the function
        #  (Token.Punctuation, '('),  # opening parenthesis
        #  (Token.Text, 'a1, a2',  # if there are args, they're concatenated
        #  (Token.Punctuation, ')'),  # closing parenthesis
        #  (Token.Text.Whitesapce, '\n')]  # all whitespace after args
        # XXX: Pygments does not tolerate MATLAB continuation ellipsis!
        tks = copy(self.tokens)  # make a copy of tokens
        tks.reverse()  # reverse in place for faster popping, stacks are LiLo
        try:
            # =====================================================================
            # parse function signature
            # function [output] = name(inputs)
            # % docstring
            # =====================================================================
            # Skip function token - already checked in MatObject.parse_mfile
            tks.pop()
            skip_whitespace(tks)

            #  Check for return values
            retv = tks.pop()
            if retv[0] is Token.Text:
                self.retv = [rv.strip() for rv in retv[1].strip("[ ]").split(",")]
                if len(self.retv) == 1:
                    # check if return is empty
                    if not self.retv[0]:
                        self.retv = None
                    # check if return delimited by whitespace
                    elif " " in self.retv[0] or "\t" in self.retv[0]:
                        self.retv = [
                            rv
                            for rv_tab in self.retv[0].split("\t")
                            for rv in rv_tab.split(" ")
                        ]
                if tks.pop() != (Token.Punctuation, "="):
                    # Unlikely to end here. But never-the-less warn!
                    logger.warning(
                        "[sphinxcontrib-matlabdomain] Parsing failed in %s.%s. Expected '='.",
                        modname,
                        name,
                    )
                    return

                skip_whitespace(tks)
            elif retv[0] is Token.Name.Function:
                tks.append(retv)
            # =====================================================================
            # function name
            func_name = tks.pop()
            func_name = (
                func_name[0],
                func_name[1].strip(" ()"),
            )  # Strip () in case of dummy arg
            if func_name != (Token.Name.Function, self.name):  # @UndefinedVariable
                if isinstance(self, MatMethod):
                    self.name = func_name[1]
                else:
                    logger.warning(
                        "[sphinxcontrib-matlabdomain] Unexpected function name: '%s'. "
                        "Expected '%s' in module '%s'.",
                        func_name[1],
                        name,
                        modname,
                    )

            # =====================================================================
            # input args
            if tks.pop() == (Token.Punctuation, "("):
                args = tks.pop()
                if args[0] is Token.Text:
                    self.args = [
                        arg.strip() for arg in args[1].split(",")
                    ]  # no arguments given
                elif args == (Token.Punctuation, ")"):
                    # put closing parenthesis back in stack
                    tks.append(args)
                # check if function args parsed correctly
                if tks.pop() != (Token.Punctuation, ")"):
                    # Unlikely to end here. But never-the-less warn!
                    logger.warning(
                        "[sphinxcontrib-matlabdomain] Parsing failed in {}.{}. Expected ')'.",
                        modname,
                        name,
                    )
                    return

            skip_whitespace(tks)
            # =====================================================================
            # docstring
            try:
                docstring = tks.pop()
            except IndexError:
                docstring = None
            while docstring and docstring[0] is Token.Comment:
                self.docstring += docstring[1].lstrip("%")
                # Get newline if it exists and append to docstring
                try:
                    wht = tks.pop()  # We expect a newline
                except IndexError:
                    break
                if wht[0] in (Token.Text, Token.Text.Whitespace) and wht[1] == "\n":
                    self.docstring += "\n"
                # Skip whitespace
                try:
                    wht = tks.pop()  # We expect a newline
                except IndexError:
                    break
                while wht in list(zip((Token.Text,) * 3, (" ", "\t"))):
                    try:
                        wht = tks.pop()
                    except IndexError:
                        break
                docstring = wht  # check if Token is Comment

            # Find the end of the function - used in `MatMethod`` to determine where a method ends.
            if docstring is None:
                return
            kw = docstring  # last token
            lastkw = 0  # set last keyword placeholder
            kw_end = 1  # count function keyword
            while kw_end > 0:
                # increment keyword-end pairs count
                if kw in MATLAB_KEYWORD_REQUIRES_END:
                    kw_end += 1
                # nested function definition
                elif kw[0] is Token.Keyword and kw[1].strip() == "function":
                    kw_end += 1
                # decrement keyword-end pairs count but
                # don't decrement `end` if used as index
                elif kw == (Token.Keyword, "end") and not lastkw:
                    kw_end -= 1
                # save last punctuation
                elif kw in list(zip((Token.Punctuation,) * 2, ("(", "{"))):
                    lastkw += 1
                elif kw in list(zip((Token.Punctuation,) * 2, (")", "}"))):
                    lastkw -= 1
                try:
                    kw = tks.pop()
                except IndexError:
                    break
            tks.append(kw)  # put last token back in list
        except IndexError:
            logger.warning(
                "[sphinxcontrib-matlabdomain] Parsing failed in %s.%s. Check if valid MATLAB code.",
                modname,
                name,
            )
        # if there are any tokens left save them
        if len(tks) > 0:
            self.rem_tks = tks  # save extra tokens

    def ref_role(self):
        """Returns role to use for references to this object (e.g. when generating auto-links)"""
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
            super(MatFunction, self).getter(name, *defargs)


class MatClass(MatMixin, MatObject):
    """
    A MATLAB class definition.

    :param name: Name of :class:`MatObject`.
    :type name: str
    :param path: Path of folder containing :class:`MatObject`.
    :type path: str
    :param tokens: List of tokens parsed from mfile by Pygments.
    :type tokens: list
    """

    def __init__(self, name, modname, tokens):
        super(MatClass, self).__init__(name)
        #: Path of folder containing :class:`MatObject`.
        self.module = modname
        #: List of tokens parsed from mfile by Pygments.
        self.tokens = tokens
        #: dictionary of class attributes
        self.attrs = {}
        #: list of class superclasses
        self.bases = []
        #: docstring
        self.docstring = ""
        #: dictionary of class properties
        self.properties = {}
        #: dictionary of class methods
        self.methods = {}
        #: remaining tokens after main class definition is parsed
        self.rem_tks = None
        # =====================================================================
        # parse tokens
        # TODO: use generator and next() instead of stepping index!
        try:
            # Skip classdef token - already checked in MatObject.parse_mfile
            idx = 1  # token index

            # class "attributes"
            self.attrs, idx = self.attributes(idx, MATLAB_CLASS_ATTRIBUTE_TYPES)

            # Check if self.name matches the name in the file.
            idx += self._blanks(idx)
            if not self.tokens[idx][1] == self.name:
                logger.warning(
                    "[sphinxcontrib-matlabdomain] Unexpected class name: '%s'."
                    " Expected '%s' in '%s'.",
                    self.tokens[idx][1],
                    name,
                    modname,
                )

            idx += 1
            idx += self._blanks(idx)  # skip blanks
            # =====================================================================
            # super classes
            if self._tk_eq(idx, (Token.Operator, "<")):
                idx += 1
                # newline terminates superclasses
                while not self._is_newline(idx):
                    idx += self._blanks(idx)  # skip blanks
                    # concatenate base name
                    base_name = ""
                    while (
                        not self._whitespace(idx)
                        and self.tokens[idx][0] is not Token.Comment
                    ):
                        base_name += self.tokens[idx][1]
                        idx += 1
                    # If it's a newline, we are done parsing.
                    if not self._is_newline(idx):
                        idx += 1
                    if base_name:
                        self.bases.append(base_name)
                    idx += self._blanks(idx)  # skip blanks
                    # continue to next super class separated by &
                    if self._tk_eq(idx, (Token.Operator, "&")):
                        idx += 1
                idx += 1  # end of super classes
            # newline terminates classdef signature
            elif self._is_newline(idx):
                idx += 1  # end of classdef signature
            # =====================================================================
            # docstring
            idx += self._indent(idx)  # calculation indentation
            # concatenate docstring
            while self.tokens[idx][0] is Token.Comment:
                self.docstring += self.tokens[idx][1].lstrip("%")
                idx += 1
                # append newline to docstring
                if self._is_newline(idx):
                    self.docstring += self.tokens[idx][1]
                    idx += 1
                # skip tab
                indent = self._indent(idx)  # calculation indentation
                idx += indent
            # =====================================================================
            # properties & methods blocks
            # loop over code body searching for blocks until end of class
            while self._tk_ne(idx, (Token.Keyword, "end")):
                # skip comments and whitespace
                while self._whitespace(idx) or self.tokens[idx][0] is Token.Comment:
                    whitespace = self._whitespace(idx)
                    if whitespace:
                        idx += whitespace
                    else:
                        idx += 1

                # =================================================================
                # properties blocks
                if self._tk_eq(idx, (Token.Keyword, "properties")):
                    prop_name = ""
                    idx += 1
                    # property "attributes"
                    attr_dict, idx = self.attributes(
                        idx, MATLAB_PROPERTY_ATTRIBUTE_TYPES
                    )
                    # Token.Keyword: "end" terminates properties & methods block
                    while self._tk_ne(idx, (Token.Keyword, "end")):
                        # skip whitespace
                        while self._whitespace(idx):
                            whitespace = self._whitespace(idx)
                            if whitespace:
                                idx += whitespace
                            else:
                                idx += 1

                        # =========================================================
                        # long docstring before property
                        if self.tokens[idx][0] is Token.Comment:
                            # docstring
                            docstring = ""

                            # Collect comment lines
                            while self.tokens[idx][0] is Token.Comment:
                                docstring += self.tokens[idx][1].lstrip("%")
                                idx += 1
                                idx += self._blanks(idx)

                                try:
                                    # Check if end of line was reached
                                    if self._is_newline(idx):
                                        docstring += "\n"
                                        idx += 1
                                        idx += self._blanks(idx)

                                    # Check if variable name is next
                                    if self.tokens[idx][0] is Token.Name:
                                        prop_name = self.tokens[idx][1]
                                        self.properties[prop_name] = {
                                            "attrs": attr_dict
                                        }
                                        self.properties[prop_name][
                                            "docstring"
                                        ] = docstring
                                        break

                                    # If there is an empty line at the end of
                                    # the comment: discard it
                                    elif self._is_newline(idx):
                                        docstring = ""
                                        idx += self._whitespace(idx)
                                        break

                                except IndexError:
                                    # EOF reached, quit gracefully
                                    break

                        # with "%:" directive trumps docstring after property
                        if self.tokens[idx][0] is Token.Name:
                            prop_name = self.tokens[idx][1]
                            idx += 1
                            # Initialize property if it was not already done
                            if prop_name not in self.properties.keys():
                                self.properties[prop_name] = {"attrs": attr_dict}

                            # skip size, class and functions specifiers
                            # TODO: Parse old and new style property extras
                            idx += self._propspec(idx)

                            if self._tk_eq(idx, (Token.Punctuation, ";")):
                                continue

                        # subtype of Name EG Name.Builtin used as Name
                        elif self.tokens[idx][0] in Token.Name.subtypes:
                            prop_name = self.tokens[idx][1]
                            logger.debug(
                                "[sphinxcontrib-matlabdomain] WARNING %s.%s.%s is a builtin name.",
                                self.module,
                                self.name,
                                prop_name,
                            )
                            self.properties[prop_name] = {"attrs": attr_dict}
                            idx += 1

                            # skip size, class and functions specifiers
                            # TODO: Parse old and new style property extras
                            idx += self._propspec(idx)

                            if self._tk_eq(idx, (Token.Punctuation, ";")):
                                continue

                        elif self._tk_eq(idx, (Token.Keyword, "end")):
                            idx += 1
                            break
                        # skip semicolon after property name, but no default
                        elif self._tk_eq(idx, (Token.Punctuation, ";")):
                            idx += 1
                            # A comment might come after semi-colon
                            idx += self._blanks(idx)
                            if self._is_newline(idx):
                                idx += 1
                                # Property definition is finished; add missing values
                                if "default" not in self.properties[prop_name].keys():
                                    self.properties[prop_name]["default"] = None
                                if "docstring" not in self.properties[prop_name].keys():
                                    self.properties[prop_name]["docstring"] = None

                                continue
                            elif self.tokens[idx][0] is Token.Comment:
                                docstring = self.tokens[idx][1].lstrip("%")
                                docstring += "\n"
                                self.properties[prop_name]["docstring"] = docstring
                                idx += 1
                        elif self.tokens[idx][0] is Token.Comment:
                            # Comments seperated with blank lines.
                            idx = idx - 1
                            continue
                        else:
                            logger.warning(
                                "sphinxcontrib-matlabdomain] Expected property in %s.%s - got %s",
                                self.module,
                                self.name,
                                str(self.tokens[idx]),
                            )
                            return
                        idx += self._blanks(idx)  # skip blanks
                        # =========================================================
                        # defaults
                        default = {"default": None}
                        if self._tk_eq(idx, (Token.Punctuation, "=")):
                            idx += 1
                            idx += self._blanks(idx)  # skip blanks
                            # concatenate default value until newline or comment
                            default = ""
                            punc_ctr = 0  # punctuation placeholder
                            # keep reading until newline or comment
                            # only if all punctuation pairs are closed
                            # and comment is **not** continuation ellipsis
                            while (
                                (
                                    not self._is_newline(idx)
                                    and self.tokens[idx][0] is not Token.Comment
                                )
                                or punc_ctr > 0
                                or (
                                    self.tokens[idx][0] is Token.Comment
                                    and self.tokens[idx][1].startswith("...")
                                )
                            ):
                                token = self.tokens[idx]
                                # default has an array spanning multiple lines
                                if token in list(
                                    zip((Token.Punctuation,) * 3, ("(", "{", "["))
                                ):
                                    punc_ctr += 1  # increment punctuation counter
                                # look for end of array
                                elif token in list(
                                    zip((Token.Punctuation,) * 3, (")", "}", "]"))
                                ):
                                    punc_ctr -= 1  # decrement punctuation counter
                                # Pygments treats continuation ellipsis as comments
                                # text from ellipsis until newline is in token
                                elif token[0] is Token.Comment and token[1].startswith(
                                    "..."
                                ):
                                    idx += 1  # skip ellipsis comments
                                    # include newline which should follow comment
                                    if self._is_newline(idx):
                                        default += "\n"
                                        idx += 1
                                    continue
                                elif self._is_newline(idx - 1):
                                    idx += self._blanks(idx)
                                    continue
                                elif token[0] is Token.Text and token[1] == " ":
                                    # Skip spaces that are not in strings.
                                    idx += 1
                                    continue
                                default += token[1]
                                idx += 1
                            if self.tokens[idx][0] is not Token.Comment:
                                idx += 1
                            if default:
                                default = {"default": default.rstrip("; ")}

                        self.properties[prop_name].update(default)
                        # =========================================================
                        # docstring
                        if "docstring" not in self.properties[prop_name].keys():
                            docstring = {"docstring": None}
                            if self.tokens[idx][0] is Token.Comment:
                                docstring["docstring"] = self.tokens[idx][1].lstrip("%")
                                idx += 1
                            self.properties[prop_name].update(docstring)
                        elif self.tokens[idx][0] is Token.Comment:
                            # skip this comment
                            idx += 1

                        idx += self._whitespace(idx)
                    idx += 1
                # =================================================================
                # method blocks
                if self._tk_eq(idx, (Token.Keyword, "methods")):
                    idx += 1
                    # method "attributes"
                    attr_dict, idx = self.attributes(idx, MATLAB_METHOD_ATTRIBUTE_TYPES)
                    # Token.Keyword: "end" terminates properties & methods block
                    while self._tk_ne(idx, (Token.Keyword, "end")):
                        # skip comments and whitespace
                        while (
                            self._whitespace(idx)
                            or self.tokens[idx][0] is Token.Comment
                        ):
                            whitespace = self._whitespace(idx)
                            if whitespace:
                                idx += whitespace
                            else:
                                idx += 1
                        # skip methods defined in other files
                        meth_tk = self.tokens[idx]
                        if (
                            meth_tk[0] is Token.Name
                            or meth_tk[0] is Token.Name.Builtin
                            or meth_tk[0] is Token.Name.Function
                            or (
                                meth_tk[0] is Token.Keyword
                                and meth_tk[1].strip() == "function"
                                and self.tokens[idx + 1][0] is Token.Name.Function
                            )
                            or self._tk_eq(idx, (Token.Punctuation, "["))
                            or self._tk_eq(idx, (Token.Punctuation, "]"))
                            or self._tk_eq(idx, (Token.Punctuation, "="))
                            or self._tk_eq(idx, (Token.Punctuation, "("))
                            or self._tk_eq(idx, (Token.Punctuation, ")"))
                            or self._tk_eq(idx, (Token.Punctuation, ";"))
                            or self._tk_eq(idx, (Token.Punctuation, ","))
                        ):
                            logger.debug(
                                "[sphinxcontrib-matlabdomain] Skipping tokens for methods defined in separate files."
                                "Token #%d: %r",
                                idx,
                                self.tokens[idx],
                            )
                            idx += 1 + self._whitespace(idx + 1)
                        elif self._tk_eq(idx, (Token.Keyword, "end")):
                            idx += 1
                            break
                        else:
                            # find methods
                            meth = MatMethod(
                                self.module, self.tokens[idx:], self, attr_dict
                            )

                            # Detect getter/setter methods - these are not documented
                            isGetter = meth.name.startswith("get.")
                            isSetter = meth.name.startswith("set.")
                            if not (isGetter or isSetter):
                                # Add the parsed method to methods dictionary
                                self.methods[meth.name] = meth

                            # Update idx with the number of parsed tokens.
                            idx += meth.skip_tokens()
                            idx += self._whitespace(idx)
                    idx += 1
                if self._tk_eq(idx, (Token.Keyword, "events")):
                    logger.debug(
                        "[sphinxcontrib-matlabdomain] ignoring 'events' in 'classdef %s.'",
                        self.name,
                    )
                    idx += 1
                    # Token.Keyword: "end" terminates events block
                    while self._tk_ne(idx, (Token.Keyword, "end")):
                        idx += 1
                    idx += 1
                if self._tk_eq(idx, (Token.Name, "enumeration")):
                    logger.debug(
                        "[sphinxcontrib-matlabdomain] ignoring 'enumeration' in 'classdef %s'.",
                        self.name,
                    )
                    idx += 1
                    # Token.Keyword: "end" terminates events block
                    while self._tk_ne(idx, (Token.Keyword, "end")):
                        idx += 1
                    idx += 1
                if self._tk_eq(idx, (Token.Punctuation, ";")):
                    # Skip trailing semicolon after end.
                    idx += 1
        except IndexError:
            logger.warning(
                "[sphinxcontrib-matlabdomain] Parsing failed in %s.%s. "
                "Check if valid MATLAB code.",
                modname,
                name,
            )

        self.rem_tks = idx  # index of last token

    def ref_role(self):
        """Returns role to use for references to this object (e.g. when generating auto-links)"""
        return "class"

    def fullname(self, env):
        """Returns full name for class object, for use as link target"""
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
        """Returns link for class object"""
        target = self.fullname(env)
        if name:
            return f":class:`{name} <{target}>`"
        else:
            return f":class:`{target}`"

    def attributes(self, idx, attr_types):
        """
        Retrieve MATLAB class, property and method attributes.
        """
        attr_dict = {}
        idx += self._blanks(idx)  # skip blanks
        # class, property & method "attributes" start with parenthesis
        if self._tk_eq(idx, (Token.Punctuation, "(")):
            idx += 1
            # closing parenthesis terminates attributes
            while self._tk_ne(idx, (Token.Punctuation, ")")):
                idx += self._blanks(idx)  # skip blanks

                k, attr_name = self.tokens[idx]  # split token key, value
                if k is Token.Name and attr_name in attr_types:
                    attr_dict[attr_name] = True  # add attibute to dictionary
                    idx += 1
                elif k is Token.Name:
                    logger.warning(
                        "[sphinxcontrib-matlabdomain] Unexpected class attribute: '%s'. "
                        " In '%s.%s'.",
                        str(self.tokens[idx][1]),
                        self.module,
                        self.name,
                    )
                    idx += 1

                idx += self._blanks(idx)  # skip blanks

                # Continue if attribute is assigned a boolean value
                if self.tokens[idx][0] == Token.Name.Builtin:
                    idx += 1
                    continue

                # continue to next attribute separated by commas
                if self._tk_eq(idx, (Token.Punctuation, ",")):
                    idx += 1
                    continue
                # attribute values
                elif self._tk_eq(idx, (Token.Punctuation, "=")):
                    idx += 1
                    idx += self._blanks(idx)  # skip blanks
                    k, attr_val = self.tokens[idx]  # split token key, value
                    if k is Token.Name and attr_val in ["true", "false"]:
                        # logical value
                        if attr_val == "false":
                            attr_dict[attr_name] = False
                        idx += 1
                    elif k is Token.Name or self._tk_eq(idx, (Token.Text, "?")):
                        # concatenate enumeration or meta class
                        enum_or_meta = self.tokens[idx][1]
                        idx += 1
                        while (
                            self._tk_ne(idx, (Token.Text, " "))
                            and self._tk_ne(idx, (Token.Text, "\t"))
                            and self._tk_ne(idx, (Token.Punctuation, ","))
                            and self._tk_ne(idx, (Token.Punctuation, ")"))
                        ):
                            enum_or_meta += self.tokens[idx][1]
                            idx += 1
                        if self._tk_ne(idx, (Token.Punctuation, ")")):
                            idx += 1
                        attr_dict[attr_name] = enum_or_meta
                    # cell array of values
                    elif self._tk_eq(idx, (Token.Punctuation, "{")):
                        idx += 1
                        # closing curly braces terminate cell array
                        attr_dict[attr_name] = []
                        while self._tk_ne(idx, (Token.Punctuation, "}")):
                            idx += self._blanks(idx)  # skip blanks
                            # concatenate attr value string
                            attr_val = ""
                            # TODO: use _blanks or _indent instead
                            while self._tk_ne(
                                idx, (Token.Punctuation, ",")
                            ) and self._tk_ne(idx, (Token.Punctuation, "}")):
                                attr_val += self.tokens[idx][1]
                                idx += 1
                            if self._tk_eq(idx, (Token.Punctuation, ",")):
                                idx += 1
                            if attr_val:
                                attr_dict[attr_name].append(attr_val)
                        idx += 1
                    elif (
                        self.tokens[idx][0] == Token.Literal.String
                        and self.tokens[idx + 1][0] == Token.Literal.String
                    ):
                        # String
                        attr_val += self.tokens[idx][1] + self.tokens[idx + 1][1]
                        idx += 2
                        attr_dict[attr_name] = attr_val.strip("'")

                    idx += self._blanks(idx)  # skip blanks
                    # continue to next attribute separated by commas
                    if self._tk_eq(idx, (Token.Punctuation, ",")):
                        idx += 1
            idx += 1  # end of class attributes
        return attr_dict, idx

    @property
    def __module__(self):
        return self.module

    @property
    def __doc__(self):
        return self.docstring

    @property
    def __bases__(self):
        bases_ = dict.fromkeys(self.bases)  # make copy of bases
        class_entity_table = {}
        for name, entity in entities_table.items():
            if isinstance(entity, MatClass) or "@" in name:
                class_entity_table[name] = entity

        for base in self.bases:
            if base in class_entity_table.keys():
                bases_[base] = class_entity_table[base]

        return bases_

    def getter(self, name, *defargs):
        """
        :class:`MatClass` ``getter`` method to get attributes.
        """
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
        elif name in self.methods:
            return self.methods[name]
        elif name == "__dict__":
            objdict = dict([(pn, self.getter(pn)) for pn in self.properties.keys()])
            objdict.update(self.methods)
            return objdict
        else:
            super(MatClass, self).getter(name, *defargs)


class MatProperty(MatObject):
    def __init__(self, name, cls, attrs):
        super(MatProperty, self).__init__(name)
        self.cls = cls
        self.attrs = attrs["attrs"]
        self.default = attrs["default"]
        self.docstring = attrs["docstring"]
        # self.class = attrs['class']

    def ref_role(self):
        """Returns role to use for references to this object (e.g. when generating auto-links)"""
        return "attr"

    @property
    def __module__(self):
        return self.cls.module

    @property
    def __doc__(self):
        return self.docstring


class MatMethod(MatFunction):
    def __init__(self, modname, tks, cls, attrs):
        # set name to None
        super(MatMethod, self).__init__(None, modname, tks)
        self.cls = cls
        self.attrs = attrs

    def ref_role(self):
        """Returns role to use for references to this object (e.g. when generating auto-links)"""
        return "meth"

    def skip_tokens(self):
        # Number of tokens to skip in `MatClass`
        num_rem_tks = len(self.rem_tks)
        len_meth = len(self.tokens) - num_rem_tks
        self.tokens = self.tokens[:-num_rem_tks]
        self.rem_tks = None
        return len_meth

    @property
    def __module__(self):
        return self.module

    @property
    def __doc__(self):
        return self.docstring


class MatScript(MatObject):
    def __init__(self, name, modname, tks):
        super(MatScript, self).__init__(name)
        #: Path of folder containing :class:`MatScript`.
        self.module = modname
        #: List of tokens parsed from mfile by Pygments.
        self.tokens = tks
        #: docstring
        self.docstring = ""
        #: remaining tokens after main function is parsed
        self.rem_tks = None

        tks = copy(self.tokens)  # make a copy of tokens
        tks.reverse()  # reverse in place for faster popping, stacks are LiLo
        skip_whitespace(tks)
        # =====================================================================
        # docstring
        try:
            docstring = tks.pop()
            # Skip any statements before first documentation header
            while docstring and docstring[0] is not Token.Comment:
                docstring = tks.pop()
        except IndexError:
            docstring = None
        while docstring and docstring[0] is Token.Comment:
            self.docstring += docstring[1].lstrip("%")
            # Get newline if it exists and append to docstring
            try:
                wht = tks.pop()  # We expect a newline
            except IndexError:
                break
            if wht[0] in (Token.Text, Token.Text.Whitespace) and wht[1] == "\n":
                self.docstring += "\n"
            # Skip whitespace
            try:
                wht = tks.pop()  # We expect a newline
            except IndexError:
                break
            while wht in list(zip((Token.Text,) * 3, (" ", "\t"))):
                try:
                    wht = tks.pop()
                except IndexError:
                    break
            docstring = wht  # check if Token is Comment

    @property
    def __doc__(self):
        return self.docstring

    @property
    def __module__(self):
        return self.module


class MatApplication(MatObject):
    """
    Representation of the documentation in a Matlab Application.

    :param name: Name of :class:`MatObject`.
    :type name: str
    :param modname: Name of folder containing :class:`MatObject`.
    :type modname: str
    :param desc: Summary and description string.
    :type desc: str
    """

    def __init__(self, name, modname, desc):
        super(MatApplication, self).__init__(name)
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
        super(MatException, self).__init__(name)
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
            res += " (exception was: %r)" % self.args[1]
        return res


class MatModuleAnalyzer(object):
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
            err = MatcodeError("error importing %r" % modname)
            cls.cache["module", modname] = err
            raise err
        cls.cache["module", modname] = obj
        return obj

    def __init__(self, source, modname, srcname, decoded=False):
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

    def find_attr_docs(self, scope=""):
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
                    namespace = ".".join([mod.package, k])
                    namespace = namespace.lstrip(".")
                    tagname = "%s.%s" % (k, mk)
                    tagname = tagname.lstrip(".")
                    attr_visitor_collected[namespace, mk] = mv.docstring
                    attr_visitor_tagorder[tagname] = tagnumber
                    tagnumber += 1
        self.attr_docs = attr_visitor_collected
        self.tagorder = attr_visitor_tagorder
        return attr_visitor_collected
