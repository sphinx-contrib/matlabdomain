# -*- coding: utf-8 -*-
"""
    sphinxcontrib.test.helper
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: Copyright 2023 Joergen Cederberg
    :license: BSD, see LICENSE for details.
"""


from sphinx import version_info as sphinx_version_info
import os.path

if sphinx_version_info[0] > 6:
    # from sphinx.testing.path was deprecated in version 7.2
    # https://www.sphinx-doc.org/en/master/extdev/deprecated.html
    from pathlib import Path as path

    def rootdir(the_file):
        return path(os.path.dirname(__file__)).absolute()

else:
    from sphinx.testing.path import path

    def rootdir(the_file):
        return path(os.path.dirname(__file__)).abspath()
