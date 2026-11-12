"""Fuzz the Simulink and App Designer readers with mutated fixtures.

    python test_slow/simulink/fuzz.py [--seed N] [--cases N] [--keep DIR]

Mutates the files of ``tests/simulink/fixtures/`` (``.slx``, ``.mdl``) and
``tests/test_data/Application.mlapp``: bit flips, truncation, rewritten zip
members, an entity declaration, deep nesting and odd encodings in the XML
declaration. Each case calls ``mat_simulink.classify`` and
``read_diagram`` (Simulink files) or ``MatObject.parse_mlappfile`` (``.mlapp``).
The run is deterministic for a ``--seed``.

An escape is any other exception than the documented failure (a
``SimulinkFileError``; for ``.mlapp`` also the errors of the zip and XML
modules, a missing member or an unknown encoding, which ``mat_types._parse``
turns into a ``mat.parse_error``), or a case slower than ``SLOW`` seconds.
The mutated file of each escape is kept in ``--keep`` (default: a folder in
the system's temporary folder). Exit 1 if there is an escape.
"""

from __future__ import annotations

import argparse
import collections
import io
import random
import re
import sys
import tempfile
import time
import warnings
import xml.etree.ElementTree as ET
import zipfile
import zlib
from collections.abc import Callable
from pathlib import Path

from sphinxcontrib.mat_simulink import SimulinkFileError, classify, read_diagram
from sphinxcontrib.mat_types import MatObject

ROOT = Path(__file__).parents[2]
FIXTURES = ROOT / "tests" / "simulink" / "fixtures"
MLAPP = ROOT / "tests" / "test_data" / "Application.mlapp"
SLOW = 10.0
#: the failures of ``parse_mlappfile`` that ``mat_types._parse`` reports
MLAPP_ERRORS = (
    SimulinkFileError,
    zipfile.BadZipFile,
    KeyError,
    ET.ParseError,
    LookupError,
    EOFError,
    zlib.error,
    NotImplementedError,
    RuntimeError,  # an encrypted member
    OSError,
)
ENCODINGS = [
    "bogus",
    "utf-16",
    "UTF-16LE",
    "utf-7",
    "cp037",
    "latin-1",
    "ascii",
    "rot13",
    "zlib",
    "idna",
    "",
    "utf-8\x00",
]
ENTITIES = [
    b'<!DOCTYPE a [<!ENTITY x "y">]>',
    b"<!DOCTYPE a>",
    b'<!ENTITY x "y">',
    b'<!DOCTYPE a [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;&a;">]>',
]


def seeds() -> list[tuple[str, bytes]]:
    """Return the files to mutate, as ``(suffix, content)``."""
    out = [
        (path.suffix, path.read_bytes())
        for path in sorted(FIXTURES.rglob("*"))
        if path.suffix in (".slx", ".mdl")
    ]
    return out


# --- mutations ---------------------------------------------------------------


def bit_flips(rng: random.Random, data: bytes) -> bytes:
    out = bytearray(data)
    for _ in range(rng.randint(1, 8)):
        if out:
            out[rng.randrange(len(out))] ^= 1 << rng.randrange(8)
    return bytes(out)


def truncate(rng: random.Random, data: bytes) -> bytes:
    return data[: rng.randrange(len(data) + 1)]


def entity(rng: random.Random, data: bytes) -> bytes:
    """Insert an entity or DTD declaration at a ``<`` of the text, now and
    then in a UTF-16 document.
    """
    spots = [m.start() for m in re.finditer(rb"<", data)] or [0]
    at = rng.choice(spots)
    declaration = rng.choice(ENTITIES)
    if rng.random() < 0.3:  # the same, in a UTF-16 document
        text = (data[:at] + declaration + data[at:]).decode("utf-8", "replace")
        return text.encode(rng.choice(["utf-16", "utf-16-le", "utf-16-be"]))
    return data[:at] + declaration + data[at:]


def nesting(rng: random.Random, data: bytes) -> bytes:
    """Nest elements (or classic ``Name {`` blocks) deeply."""
    depth = rng.choice([10, 499, 500, 501, 502, 1000, 5000, 100_000])
    if rng.random() < 0.5:
        deep = b"<a>" * depth + b"</a>" * depth
    else:
        deep = b"Block {\n" * depth + b"}\n" * depth
    at = rng.randrange(len(data) + 1)
    return data[:at] + deep + data[at:]


def encoding(rng: random.Random, data: bytes) -> bytes:
    """Put an XML declaration with an odd encoding first or in place."""
    declaration = f'<?xml version="1.0" encoding="{rng.choice(ENCODINGS)}"?>'.encode(
        "utf-8", "replace"
    )
    stripped = re.sub(rb"^\s*<\?xml[^>]*\?>", b"", data)
    return declaration + stripped


TEXT_MUTATIONS: list[Callable[[random.Random, bytes], bytes]] = [
    bit_flips,
    truncate,
    entity,
    nesting,
    encoding,
]


def read_zip(data: bytes) -> list[tuple[str, bytes]] | None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            return [(i.filename, z.read(i)) for i in z.infolist()]
    except Exception:  # a seed already mutated: any zip fault means "not a zip"
        return None


def write_zip(members: list[tuple[str, bytes]], rng: random.Random) -> bytes:
    buf = io.BytesIO()
    method = rng.choice([zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED])
    with zipfile.ZipFile(buf, "w", method) as z:
        for name, content in members:
            z.writestr(name, content)
    return buf.getvalue()


def rewrite_members(rng: random.Random, data: bytes) -> bytes:
    """Rewrite, drop, rename or duplicate zip members, mutating one's text."""
    members = read_zip(data)
    if not members:
        return bit_flips(rng, data)
    i = rng.randrange(len(members))
    name, content = members[i]
    choice = rng.randrange(6)
    if choice == 0:
        members[i] = (name, rng.choice(TEXT_MUTATIONS)(rng, content))
    elif choice == 1:
        del members[i]
    elif choice == 2:
        members[i] = (name, b"")
    elif choice == 3:
        members[i] = (name, rng.randbytes(rng.randrange(64)))
    elif choice == 4:
        members.append((name, rng.choice(TEXT_MUTATIONS)(rng, content)))
    else:
        members[i] = (name.swapcase(), content)
    return write_zip(members, rng)


def mutate(rng: random.Random, data: bytes) -> bytes:
    for _ in range(rng.choice([1, 1, 1, 2, 3])):
        if data[:2] == b"PK" and rng.random() < 0.7:
            data = rewrite_members(rng, data)
        else:
            data = rng.choice(TEXT_MUTATIONS)(rng, data)
    return data


# --- running -----------------------------------------------------------------


def run_case(path: Path) -> str:
    """Read ``path``; return ``ok`` or the name of the documented failure, and
    raise anything else.
    """
    if path.suffix == ".mlapp":
        try:
            MatObject.parse_mlappfile(str(path), "App", "")
        except MLAPP_ERRORS as err:
            return f"{type(err).__module__}.{type(err).__name__}".removeprefix(
                "builtins."
            )
        return "ok"
    try:
        classify(path)
        read_diagram(path)
    except SimulinkFileError:
        return "SimulinkFileError"
    return "ok"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--cases", type=int, default=1000)
    parser.add_argument("--keep", type=Path, help="folder for the escaping files")
    args = parser.parse_args(argv)
    warnings.simplefilter("ignore")  # zipfile: Duplicate name

    rng = random.Random(args.seed)
    pool = seeds()
    mlapp = MLAPP.read_bytes()
    keep = args.keep or Path(tempfile.mkdtemp(prefix=f"fuzz-seed{args.seed}-"))
    results: collections.Counter[tuple[str, str]] = collections.Counter()
    escapes: list[tuple[int, str, str]] = []
    slowest = (0.0, -1)
    start = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        for n in range(args.cases):
            # a fifth of the cases mutate the app: the fixtures are many
            suffix, original = (
                (".mlapp", mlapp) if rng.random() < 0.2 else rng.choice(pool)
            )
            data = mutate(rng, original)
            path = Path(tmp) / f"case{suffix}"
            path.write_bytes(data)
            began = time.perf_counter()
            try:
                outcome = run_case(path)
            except Exception as err:  # the point of the run
                outcome = f"ESCAPE {type(err).__name__}"
                escapes.append((n, suffix, f"{type(err).__name__}: {err}"[:200]))
                keep.mkdir(parents=True, exist_ok=True)
                (keep / f"case{n}{suffix}").write_bytes(data)
            took = time.perf_counter() - began
            slowest = max(slowest, (took, n))
            if took > SLOW and not outcome.startswith("ESCAPE"):
                outcome = "ESCAPE slow"
                escapes.append((n, suffix, f"took {took:.1f} s"))
                keep.mkdir(parents=True, exist_ok=True)
                (keep / f"case{n}{suffix}").write_bytes(data)
            results[(suffix, outcome)] += 1
    elapsed = time.perf_counter() - start

    print(f"seed {args.seed}: {args.cases} cases in {elapsed:.1f} s")
    for (suffix, outcome), count in sorted(results.items()):
        print(f"  {suffix:7} {outcome:28} {count}")
    print(f"  slowest case: {slowest[0]:.2f} s (case {slowest[1]})")
    for n, suffix, message in escapes:
        print(f"ESCAPE case {n} ({suffix}): {message}  -> {keep}/case{n}{suffix}")
    return 1 if escapes else 0


if __name__ == "__main__":
    sys.exit(main())
