"""sphinxcontrib.matlab_skills.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``scmd skills``: the agent skills that ship with the package (one folder
with a ``SKILL.md`` each) and the command that lists them and copies them
into a project. ``main(argv)`` runs the command line.

:copyright: Copyright 2014-2026 by the sphinxcontrib-matlabdomain team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

from ._cli import main

__all__ = ["main"]
