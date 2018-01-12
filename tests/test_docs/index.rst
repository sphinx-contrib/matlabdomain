.. MATLAB Sphinx Documentation Test documentation master file, created by
   sphinx-quickstart on Wed Jan 15 11:38:03 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to MATLAB Sphinx Documentation Test's documentation!
============================================================

Contents:
---------

.. toctree::
   :maxdepth: 2

Tests:
------

.. _test-data:

Test Data
^^^^^^^^^
This is the test data module

.. automodule:: test_data

:mod:`test_data` is a really cool module

.. _ClassInheritHandle:

A Handle Class
++++++++++++++
Should show inheritance and members.

.. autoclass:: ClassInheritHandle
    :show-inheritance:
    :members:

.. _ClassAbstract:

A Abstract Class
++++++++++++++++
Should show inheritance and members.

.. autoclass:: ClassAbstract
    :show-inheritance:
    :members:

.. _f_example:

Example Function
++++++++++++++++
Should show parameter and return values.

.. autofunction:: f_example

.. _f_with_nested_function:

Function with nested function
+++++++++++++++++++++++++++++
.. autofunction:: f_with_nested_function

.. _ClassExample:

An Example Class
++++++++++++++++
Should show inheritance and members.

.. autoclass:: ClassExample
    :show-inheritance:
    :members:

.. _mymethod:

my method
~~~~~~~~~
A method in ClassExample

.. automethod:: ClassExample.mymethod

A class with ellipsis properties
++++++++++++++++++++++++++++++++
Some edge cases that have ellipsis inside arrays.

.. autoclass:: ClassWithEllipsisProperties
    :show-inheritance:
    :members:

+package
++++++++
This is the test package

.. automodule:: test_data.+package

packageFunc
~~~~~~~~~~~

.. autofunction:: package_func

@ClassFolder
++++++++++++
This is the test class folder

.. automodule:: test_data.@ClassFolder

ClassFolder
~~~~~~~~~~~

.. autoclass:: ClassFolder

classMethod
~~~~~~~~~~~

.. autofunction:: classMethod
.. automethod:: ClassFolder.method_inside_classdef


A Static Function
~~~~~~~~~~~~~~~~~

.. autofunction:: a_static_func


Submodule
+++++++++
This is the test_data module

.. automodule:: test_data.submodule


Ellipsis after equals
~~~~~~~~~~~~~~~~~~~~~
.. autofunction:: f_ellipsis_after_equals


No Arguments
~~~~~~~~~~~~
.. autofunction:: f_no_input


No Outputs
~~~~~~~~~~
.. autofunction:: f_no_output


Output with Ellipsis
~~~~~~~~~~~~~~~~~~~~
.. autofunction:: f_ellipsis_in_output


Ellipsis in input and no spaces in output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. autofunction:: f_ellipsis_in_input


Function with no parentheses in input
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. autofunction:: f_no_input_parentheses


Class that inherits from different modules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Insert text here

.. autoclass:: ClassInheritDifferentModules
    :members:
    :show-inheritance:


TestFibonacci
~~~~~~~~~~~~~
A Matlab unittest class

.. autoclass:: TestFibonacci
    :members:
    :show-inheritance:


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

