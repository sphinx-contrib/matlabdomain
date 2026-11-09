Builds and performance
======================

The :term:`extension` is built for projects with thousands of files: a build reads
each file once, parses only what the pages use, and an unchanged file is
never read or parsed again.

What a build does
-----------------

1. **Index.** When the build starts, the extension walks the project root,
   reads each selected file once, decodes it, and finds its type from its
   first line of code. It names every file and folder the way MATLAB would.
   This is fast (well under a second for a few thousand files) and needs no
   parser.
2. **Parse on demand.** A file is parsed with tree-sitter only when a page
   needs its contents: to document it, to show a base class, or to link a
   name in help text. A project of 2,000 files whose pages document 30 of
   them parses about 30 files.
3. **Cache.** Parsed files are kept in Sphinx's :term:`environment`, keyed by the
   file's path, modification time and size. The next build reuses them while
   none of these change; a file whose size or time changed is parsed again.

The index keeps decoded text in memory for the parse, avoiding a second read
when a newly indexed file is parsed in the same process.

Incremental builds
------------------

Sphinx reads only the pages that changed. The extension adds the pages that
used a changed MATLAB file: edit ``Circle.m`` and the page that documents
it is read again; edit a file no page uses and nothing is read again. When
files or folders are added, removed or change type, every page that looks
up MATLAB files is read again, because a name may now mean another file.

Changing a ``matlab_*`` setting (other than the ``matlab_api_check_*`` ones)
reads every page again and drops the
cached parses. Upgrading the extension may do the same.

Pages that only *link* to an :term:`object` with a :term:`role` are not read again when
the object's file changes; this is Sphinx's usual behavior for
cross-references.

Warnings found while reading a page appear only in the build that reads it:
after a failed ``-W`` build, a rebuild may say that nothing is out of date.
To see every warning again (for example after changing
``nitpick_ignore``), build from scratch with ``-E``.

Building some pages
-------------------

``sphinx-build`` accepts page files after the output folder
(``sphinx-build -b html docs docs/_build/html docs/api/shapes.rst``). Sphinx
still reads every page that is out of date, and writes only the pages
given (with a warning that the search index is incomplete). The extension
behaves as in a full build: it indexes the whole project root and parses
the files the pages it reads use, so links to objects on other pages work.
The ``matlab-api-check`` builder ignores the page list: it checks every
indexed file.

Parallel builds
---------------

``sphinx-build -j auto`` reads pages in parallel; the extension is safe for
parallel reading and writing, and the output is the same as a serial build.
Sphinx runs parallel builds only where processes can be forked (Linux,
macOS); on Windows, ``-j`` builds serially.

Large projects
--------------

* Exclude what needs no documentation (tests, generated data, vendored
  copies) with :confval:`matlab_src_exclude_patterns`; excluded folders
  are not even listed.
* Large generated data files (megabytes of numbers in a ``.m`` file) are
  slow to parse when a page documents them.
* ``scmd apidoc`` writes only the pages whose text changed, so
  regenerating before each build does not trigger a full rebuild.
* The ``matlab-api-check`` builder parses every file on each run.

For a sense of scale: the 14 open-source projects the extension is tested
on (24,000 files, the largest 5,300 files) build with
``scmd apidoc`` pages in 1 to 60 seconds each.

Working with other tools
------------------------

* `sphinx-autobuild <https://github.com/sphinx-doc/sphinx-autobuild>`_:
  works; MATLAB files are not watched unless you add them. With
  ``scmd apidoc`` pages, also run the generator before each
  build, so new and moved files get pages:

  .. code-block:: console

     $ uv run sphinx-autobuild docs docs/_build/html --watch src --pre-build "uv run scmd apidoc --conf-dir docs --quiet"

  A change that the generator turns into a page change triggers one more
  build. The ``--pre-build`` command is split like a POSIX shell line, so
  on Windows write paths in it with ``/`` (or run it from the activated
  environment, as above). ``--watch`` the folder of
  :confval:`matlab_src_code_project_root` (``src`` above); that covers
  sidecar docs too. The extension cannot configure sphinx-autobuild
  itself, so these options go on its command line.
* `sphinx-multiversion <https://github.com/sphinx-contrib/multiversion>`_:
  works on Sphinx 8 when each version's commit holds its API pages; a
  relative :confval:`matlab_src_code_project_root` is relative to the
  Sphinx source folder, which it moves. See :doc:`projects-and-versions`,
  also for several projects, sphinx-multiproject and one search over
  several sites.
