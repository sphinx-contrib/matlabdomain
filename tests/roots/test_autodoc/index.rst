Description
===========

In this directory we test basic autodoc features for different folder types. The
folder layout is::

    test_autodoc
        target  - A typically folder
            @classfolders - i.e folders starting with ``@``
            +package - i.e folders starting with ``+``.
            submodule - i.e subfolders (assumed to be in path).
            ClassExample.m
        BaseClass.m


Table of contents
=================

.. automodule:: target

.. toctree::
   :maxdepth: 2

   index_classfolder
   index_package
   index_submodule
   index_target
   index_root
