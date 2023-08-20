# -*- coding: utf-8 -*-
"""
    sphinxcontrib.test.helper
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: Copyright 2023 Joergen Cederberg
    :license: BSD, see LICENSE for details.
"""


from sphinx import version_info as sphinx_version_info
import os.path

if sphinx_version_info[0] >= 7 and sphinx_version_info[1] >= 2:
    # from sphinx.testing.path was deprecated in version 7.2
    # https://www.sphinx-doc.org/en/master/extdev/deprecated.html
    from pathlib import Path

    def rootdir(the_file):
        return Path(os.path.dirname(__file__)).absolute()

else:
    from sphinx.testing.path import path as sphinx_path

    def rootdir(the_file):
        return sphinx_path(os.path.dirname(__file__)).abspath()
