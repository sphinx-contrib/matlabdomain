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

An Abstract Class
+++++++++++++++++
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

A class using bysource ordering
+++++++++++++++++++++++++++++++

Using `bysource` ordering instead of default `alphabetic`

.. autoclass:: ClassBySource
    :show-inheritance:
    :members:
    :member-order: bysource

A class with undocumented members
+++++++++++++++++++++++++++++++++

List all members of a class, even those without documentation by using
`:undoc-members:`.

.. autoclass:: ClassWithUndocumentedMembers
    :members:
    :undoc-members:

Default is to only list documented members.

.. autoclass:: ClassWithUndocumentedMembers
    :members:


A class with ellipsis properties
++++++++++++++++++++++++++++++++
Some edge cases that have ellipsis inside arrays.

.. autoclass:: ClassWithEllipsisProperties
    :show-inheritance:
    :members:

A class with old style properties
+++++++++++++++++++++++++++++++++

.. autoclass:: PropTypeOld
    :members:

ValidateProps
+++++++++++++
A Matlab class with property validation

.. autoclass:: ValidateProps
    :members:

ClassWithMethodAttributes
+++++++++++++++++++++++++

A Matlab class with different method attributes

.. literalinclude:: ../test_data/ClassWithMethodAttributes.m
   :language: matlab

Public methods
~~~~~~~~~~~~~~

By default only the public methods will be included

.. autoclass:: ClassWithMethodAttributes
    :members:
    :show-inheritance:

Protected methods
~~~~~~~~~~~~~~~~~

Including the protected members as well

.. autoclass:: ClassWithMethodAttributes
    :members:
    :show-inheritance:
    :protected-members:

Private methods
~~~~~~~~~~~~~~~

Including the private members as well

.. autoclass:: ClassWithMethodAttributes
    :members:
    :show-inheritance:
    :private-members:

Hidden methods
~~~~~~~~~~~~~~

Including the hidden members as well

.. autoclass:: ClassWithMethodAttributes
    :members:
    :show-inheritance:
    :hidden-members:

Friend methods
~~~~~~~~~~~~~~

Including the friend members as well

.. autoclass:: ClassWithMethodAttributes
    :members:
    :show-inheritance:
    :friend-members:

ClassWithPropertyAttributes
+++++++++++++++++++++++++++

A Matlab class with different property attributes

.. literalinclude:: ../test_data/ClassWithPropertyAttributes.m
   :language: matlab

Public properties
~~~~~~~~~~~~~~~~~

By default only the public properties will be included

.. autoclass:: ClassWithPropertyAttributes
    :members:
    :show-inheritance:

Protected properties
~~~~~~~~~~~~~~~~~~~~

Including the protected members as well

.. autoclass:: ClassWithPropertyAttributes
    :members:
    :show-inheritance:
    :protected-members:

Private properties
~~~~~~~~~~~~~~~~~~

Including the private members as well

.. autoclass:: ClassWithPropertyAttributes
    :members:
    :show-inheritance:
    :private-members:

Hidden properties
~~~~~~~~~~~~~~~~~

Including the hidden members as well

.. autoclass:: ClassWithPropertyAttributes
    :members:
    :show-inheritance:
    :hidden-members:

ClassWithAttributes
+++++++++++++++++++

A MATLAB class with class attributes.

.. autoclass:: ClassWithAttributes
    :members:
    :show-inheritance:

ClassWithUnknownAttributes
++++++++++++++++++++++++++

A MATLAB class with unknown class attributes.

.. autoclass:: ClassWithUnknownAttributes
    :members:
    :show-inheritance:


ClassWithGetterSetter
+++++++++++++++++++++

A MATLAB class with getter and setter methods for a property, these are should
not be documented.

.. autoclass:: ClassWithGetterSetter
    :members:
    :show-inheritance:

ClassWithDoubleQuotedString
+++++++++++++++++++++++++++

A MATLAB class with strings using double quotes.

.. autoclass:: ClassWithDoubleQuotedString
    :members:

ClassWithStrings
++++++++++++++++

A MATLAB class with strings using single and double quotes.

.. autoclass:: ClassWithStrings
    :members:

ClassWithDummyArguments
+++++++++++++++++++++++

A MATLAB class where one method, has a dummy argument as first argument.

.. autoclass:: ClassWithDummyArguments
    :members:

FunctionWithNameMismatch
++++++++++++++++++++++++

.. autofunction:: f_with_name_mismatch

FunctionWithDummyArgument
+++++++++++++++++++++++++
.. autofunction:: f_with_dummy_argument


FunctionWithLatin1Encoding
++++++++++++++++++++++++++
.. autofunction:: f_with_latin_1


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

A matlab application (``.mlapp`` file)
++++++++++++++++++++++++++++++++++++++

.. autoapplication:: test_data.Application

This is a reference to an application :app:`test_data.Application`

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

