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
