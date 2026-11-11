"""One tree for XML parts and classic ``.mdl`` sections.

A :class:`Node` has a tag, attributes, parameters and children. XML
``<P Name="X">v</P>`` children and classic ``X  v`` lines are parameters;
classic ``$X`` lines are attributes, like XML attributes. Every other
element or section is a child.
"""

from __future__ import annotations

import codecs
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from ._parts import MAX_PART_BYTES, SimulinkFileError

MAX_DEPTH = 500


@dataclass
class Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    params: dict[str, list[str]] = field(default_factory=dict)
    children: list[Node] = field(default_factory=list)
    text: str = ""

    def param(self, name: str, default: str = "") -> str:
        """Return the attribute or the last parameter called ``name``."""
        if name in self.attrs:
            return self.attrs[name]
        values = self.params.get(name)
        return values[-1] if values else default

    def has(self, name: str) -> bool:
        return name in self.attrs or name in self.params

    def find(self, tag: str) -> Node | None:
        return next((c for c in self.children if c.tag == tag), None)

    def findall(self, tag: str) -> list[Node]:
        return [c for c in self.children if c.tag == tag]

    def child_text(self, tag: str) -> str:
        child = self.find(tag)
        return child.text if child is not None else ""

    def cells(self) -> list[str]:
        """Cell values of an ``Array`` (XML elements or classic lines)."""
        return [c.text for c in self.findall("Cell")] + self.params.get("Cell", [])


# The parser reads ASCII-compatible encodings and UTF-16 (little or big endian,
# with or without a byte-order mark); the other encodings are invalid XML for it.
# Each UTF-16 form is a plain byte string, so these are six byte searches.
_DTD_MARKERS = tuple(
    marker.encode(encoding)
    for marker in ("<!DOCTYPE", "<!ENTITY")
    for encoding in ("ascii", "utf-16-le", "utf-16-be")
)


def parse_xml(data: bytes, what: str) -> Node:
    """Parse an XML part; DTDs and entity declarations are refused."""
    if any(marker in data for marker in _DTD_MARKERS):
        raise SimulinkFileError(f"has a DTD or entity declaration in {what}.")
    try:
        root = ET.fromstring(data)
    # LookupError: the XML declaration names an unknown or non-text encoding;
    # ValueError: a multi-byte one (utf-7) or one that cannot decode (idna).
    except (ET.ParseError, LookupError, ValueError) as err:
        raise SimulinkFileError(f"has invalid XML in {what} ({err}).") from err
    return _from_element(root, 0, what)


def _from_element(element: ET.Element, depth: int, what: str) -> Node:
    if depth > MAX_DEPTH:
        raise SimulinkFileError(f"is nested deeper than {MAX_DEPTH} in {what}.")
    node = Node(_local(element.tag), dict(element.attrib), text=element.text or "")
    for child in element:
        tag = _local(child.tag)
        if tag == "P" and "Name" in child.attrib:
            node.params.setdefault(child.attrib["Name"], []).append(child.text or "")
        else:
            node.children.append(_from_element(child, depth + 1, what))
    return node


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


_SECTION = re.compile(r"([A-Za-z_$][\w$.]*)\s*\{\s*$")
_ITEM = re.compile(r"([A-Za-z_$][\w$.]*)(?:\s+(.*))?$")
_STRING = re.compile(r'"((?:[^"\\]|\\.)*)"')
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}
_ENCODING = re.compile(rb'SavedCharacterEncoding\s+"([^"]+)"')


def decode_mdl(data: bytes) -> str:
    """Decode a classic ``.mdl`` file with its ``SavedCharacterEncoding``."""
    if len(data) > MAX_PART_BYTES * 4:
        raise SimulinkFileError(f"is larger than {MAX_PART_BYTES * 4} bytes.")
    found = _ENCODING.search(data[:65536])
    candidates = [found.group(1).decode("ascii", "replace")] if found else []
    for encoding in [*candidates, "utf-8"]:
        try:
            codecs.lookup(encoding)
            return data.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("cp1252", errors="replace")


def unescape(value: str) -> str:
    return re.sub(r"\\(.)", lambda m: _ESCAPES.get(m.group(1), m.group(0)), value)


def parse_mdl(text: str) -> list[Node]:
    """Parse classic ``.mdl`` text into its top-level sections."""
    top: list[Node] = []
    stack: list[Node] = []
    last: tuple[Node, str] | None = None
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == "}":
            if not stack:
                raise SimulinkFileError(f"has an unmatched '}}' on line {number}.")
            stack.pop()
            last = None
            continue
        if line.startswith('"') and last is not None:
            node, key = last
            node.params[key][-1] += "".join(unescape(s) for s in _STRING.findall(line))
            continue
        section = _SECTION.match(line)
        if section:
            if len(stack) >= MAX_DEPTH:
                raise SimulinkFileError(f"is nested deeper than {MAX_DEPTH}.")
            node = Node(section.group(1))
            (stack[-1].children if stack else top).append(node)
            stack.append(node)
            last = None
            continue
        item = _ITEM.match(line)
        if not item or not stack:
            raise SimulinkFileError(f"has an unreadable line {number}.")
        key, value = item.group(1), (item.group(2) or "").strip()
        node = stack[-1]
        is_string = value.startswith('"')
        if is_string:
            value = "".join(unescape(s) for s in _STRING.findall(value))
        if key.startswith("$"):
            node.attrs[key[1:]] = value
            last = None
        else:
            node.params.setdefault(key, []).append(value)
            last = (node, key) if is_string else None
    if stack:
        raise SimulinkFileError("ends inside an open section.")
    return top
