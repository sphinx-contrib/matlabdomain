autosummary for modules
=======================

.. autosummary::
    :toctree: generated/
    :template: matmodule.rst

    test_data
    test_data.+package
    test_data.@ClassFolder
    test_data.submodule

.. Specifying template files by :template: directive. matmodule.rst is the default template file for modules(folders).
.. And matclass.rst is the default template file for classes.
.. Could be omitted or user could create their own template files.
.. IF omitted, the template file will be chosen based on the object type.

autosummary for classes and functions
=====================================

.. currentmodule:: test_data
.. autosummary::
    :toctree: generated/

    test_data.f_example
    test_data.f_inputargs_error
    test_data.Bool
    test_data.ClassAbstract
