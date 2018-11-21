.. sphinxcontrib-matlabdomain documentation master file, created by
   sphinx-quickstart on Tue Jul 17 11:53:15 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

sphinxcontrib-matlabdomain
==========================

**sphinxcontrib-matlabdomain** is `Sphinx`_ extension to generate API
documentation for `MATLAB`_, it also provides *autodoc* facilities, that lets
you generate documentation *automatically* from MATLAB source files. It works
similar to the  `Python Domain`_.


Getting started
---------------

If you are completely new to `Sphinx`_, follow this `Tutorial`_.

Install **sphinxcontrib-matlabdomain** with

::

   pip install sphinxcontrib-matlabdomain

In order for the Sphinx MATLAB domain to auto-document MATLAB source code, set
the config value of ``matlab_src_dir`` to the absolute root path. Currently
only one MATLAB path can be specified, but all subfolders in that tree will be
searched.

For convenience the `primary domain <http://sphinx-doc.org/config.html#confval-primary_domain>`_
can be set to ``mat``.

Assuming that the directory structure of the project is ike this:

::

   docs/
       conf.py
       index.rst
       make.bat
       Makefile
   src
       <matlab source files>

The ``docs/conf.py`` would look like this:

.. code-block:: python

   import os

   # other statements

   extensions = ['sphinx.ext.autodoc', 'sphinxcontrib.matlab']
   this_dir = os.path.dirname(os.path.abspath(__file__))
   matlab_src_dir = os.path.abspath(os.path.join(this_dir, '..'))
   primary_domain = 'mat'

Example
-------

.. automodule:: src

.. autofunction:: times_two

.. autofunction:: times_two_napoleon

Using auto-directives
---------------------

* Creating a Sphinx project
* Modifying ``conf.py`` to include **sphinxcontrib-matlabdomain**  and autodoc.
* Add ``matlab_src_dir`` with root of MATLAB sources
* List directives and options
* Using auto-directives
* Using napoleon - different style docstrings, that are almost like MATLAB
* Examples

  * Function
  * Function in package
  * Class with inheritance and properties
  * Class folder (have to use autofunction)

* Known limitations

.. toctree::
   :maxdepth: 2
   :caption: Contents:


Directives
----------

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _Sphinx: https://http://www.sphinx-doc.org
.. _Python Domain: http://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html#the-python-domain
.. _Tutorial: http://www.sphinx-doc.org/en/1.7/tutorial.html
.. _MATLAB: https://mathworks.com
