
.. |github-action-badge| image:: https://github.com/sphinx-contrib/matlabdomain/actions/workflows/python-package.yml/badge.svg
   :scale: 100%
   :align: middle

+----------------+-----------------------+
+ Github Actions | |github-action-badge| |
+----------------+-----------------------+

sphinxcontrib-matlabdomain -- Sphinx domain for auto-documenting MATLAB
=======================================================================

This extension provides a `Sphinx <http://www.sphinx-doc.org/en/master/index.html>`_
*domain* for automatically generating doumentation from MATLAB source files.
It is modelled after the `Python autodoc <http://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html>`_.

The extension allows you to have your documentation and source files together
and use the powerful `Sphinx <http://www.sphinx-doc.org/en/master/index.html>`_
documentation tool. All your MATLAB file help text can be automatically
included in the your documentation and output as for instance HTML.

The extension works really well with `sphinx.ext.napoleon
<https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html>`_.

Recent `Changes <https://github.com/sphinx-contrib/matlabdomain/blob/master/CHANGES.rst>`_.


Usage
=====

The Python package must be installed with::

   pip install -U sphinxcontrib-matlabdomain

In general, the usage is the same as for documenting Python code. The package
is tested with Python >= 3.8 and Sphinx >=4.0.0 and <6.0.0.

For a Python 2 compatible version the package must be installed with::

   pip install sphinxcontrib-matlabdomain==0.11.8

Configuration
-------------
In your Sphinx ``conf.py`` file add ``sphinxcontrib.matlab`` to the list of
extensions. ::

   extensions = ['sphinxcontrib.matlab', 'sphinx.ext.autodoc']

Additional Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

``matlab_src_dir``
   In order for the Sphinx MATLAB domain to auto-document MATLAB source code,
   set the config value of ``matlab_src_dir`` to the absolute path. Currently
   only one MATLAB path can be specified, but all subfolders in that tree will
   be searched.

``matlab_src_encoding``
   The encoding of the MATLAB files. By default, the files will be read as utf-8
   and parsing errors will be replaced using ? chars. *Added in Version 0.9.0.*

``matlab_keep_package_prefix``
   Determines if the MATLAB package prefix ``+`` is displayed in the
   generated documentation.  Default is ``True``.  When ``False``, packages are
   still referred to in ReST using ``+pakage.+subpkg.func`` but the output
   will be ``pakage.other.func()``. *Added in Version
   0.11.0.*

``matlab_show_property_default_value``
   Show property default values in the rendered document. Default is ``False``,
   which is what MathWorks does in their documentation. *Added in Version
   0.16.0.*

For convenience the `primary domain <https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-primary_domain>`_
can be set to ``mat``.


Roles and Directives
--------------------

Please see `Sphinx Domains <https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html>`_ and
`sphinx.ext.autodoc
<http://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html>`_ for
documentation on the use of roles and directives. MATLAB code can be documented
using the following roles and directives:

====================================  ===========================================
Directive                             MATLAB object
====================================  ===========================================
``.. module:: foldername``            **folders, packages and namespaces**
``.. currentmodule:: foldername``     * set folder but do not link
``.. automodule:: foldername``        * auto-document
``:mod:`foldername```                 * reference
``.. function:: funcname``            **function definition and signature**
``.. autofunction:: funcname()``      * auto-document
``:func:`funcname```                  * reference
``.. script:: scriptname``            **script definition**
``.. autoscript:: scriptname``        * auto-document
``:scpt:`scriptname```                * reference
``.. class:: classname()``            **class definition and optional signature**
``.. autoclass:: classname``          * auto-document
``:class:`classname```                * reference
``.. method:: methname()``            **method definition and signature**
``.. automethod:: methname``          * auto-document
``:meth:`methname```                  * reference
``.. staticmethod:: statmethname()``  **static method definition and signature**
``.. automethod:: statmethname``      * auto-document
``:meth:`methname```                  * reference
``.. attribute:: attrname``           **property definition**
``.. autoattribute:: attrname``       * auto-document
``:attr:`attrname```                  * reference
``.. application:: appname``          **application definition**
``.. autoapplication:: appname``      * auto-document
``:app:`appname```                    * reference
====================================  ===========================================

Several options are available for auto-directives.

* ``:members:`` auto-document public members
* ``:show-inheritance:`` list bases
* ``:undoc-members:`` document members without docstrings
* ``:annotation:`` specifies attribute annotation instead of default

There are also several config values that can be set in ``conf.py`` that will
affect auto-docementation.

* ``autoclass_content`` can be set to ``class``, ``both`` or ``init``, which
  determines which docstring is used for classes. The constructor docstring
  is used when this is set to ``init``.
* ``autodoc_member_order`` can be set to ``alphabetical``, ``groupwise`` or
  ``bysource``.
* ``autodoc_default_flags`` can be set to a list of options to apply. Use
  the ``no-flag`` directive option to disable this config value once.

.. note::

    The module roles and directives create a psuedo namespace for MATLAB
    objects, similar to a package. They represent the path to the folder
    containing the MATLAB object. If no module is specified then Sphinx will
    assume that the object is a built-in.

Example: given the following MATLAB source in folder ``test_data``::

    classdef MyHandleClass < handle & my.super.Class
        % a handle class
        %
        % :param x: a variable

        %% some comments
        properties
            x % a property

            % Multiple lines before a
            % property can also be used
            y
        end
        methods
            function h = MyHandleClass(x)
                h.x = x
            end
            function x = get.x(obj)
            % how is this displayed?
                x = obj.x
            end
        end
        methods (Static)
            function w = my_static_function(z)
            % A static function in :class:`MyHandleClass`.
            %
            % :param z: input z
            % :returns: w

                w = z
            end
        end
    end

Use the following to document::

    Test Data
    =========
    This is the test data module.

    .. automodule:: test_data

    :mod:`test_data` is a really cool module.

    My Handle Class
    ---------------
    This is the handle class definition.

    .. autoclass:: MyHandleClass
        :show-inheritance:
        :members:


Module Index
------------

Since version 0.10.0 the *MATLAB Module Index* should be linked to with::

   `MATLAB Module Index <mat-modindex.html>`_

Older versions, used the *Python Module Index*, which was linked to with::

   :ref:`modindex`


Documenting Python and MATLAB sources together
==============================================

Since version 0.10.0 MATLAB and Python sources can be (auto-)documented in the same
Sphinx documentation. For this to work, do not set the `primary domain <https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-primary_domain>`_.

Instead use the ``mat:`` prefix before the desired directives::

   .. automodule:: func
   .. autofunction:: func.main

   .. mat:automodule:: matsrc
   .. mat:autofunction:: matsrc.func


Online Demo
===========

The test docs in the repository are online here:
http://bwanamarko.alwaysdata.net/matlabdomain/

.. note::

    Sphinx style markup are used to document parameters, types, returns and
    exceptions. There must be a blank comment line before and after the
    parameter descriptions. Currently property docstrings are only collected if
    they are on the same line following the property definition. Getter and
    setter methods are documented like methods currently, but the dot is
    replaced by an underscore. Default values for properties are represented as
    unicode strings, therefore strings will be double quoted.


Users
=====

* `Cantera <http://cantera.github.io/docs/sphinx/html/compiling/dependencies.html?highlight=matlabdomain>`_
* `CoSMo MVPA <http://cosmomvpa.org/download.html?highlight=matlabdomain#developers>`_
* `The Cobra Toolbox <https://opencobra.github.io/cobratoolbox/stable/index.html#>`_
* `The RepLAB Toolbox <https://replab.github.io/replab>`_


Citation
========
.. image:: https://zenodo.org/badge/105161090.svg
   :target: https://zenodo.org/badge/latestdoi/105161090
