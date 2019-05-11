sphinxcontrib-matlabdomain-0.8.0 (2019-05-11)
=============================================

* Fixed ``Issue 91 <https://github.com/sphinx-contrib/matlabdomain/issues/91>`_.
  Static methods in folder based classes.
* Replaced Pygments MATLAB lexer with own. Removes issues with functions being
  incorrectly parsed, handles double qouted string correctly.


sphinxcontrib-matlabdomain-0.7.1 (2019-04-03)
=============================================

* Fixed ``Issue 90 <https://github.com/sphinx-contrib/matlabdomain/issues/90>`_.
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
  Handles the ``DeprecationWarning: `formatargspec` is deprecated since Python 3.5. Use `signature` and the `Signature` object directly.
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
