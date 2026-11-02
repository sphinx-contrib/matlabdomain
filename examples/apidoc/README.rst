sphinx-matlab-apidoc example
============================

A small MATLAB project (``src/``), its Sphinx project (``docs/``) and an
edited copy of the default templates (``templates/``). The pages in
``docs/api/`` are generated and committed; ``tests/test_apidoc.py``
regenerates them, compares them with these files and builds the project with
``-W``.

``src/`` has a ``+demo`` namespace with a nested ``+geometry`` namespace, an
``@Shape`` class folder with method files, a plain folder of global functions
(``utils/``) with a ``private/`` folder, a script and an App Designer app.
It also has pages next to code: a Markdown tutorial with an image and a
README in ``+demo/``, and a reST page in ``utils/`` (``conf.py`` turns them
on and loads ``myst_parser``).

Regenerate and build, from ``docs/``::

    sphinx-matlab-apidoc -c .
    sphinx-build -n -W -b html . _build/html

``-c .`` reads ``conf.py``: the MATLAB root
(``matlab_src_code_project_root``), the output folder
(``matlab_apidoc_output_dir``) and the templates
(``matlab_apidoc_templatedir``). ``sphinx-matlab-apidoc --check -c .``
exits with 1 when the pages are out of date.

The templates differ from the defaults in two places: the root page is
titled "Demo API reference", and classes are documented without
``:undoc-members:``. To customize your own output, copy these templates (or
the defaults in ``sphinxcontrib/matlab_apidoc/templates/``) into your
project, edit them and set ``matlab_apidoc_templatedir`` (or pass ``-t``).
