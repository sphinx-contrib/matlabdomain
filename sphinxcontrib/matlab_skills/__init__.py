"""``scmd skills``: the agent skills that ship with the package.

Each skill is one folder with a ``SKILL.md``; the command lists them and
copies them into a project. ``main(argv)`` runs the command line.

:copyright: Copyright 2014-2026 by the sphinxcontrib-matlabdomain team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

from ._cli import main

__all__ = ["main"]
