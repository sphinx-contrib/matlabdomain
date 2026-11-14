"""Physical layouts of Simulink files: sniffing, size limits and part
stores for SLX (an OPC zip) and the OPC text form of ``.mdl``.
"""

from __future__ import annotations

import base64
import binascii
import re
import zipfile
import zlib
from collections.abc import Callable
from pathlib import Path

# Model files may be corrupt or huge (project files are trusted): bound
# everything that is read.
MAX_FILE_BYTES = 1024 * 1024 * 1024
MAX_ENTRIES = 100_000
MAX_PART_BYTES = 256 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
# The parts below metadata/ are a few kilobytes in real files.
MAX_METADATA_PART_BYTES = 16 * 1024 * 1024
HEAD_BYTES = 4096

LFS_POINTER = b"version https://git-lfs.github.com/spec/v1"
OPC_TEXT = b"# MathWorks OPC Text Package"
OPC_PART = "__MWOPC_PART_BEGIN__ "
OPC_END = "__MWOPC_PACKAGE_END__"
_CLASSIC = re.compile(rb"(?:#[^\n]*\n\s*)*(Model|Library|Subsystem)\s*\{")


class SimulinkFileError(Exception):
    """A Simulink file that cannot be read (format, size or content)."""


def read_head(path: Path) -> bytes:
    with open(path, "rb") as f:
        return f.read(HEAD_BYTES)


def sniff(head: bytes) -> str:
    """Return the layout of a file: ``zip``, ``opc``, ``classic`` or
    ``unknown``. A Git LFS pointer is a :class:`SimulinkFileError`.
    """
    if head.startswith(LFS_POINTER):
        raise SimulinkFileError("is a Git LFS pointer, not the model file.")
    if head.startswith(b"PK\x03\x04"):
        return "zip"
    text = head.removeprefix(b"\xef\xbb\xbf").lstrip()
    if text.startswith(OPC_TEXT):
        return "opc"
    if _CLASSIC.match(text):
        return "classic"
    return "unknown"


def check_size(path: Path) -> None:
    if path.stat().st_size > MAX_FILE_BYTES:
        raise SimulinkFileError(f"is larger than {MAX_FILE_BYTES} bytes.")


class Parts:
    """The parts of an OPC package, by name (case-insensitive, no leading
    ``/``).
    """

    def __init__(self, parts: dict[str, bytes]):
        self._parts = {name.lstrip("/").lower(): data for name, data in parts.items()}

    def get(self, name: str) -> bytes | None:
        return self._parts.get(name.lstrip("/").lower())


def zip_parts(path: Path, wanted: Callable[[str], bool]) -> Parts:
    """Read the parts of an SLX file whose lower-case name ``wanted``
    accepts.
    """
    check_size(path)
    # Opened first: a missing file stays an OSError for the caller.
    with open(path, "rb") as f:
        try:
            return _zip_parts(f, wanted)
        except (
            zipfile.BadZipFile,
            NotImplementedError,
            RuntimeError,
            EOFError,
            OSError,
            zlib.error,
        ) as err:
            raise SimulinkFileError(f"is not a readable zip file ({err}).") from err


def _zip_parts(f, wanted: Callable[[str], bool]) -> Parts:
    with zipfile.ZipFile(f) as z:
        infos = z.infolist()
        if len(infos) > MAX_ENTRIES:
            raise SimulinkFileError(f"has more than {MAX_ENTRIES} entries.")
        parts: dict[str, bytes] = {}
        total = 0
        for info in infos:
            name = info.filename
            if name.endswith("/") or not wanted(name.lower()):
                continue
            data = _read_entry(z, info)
            total += len(data)
            if total > MAX_TOTAL_BYTES:
                raise SimulinkFileError(
                    f"holds more than {MAX_TOTAL_BYTES} bytes of parts."
                )
            parts[name] = data
    return Parts(parts)


def _check_part_size(name: str, size: int) -> None:
    """Refuse a part larger than its limit: the smaller one below
    ``metadata/``.
    """
    if name.lstrip("/").lower().startswith("metadata/"):
        if size > min(MAX_PART_BYTES, MAX_METADATA_PART_BYTES):
            limit = min(MAX_PART_BYTES, MAX_METADATA_PART_BYTES)
            raise SimulinkFileError(
                f"has a metadata part larger than {limit} bytes: {name}."
            )
    elif size > MAX_PART_BYTES:
        raise SimulinkFileError(
            f"has a part larger than {MAX_PART_BYTES} bytes: {name}."
        )


def _read_entry(z: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes:
    # zipfile stops at the declared size, so checking it bounds the read.
    _check_part_size(info.filename, info.file_size)
    return z.read(info)


def read_members(path: Path, names: tuple[str, ...]) -> list[bytes]:
    """Read the members ``names`` of a zip file within the size limits. Other
    members are not read. A zip or lookup error is raised as it is (for
    ``.mlapp`` files).
    """
    check_size(path)
    with zipfile.ZipFile(path) as z:
        if len(z.infolist()) > MAX_ENTRIES:
            raise SimulinkFileError(f"has more than {MAX_ENTRIES} entries.")
        return [_read_entry(z, z.getinfo(name)) for name in names]


def opc_text_parts(path: Path, wanted: Callable[[str], bool]) -> Parts:
    """Read the parts of an ``.mdl`` file in the OPC text form: each part
    follows a ``__MWOPC_PART_BEGIN__ /name`` line; `` BASE64`` marks
    binary parts.
    """
    check_size(path)
    text = path.read_bytes().decode("utf-8", errors="replace")
    parts: dict[str, bytes] = {}
    name: str | None = None
    is_base64 = False
    lines: list[str] = []
    total = 0
    seen = 0

    def finish() -> None:
        nonlocal total
        if name is None:
            return
        body = "".join(lines)
        if is_base64:
            # MATLAB may write more '=' than base64 needs.
            encoded = "".join(body.split()).rstrip("=")
            encoded += "=" * (-len(encoded) % 4)
            try:
                data = base64.b64decode(encoded, validate=True)
            except binascii.Error as err:
                raise SimulinkFileError(f"has a bad base64 part {name}.") from err
        else:
            data = body.encode("utf-8")
        _check_part_size(name, len(data))
        total += len(data)
        if total > MAX_TOTAL_BYTES or len(parts) >= MAX_ENTRIES:
            raise SimulinkFileError("has too many or too large parts.")
        parts[name] = data

    for line in text.splitlines(keepends=True):
        if line.startswith((OPC_PART, OPC_END)):
            finish()
            name, lines = None, []
            if line.startswith(OPC_PART):
                seen += 1
                spec = line[len(OPC_PART) :].strip()
                is_base64 = spec.endswith(" BASE64")
                part = spec.removesuffix(" BASE64").strip()
                name = part if wanted(part.lstrip("/").lower()) else None
        elif name is not None:
            lines.append(line)
    finish()
    if not seen:
        raise SimulinkFileError("has no parts in its OPC text package.")
    return Parts(parts)
