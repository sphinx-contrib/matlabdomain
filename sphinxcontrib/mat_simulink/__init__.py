"""Read Simulink model files (``.slx``, ``.mdl``, exported ``.xml``)
without MATLAB.

``classify`` gives the kind of a file cheaply (index stage);
``read_diagram`` reads what the documentation needs (parse stage). The
formats and what changes between releases are described in the developer
guide page "Simulink file formats".
"""

from ._model import (
    KINDS,
    Diagram,
    LibraryBlock,
    Mask,
    MaskParameter,
    Port,
    Reference,
    classify,
    is_exported_xml,
    read_diagram,
    simulink_release,
)
from ._parts import SimulinkFileError

__all__ = [
    "KINDS",
    "Diagram",
    "LibraryBlock",
    "Mask",
    "MaskParameter",
    "Port",
    "Reference",
    "SimulinkFileError",
    "classify",
    "is_exported_xml",
    "read_diagram",
    "simulink_release",
]
