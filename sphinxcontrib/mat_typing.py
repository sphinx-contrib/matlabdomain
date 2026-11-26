"""The ``override`` decorator on every supported Python version.

It is ``typing.override``, or ``typing_extensions.override`` before Python
3.12. Ruff reads this module as ``typing`` (``lint.typing-modules`` in
``pyproject.toml``), so it knows that a method decorated with ``override``
overrides a base class method and must keep its signature.
"""

import sys

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

__all__ = ["override"]
