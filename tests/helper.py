"""sphinxcontrib.test.helper.
~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: Copyright Joergen Cederberg
:license: BSD, see LICENSE for details.
"""

import os
from pathlib import Path


def rootdir(file):
    return Path(os.path.dirname(__file__)).resolve().absolute()
