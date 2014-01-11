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
class MatObject(object):
    def __init__(self, name):
        self.name = name


class MatModule(MatObject):
    def getter(self, name, *defargs):
        fullpath = os.path.join(self.name, name)
        if os.path.isdir(fullpath):
            return MatModule(fullpath)
        elif os.path.isfile(fullpath):
            pass


class MatMixin(MatObject):
    pass


class MatClass(MatObject):
    def __init__(self, name, tokens):
        super(MatClass, self).__init__(name)
        self.tokens = list(tokens)
    def getter(self, name, *defargs):
        for k, v in self.tokens:
            pass


class MatProperty(MatObject):
    pass


class MatFunction(MatObject):
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



