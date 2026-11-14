"""The format-neutral content of a Simulink file and the readers that
build it from SLX, OPC text ``.mdl`` and classic ``.mdl``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ._nodes import Node, decode_mdl, parse_mdl, parse_xml
from ._parts import (
    Parts,
    SimulinkFileError,
    check_size,
    opc_text_parts,
    read_head,
    sniff,
    zip_parts,
)

KINDS = ("model", "library", "subsystem")
CORE = "metadata/coreProperties.xml"
BLOCK_DIAGRAM = "simulink/blockdiagram.xml"
_USED = (
    "simulink/blockdiagram.xml",
    "simulink/bddefaults.xml",
    "simulink/modelmask.xml",
)
PORT_TYPES = ("Inport", "Outport", "PMIOPort")
# Listed by type after the numbered ports, with no number or data type.
CONTROL_PORT_TYPES = ("EnablePort", "TriggerPort", "ActionPort")
# Simulink's defaults, for files that do not save them (bddefaults.json).
PORT_DEFAULTS = {
    "Port": "1",
    "OutDataTypeStr": "Inherit: auto",
    "PortDimensions": "-1",
    "Unit": "inherit",
    "Description": "",
}
OLD_MASK_KEYS = ("MaskType", "MaskDescription", "MaskHelp", "MaskPromptString")
# Simulink version -> release, before versions followed the release (R2023b).
_RELEASES = {
    **{f"6.{n}": f"R{2006 + (n - 4) // 2}{'ab'[n % 2]}" for n in range(4, 7)},
    **{f"7.{n}": f"R{2007 + (n + 1) // 2}{'ba'[n % 2]}" for n in range(10)},
    **{f"8.{n}": f"R{2012 + (n + 1) // 2}{'ba'[n % 2]}" for n in range(10)},
    **{f"9.{n}": f"R{2017 + (n + 1) // 2}{'ba'[n % 2]}" for n in range(4)},
    **{f"10.{n}": f"R{2019 + (n + 1) // 2}{'ba'[n % 2]}" for n in range(8)},
}


@dataclass(frozen=True)
class MaskParameter:
    name: str
    prompt: str
    type: str
    value: str
    options: tuple[str, ...] = ()
    #: False for a parameter the mask dialog does not show (``Visible`` off)
    visible: bool = True


@dataclass(frozen=True)
class Mask:
    type: str
    description: str
    help: str
    initialization: str = ""
    parameters: tuple[MaskParameter, ...] = ()


@dataclass(frozen=True)
class Port:
    block_type: str
    name: str
    number: str
    data_type: str
    dimensions: str
    unit: str
    description: str
    port_name: str = ""
    element: str = ""


@dataclass(frozen=True)
class Reference:
    """A model reference (``model``), subsystem reference (``subsystem``)
    or library link (``library``) of the block at ``block``.
    """

    kind: str
    block: str
    target: str


@dataclass(frozen=True)
class LibraryBlock:
    """A block found by the library walk: documented (``mask`` set), a
    link to another library's block (``link`` set) or a sublibrary block
    that opens another library (``opens`` set).
    """

    path: str
    description: str
    mask: Mask | None
    link: str = ""
    ports: tuple[Port, ...] = ()
    opens: str = ""


@dataclass(frozen=True)
class Diagram:
    name: str
    kind: str
    layout: str
    description: str
    release: str
    metadata: tuple[tuple[str, str], ...]
    system_mask: Mask | None
    ports: tuple[Port, ...]
    references: tuple[Reference, ...]
    library_blocks: tuple[LibraryBlock, ...]


def simulink_release(version: str) -> str:
    """Return the release of a Simulink version (``8.6`` -> ``R2015b``,
    ``24.1`` -> ``R2024a``), or ``""``.
    """
    if version in _RELEASES:
        return _RELEASES[version]
    match = re.fullmatch(r"(2[3-9]|[3-9]\d)\.([12])", version)
    return f"R20{match.group(1)}{'ab'[int(match.group(2)) - 1]}" if match else ""


def _used(name: str) -> bool:
    """Parts the reader uses (model workspace, data and images are not)."""
    return (
        name in _USED
        or (name.startswith("metadata/") and name.endswith(".xml"))
        or (name.startswith("simulink/systems/") and name.endswith(".xml"))
    )


def _is_core(name: str) -> bool:
    return name == CORE.lower()


def _is_block_diagram(name: str) -> bool:
    return name == BLOCK_DIAGRAM


_LINKER = "sphinxcontrib.matlabdomain.simulinkDocumentationLinker"
# A sublibrary block's OpenFcn: the library name, or open_system('name').
_OPENS = re.compile(
    r"""\s*(?:open_system\(\s*["']?([A-Za-z]\w*)["']?\s*\)|([A-Za-z]\w*))\s*;?\s*"""
)
# The schemes of a Help URL (R2026b Mask Editor documentation).
_SCHEMES = r"(?:https?|www|file|ftp|mailto):"
_URL = re.compile(rf"{_SCHEMES}\S+")
_WEB_URL = re.compile(rf"""web\(\s*(["'])({_SCHEMES}[^"']+)\1[^)]*\)\s*;?""")
_WEB_LINKER = re.compile(
    rf'web\(\s*{re.escape(_LINKER)}\(\s*("(?:[^"]|"")*"'
    r'(?:\s*\+\s*newline\s*\+\s*"(?:[^"]|"")*")*)\s*\)\s*\)\s*;?'
)


def help_target(text: str) -> tuple[str, str] | None:
    """Return what a mask Help opens: ``("url", url)`` for a URL on its first line
    or ``web("url")``, ``("reference", reference)`` for a
    ``web(sphinxcontrib.matlabdomain.simulinkDocumentationLinker("..."))``
    line, else None (text that Simulink shows as it is).
    """
    line = text.strip().split("\n", 1)[0].strip()
    if match := _WEB_LINKER.fullmatch(line):
        pieces = re.findall(r'"((?:[^"]|"")*)"', match.group(1))
        return "reference", "\n".join(p.replace('""', '"') for p in pieces)
    if match := _WEB_URL.fullmatch(line):
        return "url", match.group(2)
    if _URL.fullmatch(line):
        return "url", line
    return None


def classify(path) -> str:
    """Return ``model``, ``library``, ``subsystem`` or ``unknown``, reading
    as little as possible.
    """
    path = Path(path)
    layout = sniff(read_head(path))
    if layout == "zip":
        kind = _core_kind(zip_parts(path, _is_core))
        if kind == "unknown":
            kind = _root_kind(zip_parts(path, _is_block_diagram))
        return kind
    if layout == "opc":
        parts = opc_text_parts(path, lambda n: _is_core(n) or _is_block_diagram(n))
        kind = _core_kind(parts)
        return kind if kind != "unknown" else _root_kind(parts)
    if layout == "classic":
        check_size(path)
        head = read_head(path).decode("latin-1")
        word = re.search(r"(Model|Library|Subsystem)\s*\{", head)
        return word.group(1).lower() if word else "unknown"
    return "unknown"


def _core_kind(parts: Parts) -> str:
    data = parts.get(CORE)
    if data is None:
        return "unknown"
    category = parse_xml(data, CORE).child_text("category").strip().lower()
    return category if category in KINDS else "unknown"


def _root_kind(parts: Parts) -> str:
    data = parts.get(BLOCK_DIAGRAM)
    if data is None:
        return "unknown"
    root = parse_xml(data, BLOCK_DIAGRAM)
    tag = root.children[0].tag.lower() if root.children else ""
    return tag if tag in KINDS else "unknown"


def read_diagram(path) -> Diagram:
    """Read a Simulink file. Raises :class:`SimulinkFileError` for a file
    that is not a readable Simulink file.
    """
    path = Path(path)
    layout = sniff(read_head(path))
    if layout == "zip":
        return _Reader(path, "slx", zip_parts(path, _used)).from_package()
    if layout == "opc":
        return _Reader(path, "mdl-opc", opc_text_parts(path, _used)).from_package()
    if layout == "classic":
        check_size(path)
        sections = parse_mdl(decode_mdl(path.read_bytes()))
        root = next((s for s in sections if s.tag.lower() in KINDS), None)
        if root is None:
            raise SimulinkFileError("has no Model, Library or Subsystem section.")
        return _Reader(path, "mdl-classic", None).from_root(root)
    raise SimulinkFileError("is not a Simulink model, library or subsystem file.")


class _Reader:
    def __init__(self, path: Path, layout: str, parts: Parts | None):
        self.path = path
        self.layout = layout
        self.parts = parts
        self.defaults: Node | None = None

    def part(self, name: str) -> Node | None:
        data = self.parts.get(name) if self.parts is not None else None
        return parse_xml(data, name) if data is not None else None

    def from_package(self) -> Diagram:
        core = self.part(CORE) or Node("coreProperties")
        mwcore = self.part("metadata/mwcoreProperties.xml") or Node("mwcoreProperties")
        info = self.part(BLOCK_DIAGRAM)
        root = info.children[0] if info is not None and info.children else None
        kind = core.child_text("category").strip().lower()
        if kind not in KINDS:
            kind = root.tag.lower() if root is not None else ""
        if kind not in KINDS:
            raise SimulinkFileError("is not a Simulink model, library or subsystem.")
        if root is not None:
            self.defaults = root.find("BlockParameterDefaults")
        if self.defaults is None:
            bddefaults = self.part("simulink/bddefaults.xml")
            if bddefaults is not None:
                self.defaults = bddefaults.find("BlockParameterDefaults")
        system = root.find("System") if root is not None else None
        if system is None:
            system = Node("System", {"Ref": "system_root"})
        mask_node = self.part("simulink/modelMask.xml")
        release = mwcore.child_text("matlabRelease") or core.child_text("version")
        metadata = {
            "creator": core.child_text("creator"),
            "last_modified_by": core.child_text("lastModifiedBy"),
            "created": core.child_text("created"),
            "modified": core.child_text("modified"),
            "model_version": core.child_text("revision"),
            "release": release,
        }
        description = core.child_text("description")
        if not description and root is not None:
            description = root.param("Description")
        return self._diagram(
            kind,
            description,
            metadata,
            _system_mask(mask_node) if mask_node is not None else None,
            self.system(system),
        )

    def from_root(self, root: Node) -> Diagram:
        self.defaults = root.find("BlockParameterDefaults")
        release = simulink_release(root.param("Version"))
        metadata = {
            "creator": root.param("Creator"),
            "last_modified_by": root.param("LastModifiedBy"),
            "created": root.param("Created"),
            "modified": root.param("LastModifiedDate"),
            "model_version": re.sub(
                r"%<AutoIncrement:([^>]*)>", r"\1", root.param("ModelVersionFormat")
            ),
            "release": release,
        }
        system = root.find("System")
        return self._diagram(
            root.tag.lower(),
            root.param("Description"),
            metadata,
            None,
            system if system is not None else Node("System"),
        )

    def _diagram(self, kind, description, metadata, system_mask, system) -> Diagram:
        return Diagram(
            name=self.path.stem,
            kind=kind,
            layout=self.layout,
            description=description,
            release=metadata["release"],
            metadata=tuple((k, v) for k, v in metadata.items() if v),
            system_mask=system_mask,
            ports=self.ports(system),
            references=tuple(self.references(system, "")),
            library_blocks=tuple(self.walk(system, "")) if kind == "library" else (),
        )

    def system(self, node: Node) -> Node:
        """Return an inline ``System`` node, or the part a ``System Ref`` names."""
        ref = node.attrs.get("Ref")
        if not ref:
            return node
        name = f"simulink/systems/{ref}.xml"
        loaded = self.part(name)
        if loaded is None:
            raise SimulinkFileError(f"has no part {name}.")
        return loaded

    def subsystem(self, block: Node) -> Node | None:
        system = block.find("System")
        return self.system(system) if system is not None else None

    def default(self, block_type: str, name: str) -> str:
        if self.defaults is not None:
            for block in self.defaults.findall("Block"):
                if block.param("BlockType") == block_type and block.has(name):
                    return block.param(name)
        return PORT_DEFAULTS.get(name, "")

    def ports(self, system: Node) -> tuple[Port, ...]:
        """Return the port blocks of ``system``: by type, then by port number
        (the elements of a bus port in file order), then the control ports.
        """
        ports = []
        blocks = system.findall("Block")
        for block_type in (*PORT_TYPES, *CONTROL_PORT_TYPES):
            of_type = []
            for block in blocks:
                if block.param("BlockType") != block_type:
                    continue

                def value(name: str, block=block, block_type=block_type) -> str:
                    if block.has(name):
                        return block.param(name)
                    return self.default(block_type, name)

                numbered = block_type in PORT_TYPES
                signal = block_type in ("Inport", "Outport")
                interface = next(
                    (
                        n
                        for n in block.findall("List")
                        if n.param("ListType") == "InterfaceData"
                    ),
                    block,
                )
                of_type.append(
                    Port(
                        block_type=block_type,
                        name=block.param("Name"),
                        number=value("Port") if numbered else "",
                        data_type=value("OutDataTypeStr") if signal else "",
                        dimensions=value("PortDimensions") if signal else "",
                        unit=value("Unit") if signal else "",
                        description=value("Description"),
                        port_name=interface.param("PortName"),
                        element=interface.param("Element"),
                    )
                )
            # sorted() is stable: the elements of a bus port keep their order.
            ports += sorted(of_type, key=_port_number)
        return tuple(ports)

    def references(self, system: Node, prefix: str) -> list[Reference]:
        found = []
        for block in system.findall("Block"):
            path = _join(prefix, block.param("Name"))
            block_type = block.param("BlockType")
            if block_type == "Reference":
                found.append(Reference("library", path, block.param("SourceBlock")))
            elif block_type == "ModelReference":
                found.append(Reference("model", path, block.param("ModelNameDialog")))
            elif block.param("ReferencedSubsystem"):
                found.append(
                    Reference("subsystem", path, block.param("ReferencedSubsystem"))
                )
            else:
                inner = self.subsystem(block)
                if inner is not None:
                    found.extend(self.references(inner, path))
        return found

    def walk(self, system: Node, prefix: str) -> list[LibraryBlock]:
        """Walk a library: a linked block is a link, an empty subsystem whose
        ``OpenFcn`` opens a library is a sublibrary block, a masked block is
        documented and not entered, an unmasked subsystem is entered.
        """
        found = []
        for block in system.findall("Block"):
            path = _join(prefix, block.param("Name"))
            description = block.param("Description")
            inner = self.subsystem(block)
            opens = _OPENS.fullmatch(block.param("OpenFcn"))
            if block.param("BlockType") == "Reference":
                found.append(
                    LibraryBlock(path, description, None, block.param("SourceBlock"))
                )
            elif opens and (inner is None or not inner.findall("Block")):
                name = opens.group(1) or opens.group(2)
                found.append(LibraryBlock(path, description, None, opens=name))
            elif (mask := block_mask(block)) is not None:
                ports = self.ports(inner) if inner is not None else ()
                found.append(LibraryBlock(path, description, mask, "", ports))
            elif inner is not None:
                found.extend(self.walk(inner, path))
        return found


def _port_number(port: Port) -> int:
    """Sort key: the port number; an unnumbered or odd one goes last."""
    return int(port.number) if port.number.isdigit() else 1 << 30


def _join(prefix: str, name: str) -> str:
    """Simulink path below the diagram; a ``/`` in a name is ``//``."""
    name = name.replace("/", "//")
    return f"{prefix}/{name}" if prefix else name


def _system_mask(part: Node) -> Mask | None:
    """``modelMask.xml``: ``<Mask>`` from R2017b, ``<ModelMask>`` holding a
    ``Simulink.Mask`` object in R2016b-R2017a.
    """
    return _element_mask(part) if part.tag == "Mask" else block_mask(part)


def block_mask(block: Node) -> Mask | None:
    element = block.find("Mask")
    if element is not None:
        return _element_mask(element)
    for obj in block.findall("Object"):
        if obj.attrs.get("ClassName") == "Simulink.Mask":
            return _object_mask(obj)
    if any(block.has(key) for key in OLD_MASK_KEYS):
        return _old_mask(block)
    return None


def _element_mask(mask: Node) -> Mask:
    """``<Mask>`` (SLX from R2017b, ``modelMask.xml``)."""
    parameters = tuple(
        MaskParameter(
            name=p.attrs.get("Name", ""),
            prompt=p.child_text("Prompt"),
            type=p.attrs.get("Type", ""),
            value=p.child_text("Value"),
            options=tuple(
                o.text for t in p.findall("TypeOptions") for o in t.findall("Option")
            ),
            visible=p.attrs.get("Visible", "on") != "off",
        )
        for p in mask.findall("MaskParameter")
    )
    return Mask(
        type=mask.child_text("Type"),
        description=mask.child_text("Description"),
        help=mask.child_text("Help"),
        initialization=mask.child_text("Initialization"),
        parameters=parameters,
    )


def _object_mask(obj: Node) -> Mask:
    """``Simulink.Mask`` object (SLX before R2017b, classic MDL)."""
    parameters = []
    for array in obj.findall("Array"):
        if array.param("PropName") != "Parameters":
            continue
        for p in array.findall("Object"):
            options = next(
                (
                    a.cells()
                    for a in p.findall("Array")
                    if a.param("PropName") == "TypeOptions"
                ),
                [],
            )
            parameters.append(
                MaskParameter(
                    p.param("Name"),
                    p.param("Prompt"),
                    p.param("Type"),
                    p.param("Value"),
                    tuple(options),
                    p.param("Visible") != "off",
                )
            )
    return Mask(
        type=obj.param("Type"),
        description=obj.param("Description"),
        help=obj.param("Help"),
        initialization=obj.param("Initialization"),
        parameters=tuple(parameters),
    )


def _old_mask(block: Node) -> Mask:
    """Mask block parameters of old classic MDL files: ``MaskType``,
    ``MaskPromptString`` (``|``-separated), ``MaskStyleString``,
    ``MaskVariables`` (``name=@1;``), ``MaskValueString`` and
    ``MaskVisibilityString`` (``on,off``).
    """
    names = [
        v.split("=", 1)[0] for v in block.param("MaskVariables").split(";") if v.strip()
    ]
    prompts = block.param("MaskPromptString").split("|")
    styles = re.findall(r"\w+(?:\([^)]*\))?", block.param("MaskStyleString"))
    values = block.param("MaskValueString").split("|")
    visibilities = block.param("MaskVisibilityString").split(",")
    parameters = []
    for i, name in enumerate(names):
        style = styles[i] if i < len(styles) else "edit"
        kind, _, rest = style.partition("(")
        parameters.append(
            MaskParameter(
                name=name,
                prompt=prompts[i] if i < len(prompts) else "",
                type=kind,
                value=values[i] if i < len(values) else "",
                options=tuple(rest.rstrip(")").split("|")) if rest else (),
                visible=i >= len(visibilities) or visibilities[i].strip() != "off",
            )
        )
    return Mask(
        type=block.param("MaskType"),
        description=block.param("MaskDescription"),
        help=block.param("MaskHelp"),
        initialization=block.param("MaskInitialization"),
        parameters=tuple(parameters),
    )
