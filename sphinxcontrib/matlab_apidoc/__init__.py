"""``scmd apidoc``: write reST pages that document a project's MATLAB files.

The pages use sphinxcontrib-matlabdomain directives.

``main(argv)`` runs the command line; ``generate(source_index, options)``
writes the pages of a ``mat_types.build_index`` result.

:copyright: Copyright 2014-2026 by the sphinxcontrib-matlabdomain team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

from ._cli import main
from ._generate import ApidocOptions, generate

__all__ = ["ApidocOptions", "generate", "main"]
