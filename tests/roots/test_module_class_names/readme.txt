Testing that we can have a structure like:

   Myclass/
      MyModule/
      MyOtherClass/
         MyOtherClass.m
      Myclass.m
   MyModule/
   YourClass.m

Without getting conclicts over the names in `entities_table`. Further, we test
that auto-linking also works.

Regular build.::

    make html

Regular build with very verbose settings, piped to file.::

    sphinx-build -vvv -b html . _build\html > sphinx.log


With "auto link" enabled, note the output folder is changed to ``_build\autolink\html``.::

    sphinx-build -D matlab_auto_link="all" -b html . _build\autolink\html
