sphinxcontrib-matlabdomain-0.20.0 (2023-MM-DD)
==============================================

* Fixed `Issue 188`_ and `Issue 189`_, which caused the extension to crash if
  the documentation contained ``:exclude-members:``.
* Added a new configuration: ``matlab_auto_links``. It will automatically
  convert the names of known entities (e.g. classes, functions, properties,
  methods) to links! This means that we can write class documentation as `MATLAB
  Class Help`_ suggests. Including property and methods lists in the class
  docstring.

.. _Issue 188: https://github.com/sphinx-contrib/matlabdomain/issues/188
.. _Issue 189: https://github.com/sphinx-contrib/matlabdomain/issues/189
.. _MATLAB Class Help:  https://mathworks.com/help/matlab/matlab_prog/create-help-for-classes.html


sphinxcontrib-matlabdomain-0.19.1 (2023-05-17)
==============================================

* Fix parsing of classes with trailing ``;`` after ``end``
* Fix bug if extension is included, but ``matlab_src_dir`` is not set.


sphinxcontrib-matlabdomain-0.19.0 (2023-05-16)
==============================================

* Added new configuration: ``matlab_short_links``. Finally, we are getting
  closer to render documentation closer to how MathWorks does it. The parsing of
  MATLAB functions, clasess, etc. was rewritten. We now parse all MATLAB files
  in ``matlab_src_dir``. Further, you can now generate docs for files in the
  root folder (something that only worked for packages before).
* We also updated the class rendering to be closer to that of MathWorks. Instead
  of putting both properties and methods together, they are now grouped by:
  *Constructor Summary*, *Property Summary* and *Method Summary*. Below is an
  example of how the ``ClassBar`` from
  ``tests/roots/test_autodoc/target/+package/ClassBar.m`` was rendered before
  and after.

  Before

    .. image:: docs/render_classes_0.18.0.png
      :alt: Rendering of default ``ClassBar.m`` in 0.18.0

  After

    .. image:: docs/render_classes_0.19.0.png
      :alt: Rendering of default ``ClassBar.m`` in 0.19.0


sphinxcontrib-matlabdomain-0.18.0 (2023-04-14)
==============================================

* Improved rendering of class property default values when
  ``matlab_show_property_default_value = True``. Multiline default values are
  now truncated to one line. Excessive spacing is removed and values are just
  shown verbatim as they were parsed instead of in string.

  * Before

    .. image:: docs/render_default_values_0.17.1.png
      :alt: Rendering default property values in 0.17.1

  * After

    .. image:: docs/render_default_values_0.18.0.png
      :alt: Rendering default property values in 0.18.0


sphinxcontrib-matlabdomain-0.17.1 (2023-04-12)
==============================================

* Fix issue with incorrect parsing of baseclasses with trailing comments.
  Reported in `Issue 172 <https://github.com/sphinx-contrib/matlabdomain/issues/172>`_.


sphinxcontrib-matlabdomain-0.17.0 (2023-03-24)
==============================================

* Replace ``directive.warn`` (deprecated) with ``logger.warning``. Reported in
  `Issue 166 <https://github.com/sphinx-contrib/matlabdomain/issues/166>`_.
* Fix property validation parsing reported in
  `Issue 167 <https://github.com/sphinx-contrib/matlabdomain/issues/167>`_.
* Updated Author to Jørgen Cederberg as agreed in
  `Issue 164 <https://github.com/sphinx-contrib/matlabdomain/issues/164>`_.


sphinxcontrib-matlabdomain-0.16.0 (2023-03-15)
==============================================

* Add new option, ``matlab_show_property_default_value``. Default is now to not
  show property values. If a property value is ``None``, is not shown anymore.


sphinxcontrib-matlabdomain-0.15.2 (2023-03-14)
==============================================

* Fix issue with not parsing property docstrings correctly with Pygments 2.13.
  `Issue 152 <https://github.com/sphinx-contrib/matlabdomain/issues/152>`_.


sphinxcontrib-matlabdomain-0.15.1 (2023-02-06)
==============================================

* Fix being unable to document methods with name ``get``.
  `Issue 151 <https://github.com/sphinx-contrib/matlabdomain/issues/151>`_.


sphinxcontrib-matlabdomain-0.15.0 (2023-01-02)
==============================================

* Pygments >= 2.14.0 is now supported. Pygments tokenization changed to return
  ``Token.Text.WhiteSpace`` for newline characters. This resulted in a infinite
  loop when parsing MATLAB files.


sphinxcontrib-matlabdomain-0.14.1 (2022-09-02)
==============================================

* Fix parsing of overloaded class parameters with validation functions.
  `Issue 145 <https://github.com/sphinx-contrib/matlabdomain/issues/145>`_.
* Fix link in readme file.


sphinxcontrib-matlabdomain-0.14.0 (2022-06-01)
==============================================

* Sphinx >= 5.0.0 is now supported. Fixed errors due to `deprecated Sphinx API`_.
* Fixed `https://github.com/sphinx-contrib/matlabdomain/issues/134`_.
  JupyterBook complains if a domain doesn't support resolve_any_ref_.

.. _`resolve_any_ref`: https://www.sphinx-doc.org/en/master/extdev/domainapi.html?highlight=resolve_any_xref#sphinx.domains.Domain.resolve_any_xref


sphinxcontrib-matlabdomain-0.13.0 (2022-02-13)
==============================================

* Explicit set ``parallel_read_safe`` to ``False`` to avoid error in parallel
  builds.
* Fixed `Issue 125 <https://github.com/sphinx-contrib/matlabdomain/issues/125>`_.
  Finally, we are able to support *long* docstrings for properties. It works as
  the same as MATLAB. Comment lines above a ``property`` are now treated as
  docstrings.


sphinxcontrib-matlabdomain-0.12.0 (2021-06-12)
==============================================

* Only Sphinx >= 4.0.0 is now supported.
* Only Python >= 3.6 is supported.
* Fixed numerous warnings due to `deprecated Sphinx API`_.
  * Use ``sphinx.ext.autodoc.directive.DocumenterBridge.record_dependencies``
    insted of ``sphinx.ext.autodoc.directive.DocumenterBridge.filename_set``.
  * Use ``str.rpartition()`` insted of ``sphinx.util.rpartition()``
  * Remove use of ``sphinx.util.force_decode()``.
  * Use ``inspect.getmembers()`` insted of
    ``sphinx.util.inspect.safe_getmembers()``.
  * Remove use of encoding argument in ``autodoc.Documenter.get_doc()``.
* Fixed `Issue 101 <https://github.com/sphinx-contrib/matlabdomain/issues/101>`_.
* CI now tests on Python 3.6, 3.7, 3.8 and 3.9.


sphinxcontrib-matlabdomain-0.11.8 (2021-05-12)
==============================================

*  Limit to Sphinx < 4.0.0, due to too many breaking changes.
*  Last version to support Python 2.7


sphinxcontrib-matlabdomain-0.11.7 (2021-02-24)
==============================================

* Fixed `Issue 117 <https://github.com/sphinx-contrib/matlabdomain/issues/117>`_.
  Parsing errors due to `"..."`.  Fix `MatObject::_remove_line_continuations`
  to take MATLAB strings into account.


sphinxcontrib-matlabdomain-0.11.6 (2021-02-23)
==============================================

* Fixed `Issue 116 <https://github.com/sphinx-contrib/matlabdomain/issues/116>`_.
  Failure on parfor statements in class methods. Fix `MatFunction` class to
  also take `parfor` into account when counting `end`.


sphinxcontrib-matlabdomain-0.11.5 (2021-01-05)
==============================================

* Fixed `Issue 114 <https://github.com/sphinx-contrib/matlabdomain/issues/114>`_.
  NoneType AttributeError in import_object. It was caused by a bug when parsing
  method names with trailing spaces.


sphinxcontrib-matlabdomain-0.11.4 (2020-11-30)
==============================================

* Remove import of ``six``.


sphinxcontrib-matlabdomain-0.11.3 (2020-10-10)
==============================================

* Fixed `Issue 108 <https://github.com/sphinx-contrib/matlabdomain/issues/108>`_.
  Quote is not recognized as transpose after a closing curly brace.

* Fixed `Issue 109 <https://github.com/sphinx-contrib/matlabdomain/issues/109`_.
  Sphinx 3.1.1 changed API causing tests to fail.

* Fixed `Issue 111 <https://github.com/sphinx-contrib/matlabdomain/issues/111>`_.
  fnable Function Arguments Support.



sphinxcontrib-matlabdomain-0.11.2 (2020-05-18)
==============================================

* Fixed `Issue 103 <https://github.com/sphinx-contrib/matlabdomain/issues/103>`_.
  If a double quoted string was followed by a single qouted string, the lexer
  would produce incorrect token, causing the a parser warning. Fixed by merging
  parts from pygments.


sphinxcontrib-matlabdomain-0.11.1 (2020-01-07)
==============================================

* Fixed bug when Python and MATLAB sources are in the same base folder. Reported
  by Alec Weiss. Historically we stored parsed MATLAB objects in
  ``sys.modules``. However, this conflicts with Python modules.


sphinxcontrib-matlabdomain-0.11.0 (2019-10-29)
==============================================

* Fixed `Issue 93 <https://github.com/sphinx-contrib/matlabdomain/issues/93>`_.
  If a package class inherited from another package class, the link to the base
  class was incorrect. This is fixed now.
* Merged `PR #96 <https://github.com/sphinx-contrib/matlabdomain/pull/96>`_,
  which adds the option ``matlab_keep_package_prefix``. Setting this option,
  strips the ``+`` from package names. This gives far better rendering of
  documentation, as now closer resembles the actual usage for the end user.
* Merged `PR #97 <https://github.com/sphinx-contrib/matlabdomain/pull/97>`_,
  which adds support for documenting MATLAB application files with a new
  directive ``application``. They are referenced with ``app``


sphinxcontrib-matlabdomain-0.10.0 (2019-10-23)
==============================================

* Fixed `Issue 63 <https://github.com/sphinx-contrib/matlabdomain/issues/63>`_.
  Finally, documents can have Python and MATLAB sources auto-documented
  together. Before, the MATLAB autodoc directives shadowed the Python
  directives, making it impossible for them to co-exist. The MATLAB modules now
  have their own module index generated.


sphinxcontrib-matlabdomain-0.9.0 (2019-05-29)
=============================================

* Merge `PR #92 <https://github.com/sphinx-contrib/matlabdomain/pull/92>`_
  Fix autodoc parsing error when source matlab file is not encoded as UTF-8.
  This adds the option ``matlab_src_encoding``, where one can define a different
  source file encoding. Default is to use utf-8, where unknown characters are
  replaced with �. This fixes a long time issue with the parser failing with
  non utf-8 files.


sphinxcontrib-matlabdomain-0.8.0 (2019-05-11)
=============================================

* Fixed `Issue 91 <https://github.com/sphinx-contrib/matlabdomain/issues/91>`_.
  Static methods in folder based classes.
* Replaced Pygments MATLAB lexer with own. Removes issues with functions being
  incorrectly parsed, handles double qouted string correctly.


sphinxcontrib-matlabdomain-0.7.1 (2019-04-03)
=============================================

* Fixed `Issue 90 <https://github.com/sphinx-contrib/matlabdomain/issues/90>`_.
  Wrong function name parsed when method escapes first argument with ~.


sphinxcontrib-matlabdomain-0.7.0 (2019-03-29)
=============================================
* Support for Sphinx >=2.0.0. Fixes
  `Issue 89 <https://github.com/sphinx-contrib/matlabdomain/issues/84>`_.


sphinxcontrib-matlabdomain-0.6.0 (2019-03-29)
=============================================
* Limit to Sphinx <2.0.0 as a temporary fix, until support for Sphinx 2.0.0 is
  fixed.


sphinxcontrib-matlabdomain-0.5.0 (2019-02-02)
=============================================

* Fixed `Issue 84 <https://github.com/sphinx-contrib/matlabdomain/issues/84>`_.
  Undocumented members are always included regardless of :undoc-members:.
* Fixed `Issue 85 <https://github.com/sphinx-contrib/matlabdomain/issues/65>`_.
  Matlab parsing "seems" to hang if code contains a bunch of "%" consecutively.
  Thanks to GulyasGergelyR for reporting and providing a much better solution.
* Fixed `Issue 86 <https://github.com/sphinx-contrib/matlabdomain/issues/86>`_.
  Handles the ``DeprecationWarning: `formatargspec` is deprecated since Python
  3.5. Use `signature` and the `Signature` object directly.
* Fixed `Issue 87 <https://github.com/sphinx-contrib/matlabdomain/issues/87>`_.
  Strings in double quotes are not parsed correctly by pygments.
* Closed `Issue 82 <https://github.com/sphinx-contrib/matlabdomain/issues/82>`_.
  Instead of renaming getter and setter functions to `get_whatever`, they are
  not documented anymore. This is in line with MATLAB documentation
  https://se.mathworks.com/help/matlab/matlab_oop/property-access-methods.html,
  as these functions cannot be called directly.


sphinxcontrib-matlabdomain-0.4.0 (2018-10-05)
=============================================

* Fixed `Issue 69 <https://github.com/sphinx-contrib/matlabdomain/issues/69>`_.
  Autodoc for script header. Thanks to Hugo Leblanc for this contribution.


sphinxcontrib-matlabdomain-0.3.5 (2018-09-28)
=============================================

* Fixed `Issue 79 <https://github.com/sphinx-contrib/matlabdomain/issues/79>`_.
  Enumerations and events cause premature end of m-file parsing.


sphinxcontrib-matlabdomain-0.3.4 (2018-09-13)
=============================================

* Adapt to Sphinx 1.8.


sphinxcontrib-matlabdomain-0.3.3 (2018-07-13)
=============================================

* Fixed bug where a line continuation (...) in a string could cause the parser
  to fail.

* Fixed bug introduced in 0.3.2. The word 'function' was also replaced in
  docstrings.


sphinxcontrib-matlabdomain-0.3.2 (2018-07-12)
=============================================

* Fixed bug where a MATLAB class method containing a variable starting with
  'function' would cause the parser to fail.


sphinxcontrib-matlabdomain-0.3.1 (2018-07-12)
=============================================

* Fixed bug where a MATLAB script with only comments would cause an error.


sphinxcontrib-matlabdomain-0.3.0 (2018-04-10)
==============================================

* Fixed `Issue 66 <https://github.com/sphinx-contrib/matlabdomain/issues/66>`_.
  Sphinx 1.7 broke autodoc :members: functionality.
* Changed the requirement to Sphinx >= 1.7.2!


sphinxcontrib-matlabdomain-0.2.17 (2018-04-09)
==============================================

* Fixed `Issue 66 <https://github.com/sphinx-contrib/matlabdomain/issues/66>`_.
  Sphinx 1.7 broke autodoc :members: functionality.
* In this release Sphinx is locked to versions below 1.7, the next release will
  require Sphinx > 1.7.
* Added tests of autodoc capabilities.


sphinxcontrib-matlabdomain-0.2.16 (2018-03-05)
==============================================

* Fixed `Issue 13 <https://github.com/sphinx-contrib/matlabdomain/issues/13>`_.
  crashes if filename and classname are different.
* Fixed `Issue 19 <https://github.com/sphinx-contrib/matlabdomain/issues/19>`_.
  crashes if classdef docstring is not indented
* Fixed `Issue #41 <https://github.com/sphinx-contrib/matlabdomain/issues/41>`_.
  Problem with non ascii characters.


sphinxcontrib-matlabdomain-0.2.15 (2018-02-25)
==============================================

* Fixed `Issue #30 <https://github.com/sphinx-contrib/matlabdomain/issues/30>`_.
  Some definition of attributes for the "properties" or "methods" blocks causes
  Sphinx to crash.
* Fixed `Issue #57 <https://github.com/sphinx-contrib/matlabdomain/issues/57>`_.
  Parser fails while parsing new syntax extensions for the class properties.


sphinxcontrib-matlabdomain-0.2.14 (2018-02-23)
==============================================

* Merge `PR #60 <https://github.com/sphinx-contrib/matlabdomain/pull/60>`_
  Dependency fix for Sphinx 1.7.
* Added cleobis to as contributor


sphinxcontrib-matlabdomain-0.2.13 (2018-01-12)
==============================================

* Fix bug when parsing a function without output and no parentheses.
* Better error messages during parsing of functions.


sphinxcontrib-matlabdomain-0.2.12 (2018-01-10)
==============================================

* Fixed `Issue #27 <https://github.com/sphinx-contrib/matlabdomain/issues/27>`_.
  An "events" block in a class causes Sphinx to hang.
* Fixed `Issue #52 <https://github.com/sphinx-contrib/matlabdomain/issues/52>`_.
  An "enumeration" block in a class causes Sphinx to hang
* Merge `PR #51 <https://github.com/sphinx-contrib/matlabdomain/pull/51>`_
  better exception, when input args contains "..."
* Added Christoph Boeddeker as author.


sphinxcontrib-matlabdomain-0.2.11 (2017-11-28)
==============================================

* Fixed `Issue #42 <https://github.com/sphinx-contrib/matlabdomain/issues/42>`_.
  Comment strings after a function docstring are not included in the docstring
  anymore.
* Fixed `Issue #50 <https://github.com/sphinx-contrib/matlabdomain/issues/50>`_.
  Added Lukas Drude as author.


sphinxcontrib-matlabdomain-0.2.10 (2017-11-27)
==============================================

* Add Jørgen Cederberg as maintainer.
* Change bitbucket links to github ditto.


sphinxcontrib-matlabdomain-0.2.9 (2017-11-23)
=============================================

Development migrated to https://github.com/sphinx-contrib/matlabdomain

* Merge `PR #1 <https://github.com/sphinx-contrib/matlabdomain/pull/1>`_


sphinxcontrib-matlabdomain-0.2.8 (2016-12-15)
=============================================

* merge PR #2 nested functions


sphinxcontrib-matlabdomain-0.2.6 (2014-11-10)
=============================================

* fix issues #30


sphinxcontrib-matlabdomain-0.2.5 (2014-10-02)
=============================================

* fix issues #21
* changeset 8f18a8f adds [+@]? to regular expression for matlab signatures
* add Octave to sphinx-contrib README and link to sphinxcontrib-matlabdomain on
  PyPI
* update and include CHANGES in README so they're in PyPI documentation


sphinxcontrib-matlabdomain-0.2.4 (2014-02-21)
=============================================

* fix issues #17, #18
* vastly simplify regex used to remove ellipsis from function signatures
* save parsed mat_types in modules that are saved in sys.modules, and
  retrieve them instead of re-parsing mfiles everytime!


sphinxcontrib-matlabdomain-0.2.3 (2014-02-20)
=============================================

* fix critical bug in class properties, arrays and expressions with ellipsis
  were incorrectly handled


sphinxcontrib-matlabdomain-0.2.2 (2014-01-26)
=============================================

* fix ellipsis in function in output arg
* fix bases getter method had no default, so crashing build
* add catchall warning if getter fails and no default in MatObject.getter()
* fix local path used to index sys.module, instead of full path, oops!
* fix left-strip dot if in basedir, root_mod is '', so join yields ".test_data"


sphinxcontrib-matlabdomain-0.2.1 (2014-01-24)
=============================================

* allow property defaults to span multiple lines, even w/o ellipsis, and ignore
  ellipsis comments
* correct Pygments ellipsis not allowed in function signature error
* allow builtin names to be used as property names
* fix keyword-end counter bugs, add group incrementer counter, incl curly-braces
* fix module has no docstring attr bug in MatModuleAnalyzer
* allow empty property block
* allow no function return or empty input args


sphinxcontrib-matlabdomain-0.2 (2014-01-23)
===========================================

* add autodoc capabilities for MATLAB domain


sphinxcontrib-matlabdomain-0.1 (2013-04-25)
===========================================

* create a Sphinx domain for MATLAB
* override standard domain to remove py modules index

.. _`deprecated Sphinx API`: https://www.sphinx-doc.org/en/master/extdev/deprecated.html
