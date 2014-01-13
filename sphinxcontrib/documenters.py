# -*- coding: utf-8 -*-
"""
    sphinx.ext.autodoc
    ~~~~~~~~~~~~~~~~~~

    Automatically insert docstrings for functions, classes or whole modules into
    the doctree, thus avoiding duplication between docstrings and documentation
    for those who like elaborate docstrings.

    :copyright: Copyright 2007-2013 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
import sys
import inspect
import traceback
from types import FunctionType, BuiltinFunctionType, MethodType

from docutils import nodes
from docutils.utils import assemble_option_dict
from docutils.statemachine import ViewList

from sphinx.util import rpartition, force_decode
from sphinx.locale import _
from sphinx.pycode import ModuleAnalyzer, PycodeError
from sphinx.application import ExtensionError
from sphinx.util.nodes import nested_parse_with_titles
from sphinx.util.compat import Directive
from sphinx.util.inspect import getargspec, isdescriptor, safe_getmembers, \
     safe_getattr, safe_repr, is_builtin_class_method
from sphinx.util.pycompat import base_exception, class_types
from sphinx.util.docstrings import prepare_docstring

from sphinx.ext.autodoc import py_ext_sig_re as mat_ext_sig_re
from sphinx.ext.autodoc import Documenter, members_option, bool_option, \
    ModuleDocumenter as PyModuleDocumenter, \
    ModuleLevelDocumenter as PyModuleLevelDocumenter, \
    ClassLevelDocumenter as PyClassLevelDocumenter, \
    DocstringSignatureMixin as PyDocstringSignatureMixin, \
    FunctionDocumenter as PyFunctionDocumenter, \
    ClassDocumenter as PyClassDocumenter
import os
import json
import re

from pygments.lexers import MatlabLexer
from pygments.token import Token


# create some Matlab objects
# TODO: +packages & @class folders
# TODO: subfunctions (not nested) and private folders/functions/classes
# TODO: script files
class MatObject(object):
    """
    Base Matlab object to which all others are subclassed.

    :param name: Name of Matlab object.
    """
    def __init__(self, name):
        #: name of Matlab object
        self.name = name
    def __str__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.name)
    @staticmethod
    def tokenize(fullpath):
        with open(fullpath, 'r') as fp:
            code = fp.read()
        return list(MatlabLexer().get_tokens(code))
    @staticmethod
    def parse_mfile(mfile):        
        # use Pygments to parse mfile to determine type: function/classdef
        tks = MatObject.tokenize(fullpath)  # tokens
        tkn = 0  # token number
        # skip comments
        while tks[tkn][0] is Token.Commment: tkn += 1
        if tks[tkn][0] is Token.Keyword:
            if tks[tkn][1] == 'function':
                return MatFunction(name, path, tks)
            elif tks[tkn][1] == 'classdef':
                return MatClass(name, path, tks)
        else:
            # it's a script file
            return None
    @ staticmethod
    def matlabify(fullpath):
        """
        Makes a MatObject.

        :param fullpath: Full path of object to matlabify.
        :type fullpath: str
        """
        # separate path from file/folder name
        name, path = os.path.split(fullpath)
        # folder trumps mfile with same name
        if os.path.isdir(fullpath):
            return MatModule(name, path)  # treat folder as Matlab module
        elif os.path.isfile(fullpath + '.m'):
            return MatObject.parse_mfile(fullpath + '.m')
        # allow namespace to be anywhere on the path
        else:
            for root, dirs, files in os.walk:
                # don't visit vcs directories
                for vcs in ['.git', '.hg', '.svn']:
                    if vcs in dirs:
                        dirs.remove(vcs)
                # only visit mfiles
                for f in tuple(files):
                    if not f.endswith('.m'):
                        files.remove(f)
                if name in dirs:
                    return MatModule(name, root)
                elif name + '.m' in files:
                    return MatObject.parse_mfile(fullpath + '.m')
                else:
                    continue
            return None
        return None


class MatModule(MatObject):
    """
    There is no concept of a *module* in Matlab, so repurpose *module* to be
    a folder that acts like a namespace for any :class:`MatObjects` in that
    folder. Sphinx will treats objects without a namespace as builtins.
    """
    def __init__(self, name, path=None):
        super(MatModule, self).__init__(name)
        self.path = path
    def getter(self, name, *defargs):
        fullpath = os.path.join(self.path, self.name, name)
        attr = MatObject.matlabify(fullpath)
        if attr:
            return attr
        else:
            return defargs


class MatFunction(MatObject):
    def __init__(self, name, path, tokens):
        super(MatClass, self).__init__(name)
        self.path = path
        self.tokens = tokens
    def getter(self, name, *defargs):
        for k, v in self.tokens:
            pass



class MatClass(MatObject):
    def __init__(self, name, path, tokens):
        super(MatClass, self).__init__(name)
        self.tokens = list(tokens)
    def getter(self, name, *defargs):
        for k, v in self.tokens:
            pass


class MatProperty(MatObject):
    pass


class MatMethod(MatObject):
    pass


class MatStaticMethod(MatObject):
    pass


class MatlabDocumenter(Documenter):
    """
    Base class for documenters of Matlab objects.
    """
    def import_object(self):
        """Import the object given by *self.modname* and *self.objpath* and set
        it as *self.object*.

        Returns True if successful, False if an error occurred.
        """
        # make a full path out of ``self.modname`` and ``self.objpath``
        modname = self.modname.replace('.', os.sep)  # modname may have dots
        fullpath = os.path.join(modname, *self.objpath)  # objpath is a list
        # if directory, set dirname as parent
        if os.path.isdir(fullpath):
            parent = os.path.dirname(fullpath)
            self.parent = MatModule(parent) if parent else None
            self.object = MatModule(fullpath)
            return true
        # if file, tokenize
        elif os.path.isfile(fullpath):
            with open(fullpath, 'r') as fp:
                code = fp.read()
            tks = list(MatlabLexer().get_tokens(code))
        # look for objpath in modname directory
        else:
            for root, dirs, files in os.walk(modname):
                break
        if k is Token.Keyword and v == 'function':
            self.object = MatFunction(modname)
        elif k is Token.Keyword and v == 'classdef':
            self.object = MatClass(modname)



