"""Read Simulink model files (``.slx``, ``.mdl``) without
MATLAB.

``classify`` gives the kind of a file cheaply (index stage);
``read_diagram`` reads what the documentation needs (parse stage). The
formats and what changes between releases are described in the developer
guide page "Simulink file formats". ``MATLAB_TOOLS`` is the folder of the
MATLAB functions behind the Help links (``+sphinxcontrib/+matlabdomain``).
"""

from pathlib import Path

from ._model import (
    KINDS,
    Diagram,
    LibraryBlock,
    Mask,
    MaskParameter,
    Port,
    Reference,
    classify,
    help_target,
    read_diagram,
    simulink_release,
)
from ._parts import SimulinkFileError

MATLAB_TOOLS = Path(__file__).parent / "matlab"

__all__ = [
    "KINDS",
    "MATLAB_TOOLS",
    "Diagram",
    "LibraryBlock",
    "Mask",
    "MaskParameter",
    "Port",
    "Reference",
    "SimulinkFileError",
    "classify",
    "help_target",
    "read_diagram",
    "simulink_release",
]
