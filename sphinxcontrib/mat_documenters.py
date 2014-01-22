# -*- coding: utf-8 -*-
"""
    sphinxcontrib.mat_documenters
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Extend autodoc directives to matlabdomain.

    :copyright: Copyright 2014 Mark Mikofski
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
from sphinx.pycode import ModuleAnalyzer as PyModuleAnalyzer, PycodeError
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
    DocstringSignatureMixin as PyDocstringSignatureMixin, \
    FunctionDocumenter as PyFunctionDocumenter, \
    ClassDocumenter as PyClassDocumenter, \
    ExceptionDocumenter as PyExceptionDocumenter, \
    DataDocumenter as PyDataDocumenter, \
    MethodDocumenter as PyMethodDocumenter, \
    AttributeDocumenter as PyAttributeDocumenter, \
    InstanceAttributeDocumenter as PyInstanceAttributeDocumenter

from mat_types import MatObject, MatModule, MatFunction, \
    MatClass, MatProperty, MatMethod, MatScript, MatException


class MatlabDocumenter(Documenter):
    """
    Base class for documenters of MATLAB objects.
    """
    domain = 'mat'

    def import_object(self):
        """Import the object given by *self.modname* and *self.objpath* and set
        it as *self.object*.

        Returns True if successful, False if an error occurred.
        """
        # get config_value with absolute path to MATLAB source files
        basedir = self.env.config.matlab_src_dir
        dbg = self.env.app.debug
        if self.objpath:
            dbg('[autodoc] from %s import %s',
                self.modname, '.'.join(self.objpath))
        try:
            dbg('[autodoc] import %s', self.modname)
            MatObject.matlabify(basedir, self.modname)
            parent = None
            obj = self.module = sys.modules[self.modname]
            dbg('[autodoc] => %r', obj)
            for part in self.objpath:
                parent = obj
                dbg('[autodoc] getattr(_, %r)', part)
                obj = self.get_attr(obj, part)
                dbg('[autodoc] => %r', obj)
                self.object_name = part
            self.parent = parent
            self.object = obj
            return True
        # this used to only catch SyntaxError, ImportError and AttributeError,
        # but importing modules with side effects can raise all kinds of errors
        except Exception:
            if self.objpath:
                errmsg = 'autodoc: failed to import %s %r from module %r' % \
                         (self.objtype, '.'.join(self.objpath), self.modname)
            else:
                errmsg = 'autodoc: failed to import %s %r' % \
                         (self.objtype, self.fullname)
            errmsg += '; the following exception was raised:\n%s' % \
                      traceback.format_exc()
            dbg(errmsg)
            self.directive.warn(errmsg)
            self.env.note_reread()
            return False


class MatModuleDocumenter(MatlabDocumenter, PyModuleDocumenter):

    def parse_name(self):
        ret = MatlabDocumenter.parse_name(self)
        if self.args or self.retann:
            self.directive.warn('signature arguments or return annotation '
                                'given for automodule %s' % self.fullname)
        return ret

    def add_directive_header(self, sig):
        MatlabDocumenter.add_directive_header(self, sig)

        # add some module-specific options
        if self.options.synopsis:
            self.add_line(
                u'   :synopsis: ' + self.options.synopsis, '<autodoc>')
        if self.options.platform:
            self.add_line(
                u'   :platform: ' + self.options.platform, '<autodoc>')
        if self.options.deprecated:
            self.add_line(u'   :deprecated:', '<autodoc>')


class MatModuleLevelDocumenter(MatlabDocumenter):
    """
    Specialized Documenter subclass for objects on module level (functions,
    classes, data/constants).
    """
    def resolve_name(self, modname, parents, path, base):
        if modname is None:
            if path:
                modname = path.rstrip('.')
            else:
                # if documenting a toplevel object without explicit module,
                # it can be contained in another auto directive ...
                modname = self.env.temp_data.get('autodoc:module')
                # ... or in the scope of a module directive
                if not modname:
                    modname = self.env.temp_data.get('mat:module')
                # ... else, it stays None, which means invalid
        return modname, parents + [base]


class MatClassLevelDocumenter(MatlabDocumenter):
    """
    Specialized Documenter subclass for objects on class level (methods,
    attributes).
    """
    def resolve_name(self, modname, parents, path, base):
        if modname is None:
            if path:
                mod_cls = path.rstrip('.')
            else:
                mod_cls = None
                # if documenting a class-level object without path,
                # there must be a current class, either from a parent
                # auto directive ...
                mod_cls = self.env.temp_data.get('autodoc:class')
                # ... or from a class directive
                if mod_cls is None:
                    mod_cls = self.env.temp_data.get('mat:class')
                # ... if still None, there's no way to know
                if mod_cls is None:
                    return None, []
            modname, cls = rpartition(mod_cls, '.')
            parents = [cls]
            # if the module name is still missing, get it like above
            if not modname:
                modname = self.env.temp_data.get('autodoc:module')
            if not modname:
                modname = self.env.temp_data.get('mat:module')
            # ... else, it stays None, which means invalid
        return modname, parents + [base]


class MatFunctionDocumenter(MatModuleLevelDocumenter, PyFunctionDocumenter):

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return isinstance(member, MatFunction)

    def format_args(self):
        if self.object.args:
            argspec = inspect.ArgSpec(self.object.args, None, None, None)
        else:
            return None
        args = inspect.formatargspec(*argspec)
        # escape backslashes for reST
        args = args.replace('\\', '\\\\')
        return args


class MatClassDocumenter(MatModuleLevelDocumenter, PyClassDocumenter):
    """
    Specialized Documenter subclass for classes.
    """

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return isinstance(member, MatClass)

    def import_object(self):
        ret = MatModuleLevelDocumenter.import_object(self)
        # if the class is documented under another name, document it
        # as data/attribute
        if ret:
            if hasattr(self.object, '__name__'):
                self.doc_as_attr = (self.objpath[-1] != self.object.__name__)
            else:
                self.doc_as_attr = True
        return ret

    def format_args(self):
        # for classes, the relevant signature is the "constructor" method,
        # which has the same name as the class definition
        initmeth = self.get_attr(self.object, self.object.name, None)
        # classes without constructor method, default constructor or
        # constructor written in C?
        if initmeth is None or not isinstance(initmeth, MatMethod):
            return None
        if initmeth.args:
            argspec = inspect.ArgSpec(initmeth.args, None, None, None)
        else:
            return None
        if argspec[0] and argspec[0][0] in ('obj', ):
            del argspec[0][0]
        return inspect.formatargspec(*argspec)

    def format_signature(self):
        if self.doc_as_attr:
            return ''

        # get constructor method signature from docstring
        if self.env.config.autodoc_docstring_signature:
            # only act if the feature is enabled
            init_doc = MatMethodDocumenter(self.directive, self.object.name)
            init_doc.object = self.get_attr(self.object, self.object.name, None)
            init_doc.objpath = [self.object.name]
            result = init_doc._find_signature()
            if result is not None:
                # use args only for Class signature
                return '(%s)' % result[0]

        return MatModuleLevelDocumenter.format_signature(self)

    def add_directive_header(self, sig):
        if self.doc_as_attr:
            self.directivetype = 'attribute'
        Documenter.add_directive_header(self, sig)

        # add inheritance info, if wanted
        if not self.doc_as_attr and self.options.show_inheritance:
            self.add_line(u'', '<autodoc>')
            if len(self.object.__bases__):
                bases = [not v and u':class:`%s`' % b or
                         u':class:`%s.%s`' % (v.__module__, b)
                         for b, v in self.object.__bases__.iteritems()]
                self.add_line(_(u'   Bases: %s') % ', '.join(bases),
                              '<autodoc>')

    def get_doc(self, encoding=None, ignore=1):
        content = self.env.config.autoclass_content

        docstrings = []
        attrdocstring = self.get_attr(self.object, '__doc__', None)
        if attrdocstring:
            docstrings.append(attrdocstring)

        # for classes, what the "docstring" is can be controlled via a
        # config value; the default is only the class docstring
        if content in ('both', 'init'):
            # get __init__ method document from __init__.__doc__
            if self.env.config.autodoc_docstring_signature:
                # only act if the feature is enabled
                init_doc = MatMethodDocumenter(self.directive, self.object.name)
                init_doc.object = self.get_attr(self.object, self.object.name,
                                                None)
                init_doc.objpath = [self.object.name]
                init_doc._find_signature()  # this effects to get_doc() result
                initdocstring = '\n'.join(
                    ['\n'.join(l) for l in init_doc.get_doc(encoding)])
            else:
                initdocstring = self.get_attr(
                    self.get_attr(self.object, self.object.name, None),
                    '__doc__')
            # for new-style classes, no __init__ means default __init__
            if initdocstring == object.__init__.__doc__:
                initdocstring = None
            if initdocstring:
                if content == 'init':
                    docstrings = [initdocstring]
                else:
                    docstrings.append(initdocstring)
        doc = []
        for docstring in docstrings:
            if not isinstance(docstring, unicode):
                docstring = force_decode(docstring, encoding)
            doc.append(prepare_docstring(docstring))
        return doc


class MatExceptionDocumenter(MatlabDocumenter, PyExceptionDocumenter):

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return isinstance(member, MatException)


class MatDataDocumenter(MatModuleLevelDocumenter, PyDataDocumenter):

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return isinstance(member, MatScript)


class MatMethodDocumenter(MatClassLevelDocumenter, PyMethodDocumenter):

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return isinstance(member, MatMethod)

    def format_args(self):
        if self.object.args:
            argspec = inspect.ArgSpec(self.object.args, None, None, None)
        else:
            return None
        if argspec[0] and argspec[0][0] in ('obj', ):
            del argspec[0][0]
        return inspect.formatargspec(*argspec)


class MatAttributeDocumenter(MatClassLevelDocumenter, PyAttributeDocumenter):

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return isinstance(member, MatProperty)


class MatInstanceAttributeDocumenter(MatAttributeDocumenter,
                             PyInstanceAttributeDocumenter):

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return isinstance(member, MatProperty)
