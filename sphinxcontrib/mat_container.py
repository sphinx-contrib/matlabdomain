"""Read members of a zip container file within limits.

App Designer apps (``.mlapp``) are zip containers with XML members. Project
files are trusted, but a file may be corrupt or huge, so everything that is
read is bounded: the file, the number of its entries, each member that is
read and the nesting of its XML. XML with a DTD or an entity declaration is
refused.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

MAX_FILE_BYTES = 1024 * 1024 * 1024
MAX_ENTRIES = 100_000
# The metadata members that are read are a few kilobytes in real files.
MAX_MEMBER_BYTES = 16 * 1024 * 1024
MAX_DEPTH = 500


class ContainerFileError(Exception):
    """A container file that cannot be read (size or content)."""


@dataclass
class Node:
    """An XML element: its tag without the namespace, its text and children."""

    tag: str
    text: str = ""
    children: list[Node] = field(default_factory=list)

    def child_text(self, tag: str) -> str:
        """Return the text of the first child called ``tag``, or ``""``."""
        return next((child.text for child in self.children if child.tag == tag), "")


def read_members(path: Path, names: tuple[str, ...]) -> list[bytes]:
    """Read the members ``names`` of the zip file ``path`` within the size
    limits. Other members are not read. A zip or lookup error is raised as
    it is.
    """
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ContainerFileError(f"is larger than {MAX_FILE_BYTES} bytes.")
    with zipfile.ZipFile(path) as z:
        if len(z.infolist()) > MAX_ENTRIES:
            raise ContainerFileError(f"has more than {MAX_ENTRIES} entries.")
        members = []
        for name in names:
            info = z.getinfo(name)
            # zipfile stops at the declared size, so checking it bounds the read.
            if info.file_size > MAX_MEMBER_BYTES:
                raise ContainerFileError(
                    f"has a member larger than {MAX_MEMBER_BYTES} bytes: {name}."
                )
            members.append(z.read(info))
        return members


# The parser reads ASCII-compatible encodings and UTF-16 (little or big endian,
# with or without a byte-order mark); the other encodings are invalid XML for it.
# Each UTF-16 form is a plain byte string, so these are six byte searches.
_DTD_MARKERS = tuple(
    marker.encode(encoding)
    for marker in ("<!DOCTYPE", "<!ENTITY")
    for encoding in ("ascii", "utf-16-le", "utf-16-be")
)


def parse_xml(data: bytes, what: str) -> Node:
    """Parse the XML member ``what``; DTDs and entity declarations are refused."""
    if any(marker in data for marker in _DTD_MARKERS):
        raise ContainerFileError(f"has a DTD or entity declaration in {what}.")
    try:
        root = ET.fromstring(data)
    # LookupError: the XML declaration names an unknown or non-text encoding;
    # ValueError: a multi-byte one (utf-7) or one that cannot decode (idna).
    except (ET.ParseError, LookupError, ValueError) as err:
        raise ContainerFileError(f"has invalid XML in {what} ({err}).") from err
    return _from_element(root, 0, what)


def _from_element(element: ET.Element, depth: int, what: str) -> Node:
    if depth > MAX_DEPTH:
        raise ContainerFileError(f"is nested deeper than {MAX_DEPTH} in {what}.")
    node = Node(element.tag.rsplit("}", 1)[-1], element.text or "")
    for child in element:
        node.children.append(_from_element(child, depth + 1, what))
    return node
