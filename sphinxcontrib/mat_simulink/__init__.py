"""Read Simulink model files (``.slx``, ``.mdl``, exported ``.xml``)
without MATLAB.

``classify`` gives the kind of a file cheaply (index stage);
``read_diagram`` reads what the documentation needs (parse stage). The
formats and what changes between releases are described in the developer
guide page "Simulink file formats".
"""

from ._model import (
    Diagram,
    LibraryBlock,
    Mask,
    MaskParameter,
    Port,
    Reference,
    classify,
    read_diagram,
    simulink_release,
)
from ._parts import SimulinkFileError

__all__ = [
    "Diagram",
    "LibraryBlock",
    "Mask",
    "MaskParameter",
    "Port",
    "Reference",
    "SimulinkFileError",
    "classify",
    "read_diagram",
    "simulink_release",
]
