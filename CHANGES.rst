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
