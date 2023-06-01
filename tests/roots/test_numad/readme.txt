Test of class options
---------------------

Regular build.::

    make html

Regular build with very verbose settings, piped to file.::

    sphinx-build -vvv -b html . _build\html > sphinx.log


With "short links" enabled, note the output folder is changed to ``_build\short\html``.::

    sphinx-build -D matlab_short_links=True -b html . _build\short\html
