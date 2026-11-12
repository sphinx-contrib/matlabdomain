"""Survey how the Simulink fixtures are stored, release by release.

    python test_slow/simulink/survey.py [FIXTURES] [--out survey.json]

FIXTURES defaults to ``tests/simulink/fixtures`` (``<release>/<slx|mdl>/``,
as ``tests/simulink/make_fixtures.m`` writes them). For each file it records
the layout, the part names and where each probe text is stored, and prints,
per diagram and variant, what changes from one release to the next. Use it
when a new release is added: the changes are the rows of the formats page
(``docs/developer-guide/simulink-file-formats.rst``).
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import zipfile
from pathlib import Path

FIXTURES = Path(__file__).parents[2] / "tests" / "simulink" / "fixtures"
#: probe texts of make_fixtures.m
NEEDLES = {
    "desc_model": "Model description line 1",
    "desc_lib": "Library description",
    "desc_sub": "Subsystem file description",
    "desc_ref": "Referenced model description",
    "mask_desc": "Top masked block description.",
    "mask_help": "Top masked help.",
    "inner_mask": "Inner masked description.",
    "deep_mask": "Deep masked description.",
    "model_mask": "Model mask description",
    "sub_mask": "Subsystem file mask description",
    "unicode": "Größe",
}
_SEARCHES = {
    "mask_forms": [
        ("element", rb"<Mask[ >]"),
        ("object", rb'ClassName="Simulink\.Mask"|\$ClassName\s+"Simulink\.Mask"'),
        ("parameters", rb'(?m)^\s*MaskPromptString\s|<P Name="MaskPromptString">'),
    ],
    "references": [
        ("subsystem", rb'ReferencedSubsystem["\s]'),
        ("model", rb'ModelNameDialog["\s]'),
        ("link", rb'SourceBlock["\s]'),
    ],
}


def opc_parts(text: str) -> dict[str, bytes]:
    parts, name, lines, b64 = {}, None, [], False
    for line in text.splitlines(keepends=True):
        if line.startswith(("__MWOPC_PART_BEGIN__ ", "__MWOPC_PACKAGE_END__")):
            if name is not None:
                body = "".join(lines)
                if b64:
                    encoded = "".join(body.split()).rstrip("=")
                    parts[name] = base64.b64decode(encoded + "=" * (-len(encoded) % 4))
                else:
                    parts[name] = body.encode("utf-8")
            name, lines = None, []
            if line.startswith("__MWOPC_PART_BEGIN__ "):
                spec = line.split(" ", 1)[1].strip()
                b64 = spec.endswith(" BASE64")
                name = spec.removesuffix(" BASE64").lstrip("/")
        elif name is not None:
            lines.append(line)
    return parts


def normalized(name: str) -> str:
    name = re.sub(r"system_[\d_]+\.xml", "system_N.xml", name)
    return re.sub(r"_\d[\d_]*(\.\w+)$", r"_N\1", name)


def survey_file(path: Path) -> dict:
    data = path.read_bytes()
    if data[:2] == b"PK":
        with zipfile.ZipFile(path) as z:
            parts = {i.filename: z.read(i) for i in z.infolist()}
        layout = "zip"
    elif data.lstrip().startswith(b"# MathWorks OPC Text Package"):
        parts, layout = opc_parts(data.decode("utf-8", "replace")), "opc-text"
    else:
        parts, layout = {"<file>": data}, "classic"
    found = {
        key: sorted(
            {
                label
                for label, rx in searches
                for b in parts.values()
                if re.search(rx, b)
            }
        )
        for key, searches in _SEARCHES.items()
    }
    needles = {
        key: sorted({normalized(n) for n, b in parts.items() if text.encode() in b})
        for key, text in NEEDLES.items()
    }
    return {
        "layout": layout,
        "parts": sorted({normalized(n) for n in parts}),
        **found,
        "needles": {k: v for k, v in needles.items() if v},
    }


def release_key(release: str) -> tuple[int, str, str]:
    return int(release[1:5]), release[5], release[6:]


def survey(root: Path) -> list[dict]:
    rows = []
    for path in sorted(root.glob("*/*/*")):
        if path.suffix in (".slx", ".mdl"):
            release, variant = path.parts[-3], path.parts[-2]
            rows.append(
                {"release": release, "variant": variant, "diagram": path.stem}
                | survey_file(path)
            )
    return sorted(
        rows, key=lambda r: (r["diagram"], r["variant"], release_key(r["release"]))
    )


def changes(rows: list[dict]) -> list[str]:
    """Return lines that say what changes from one release to the next."""
    out, previous = [], {}
    for row in rows:
        group = (row["diagram"], row["variant"])
        before = previous.get(group)
        if before is None:
            out.append(f"\n## {group[0]} {group[1]}")
        diff = {}
        for key in sorted(set(row) - {"release", "variant", "diagram"}):
            if key == "parts" and before is not None:
                added = sorted(set(row[key]) - set(before[key]))
                removed = sorted(set(before[key]) - set(row[key]))
                if added or removed:
                    diff[key] = {"+": added, "-": removed}
            elif row[key] != (before or {}).get(key):
                diff[key] = row[key]
        if diff:
            out.append(f"{row['release']}: {json.dumps(diff, ensure_ascii=False)}")
        previous[group] = row
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Survey the Simulink fixtures.")
    parser.add_argument("fixtures", nargs="?", type=Path, default=FIXTURES)
    parser.add_argument("--out", type=Path, help="write the survey as JSON")
    args = parser.parse_args(argv)
    rows = survey(args.fixtures)
    if args.out:
        args.out.write_text(json.dumps(rows, indent=1, ensure_ascii=False), "utf-8")
    print("\n".join(changes(rows)))
    print(f"\n{len(rows)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
