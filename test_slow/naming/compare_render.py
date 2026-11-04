"""Snapshot and compare rendered HTML anchors/links across code versions.

Usage (run from the matlabdomain repo root):

  # snapshot with whatever ``sphinxcontrib.matlab`` the interpreter imports
  <python> test_slow/naming/compare_render.py snapshot OUT.json
  <python> test_slow/naming/compare_render.py compare A.json B.json
  # A = legacy dotted names, B = path references (Phase 3b): pairs old and
  # new anchors per page, then reports link, inventory, signature, text and
  # warning changes
  <python> test_slow/naming/compare_render.py report A.json B.json

Builds every ``tests/roots/*``, ``tests/test_docs`` and ``docs`` (copied to a
temp dir) with several ``matlab_*`` variants and records, per HTML page, the
element ids, the internal ``href`` targets, an md5 of the page body, the
signature texts, the body text lines, the decoded ``objects.inv`` entries and
the (path-normalized) warnings.
"""

import difflib
import hashlib
import html as html_lib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, cast

REPO = Path(__file__).resolve().parents[2]
VARIANTS = {
    "conf": [],
    "all": ["-D", "matlab_auto_link=all"],
}
ID_RE = re.compile(r'\bid="([^"]*)"')
HREF_RE = re.compile(r'\bhref="([^"#]*#[^"]*)"')
BODY_RE = re.compile(
    r'<div class="body"[^>]*>(.*?)<div class="sphinxsidebar"', re.DOTALL
)
SIG_RE = re.compile(r'<dt class="sig sig-object mat"[^>]*>(.*?)</dt>', re.DOTALL)
HEADERLINK_RE = re.compile(r'<a class="headerlink"[^>]*>.*?</a>', re.DOTALL)
BLOCK_END_RE = re.compile(r"</(p|dt|dd|li|h\d|div|pre|tr)>|<br\s*/?>")
TAG_RE = re.compile(r"<[^>]+>")


def _text(fragment):
    fragment = HEADERLINK_RE.sub("", fragment)
    fragment = BLOCK_END_RE.sub("\n", fragment)
    text = html_lib.unescape(TAG_RE.sub("", fragment))
    lines = (" ".join(line.split()) for line in text.splitlines())
    return [line for line in lines if line]


def projects(tmp):
    out = {}
    for root in sorted((REPO / "tests" / "roots").iterdir()):
        dst = tmp / "roots" / root.name
        shutil.copytree(root, dst, ignore=shutil.ignore_patterns("_build"))
        out[f"roots/{root.name}"] = dst
    tests = tmp / "tests"
    shutil.copytree(
        REPO / "tests",
        tests,
        ignore=shutil.ignore_patterns("_build", "__pycache__", "roots"),
    )
    out["test_docs"] = tests / "test_docs"
    docs = tmp / "docs"
    shutil.copytree(REPO / "docs", docs, ignore=shutil.ignore_patterns("_build"))
    out["docs"] = docs
    return out


def inventory(path):
    from sphinx.util.inventory import InventoryFile

    with open(path, "rb") as f:
        inv = InventoryFile.load(cast(Any, f), "", lambda _base, uri: uri)
    rows = []
    for objtype, items in inv.items():
        if not objtype.startswith("mat:"):
            continue
        for name, item in items.items():
            uri = item[2] if isinstance(item, tuple) else item.uri
            disp = item[3] if isinstance(item, tuple) else item.display_name
            rows.append(f"{objtype} {name} {uri} [{disp}]")
    return sorted(rows)


def snapshot(out_path):
    result = {}
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for name, src in projects(tmp).items():
            for vname, extra in VARIANTS.items():
                outdir = tmp / "out" / name / vname
                warnfile = tmp / "warn.txt"
                cmd = [sys.executable, "-m", "sphinx", "-b", "html", "-E", "-q"]
                cmd += ["-w", str(warnfile), *extra, str(src), str(outdir)]
                proc = subprocess.run(cmd, capture_output=True, text=True)
                warnings = []
                if warnfile.exists():
                    text = warnfile.read_text(encoding="utf-8")
                    text = text.replace(str(tmp), "<TMP>")
                    warnings = sorted(set(text.splitlines()))
                pages = {}
                for html in sorted(outdir.glob("**/*.html")):
                    rel = str(html.relative_to(outdir))
                    if rel in ("genindex.html", "search.html"):
                        continue
                    text = html.read_text(encoding="utf-8")
                    m = BODY_RE.search(text)
                    body = m.group(1) if m else text
                    pages[rel] = {
                        "md5": hashlib.md5(body.encode()).hexdigest(),
                        "ids": ID_RE.findall(body),
                        "hrefs": HREF_RE.findall(body),
                        "sigs": [" ".join(_text(s)) for s in SIG_RE.findall(body)],
                        "text": _text(SIG_RE.sub("", body)),
                    }
                inv = outdir / "objects.inv"
                result[f"{name}|{vname}"] = {
                    "rc": proc.returncode,
                    "warnings": warnings,
                    "pages": pages,
                    "inventory": inventory(inv) if inv.exists() else [],
                }
    Path(out_path).write_text(json.dumps(result, indent=1, sort_keys=True))


def compare(a_path, b_path):
    a = json.loads(Path(a_path).read_text())
    b = json.loads(Path(b_path).read_text())
    same = 0
    for key in sorted(set(a) | set(b)):
        ra, rb = a.get(key), b.get(key)
        if ra is None or rb is None:
            print(f"== {key}: only in {'B' if ra is None else 'A'}")
            continue
        diffs = []
        if ra["rc"] != rb["rc"]:
            diffs.append(f"  rc {ra['rc']} -> {rb['rc']}")
        diffs.extend(
            f"  -warn {w}" for w in sorted(set(ra["warnings"]) - set(rb["warnings"]))
        )
        diffs.extend(
            f"  +warn {w}" for w in sorted(set(rb["warnings"]) - set(ra["warnings"]))
        )
        diffs.extend(
            f"  -inv {i}" for i in sorted(set(ra["inventory"]) - set(rb["inventory"]))
        )
        diffs.extend(
            f"  +inv {i}" for i in sorted(set(rb["inventory"]) - set(ra["inventory"]))
        )
        for page in sorted(set(ra["pages"]) | set(rb["pages"])):
            pa, pb = ra["pages"].get(page), rb["pages"].get(page)
            if pa is None or pb is None:
                diffs.append(f"  page {page} only in {'B' if pa is None else 'A'}")
                continue
            if pa["md5"] == pb["md5"]:
                continue
            for kind in ("ids", "hrefs"):
                ca, cb = Counter(pa[kind]), Counter(pb[kind])
                for v, n in sorted((ca - cb).items()):
                    diffs.append(f"  {page} -{kind[:-1]} {v} (x{n})")
                for v, n in sorted((cb - ca).items()):
                    diffs.append(f"  {page} +{kind[:-1]} {v} (x{n})")
            for kind in ("sigs", "text"):
                if pa.get(kind) != pb.get(kind):
                    lines = difflib.unified_diff(
                        pa.get(kind, []), pb.get(kind, []), n=0, lineterm=""
                    )
                    diffs.extend(
                        f"  {page} {line[0]}{kind.rstrip('s')} {line[1:]}"
                        for line in lines
                        if line[:1] in "+-" and line[:3] not in ("---", "+++")
                    )
            if pa["ids"] == pb["ids"] and pa["hrefs"] == pb["hrefs"]:
                diffs.append(f"  {page} body differs (same ids/hrefs)")
        if diffs:
            print(f"== {key}")
            print("\n".join(diffs))
        else:
            same += 1
    print(f"identical builds: {same}/{len(set(a) | set(b))}")


INV_ROW_RE = re.compile(r"^(\S+) (.*?) (\S*\.html#\S*)(?: \[(.*)\])?$")


def _decode_anchor(anchor):
    body, out, i = anchor[4:], bytearray(), 0
    while i < len(body):
        if body[i] == "~":
            out.append(int(body[i + 1 : i + 3], 16))
            i += 3
        else:
            out.extend(body[i].encode())
            i += 1
    return out.decode()


def _object_ids(build, new):
    """Per page, the ids of documented MATLAB objects in page order."""
    rows = [cast(re.Match[str], INV_ROW_RE.match(row)) for row in build["inventory"]]
    uris = {row[3] for row in rows}
    modules = {f"module-{row[2]}" for row in rows if row[1] == "mat:module"}
    out = {}
    for page, data in build["pages"].items():
        ids = [html_lib.unescape(i) for i in data["ids"]]
        if new:
            out[page] = [i for i in ids if i.startswith("mat-")]
        else:
            out[page] = [i for i in ids if i in modules or f"{page}#{i}" in uris]
    return out


def _anchor_key(anchor):
    # Last name of an old (dotted) or new (mat-) anchor, to align the two;
    # folders (old modules) end with "/".
    if anchor.startswith("mat-"):
        ref = _decode_anchor(anchor)
        last = ref.rstrip("/").rpartition("/")[2]
        if ref.endswith("/"):
            return last.lstrip("+@") + "/"
        file = re.match(r"(.*?)\.(?:m|mlapp)(?:\.(.*))?$", last)
        if file is None:
            return last
        stem, members = file[1], file[2]
        return members.rpartition(".")[2] if members else stem
    if anchor.startswith("module-"):
        return anchor[7:].rpartition(".")[2].lstrip("+@") + "/"
    return anchor.rpartition(".")[2].lstrip("+@")


def _sig_key(sig):
    # Object name of a rendered signature, to align old and new signatures.
    words = sig.split()
    while words and words[0] in ("class", "static", "namespace", "folder"):
        words = words[1:]
    name = words[0].split("(")[0].rstrip("/") if words else ""
    if "/" in name:
        name = name.rpartition("/")[2].partition(".m")[0]
    return name.rpartition(".")[2].lstrip("+@")


def _pair(old, new, key=_anchor_key):
    matcher = difflib.SequenceMatcher(
        None, [key(i) for i in old], [key(i) for i in new], False
    )
    pairs, lost, added = [], [], []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            pairs.extend(zip(old[i1:i2], new[j1:j2], strict=True))
        else:
            lost += old[i1:i2]
            added += new[j1:j2]
    return pairs, lost, added


def report(a_path, b_path):
    """Classify the differences between legacy (A) and path-reference (B) builds.

    Old object anchors are paired with new ones per page by name, then links,
    inventory rows, signatures, text and warnings are compared.
    """
    a = json.loads(Path(a_path).read_text())
    b = json.loads(Path(b_path).read_text())
    uniq = {k: Counter() for k in ("sig", "text", "-warn", "+warn", "issue")}
    for key in sorted(set(a) & set(b)):
        ra, rb = a[key], b[key]
        if rb["rc"] != 0:
            reason = [w for w in rb["warnings"] if "Error" in w] or ["(no warning)"]
            uniq["issue"][f"rc {ra['rc']} -> {rb['rc']}: {reason[0][:120]}"] += 1
            continue
        ids_a, ids_b = _object_ids(ra, False), _object_ids(rb, True)
        refs_b = {
            cast(re.Match[str], INV_ROW_RE.match(row))[2] for row in rb["inventory"]
        }
        mapping = {}
        for page in ra["pages"]:
            pairs, lost, added = _pair(ids_a.get(page, []), ids_b.get(page, []))
            for anchor in lost:
                uniq["issue"][f"{key} {page}: anchor removed {anchor}"] += 1
            for anchor in added:
                uniq["issue"][f"{key} {page}: anchor added {anchor}"] += 1
            mapping.update({f"{page}#{o}": f"{page}#{n}" for o, n in pairs})
            # Old modules were also in the inventory under "page#name".
            mapping.update(
                {
                    f"{page}#{o.removeprefix('module-')}": f"{page}#{n}"
                    for o, n in pairs
                    if o.startswith("module-")
                }
            )
        for page, new in ids_b.items():
            for anchor in new:
                if _decode_anchor(anchor) not in refs_b:
                    uniq["issue"][f"{key} {page}: {anchor} not in inventory"] += 1
        for page in sorted(set(ra["pages"]) & set(rb["pages"])):
            pa, pb = ra["pages"][page], rb["pages"][page]

            def full(href, page=page):
                href = html_lib.unescape(href)
                return f"{page}{href}" if href.startswith("#") else href

            old_links = Counter(mapping.get(full(h), full(h)) for h in pa["hrefs"])
            new_links = Counter(full(h) for h in pb["hrefs"])
            for href, n in (old_links - new_links).items():
                uniq["issue"][f"{key} {page}: link lost {href} (x{n})"] += 1
            for href, n in (new_links - old_links).items():
                uniq["issue"][f"{key} {page}: link added {href} (x{n})"] += 1
            sig_pairs, sig_lost, sig_added = _pair(pa["sigs"], pb["sigs"], _sig_key)
            for old, new in sig_pairs:
                if old != new:
                    uniq["sig"][f"{old}  ->  {new}"] += 1
            for sig in sig_lost:
                uniq["sig"][f"- {sig}"] += 1
            for sig in sig_added:
                uniq["sig"][f"+ {sig}"] += 1
            for line in difflib.unified_diff(pa["text"], pb["text"], n=0, lineterm=""):
                if line[:1] in "+-" and line[:3] not in ("---", "+++"):
                    uniq["text"][f"{line[0]} {line[1:]}"] += 1
        inv_a = {
            cast(re.Match[str], INV_ROW_RE.match(row))[3]: row
            for row in ra["inventory"]
        }
        inv_b = {
            cast(re.Match[str], INV_ROW_RE.match(row))[3]: row
            for row in rb["inventory"]
        }
        for uri, row in inv_a.items():
            if mapping.get(uri, uri) not in inv_b:
                uniq["issue"][f"{key}: inventory row lost: {row}"] += 1
        for w in set(ra["warnings"]) - set(rb["warnings"]):
            uniq["-warn"][w] += 1
        for w in set(rb["warnings"]) - set(ra["warnings"]):
            uniq["+warn"][w] += 1
    for kind, counter in uniq.items():
        print(f"### {kind} ({len(counter)} unique)")
        for item, n in sorted(counter.items()):
            print(f"  [{n}] {item}")


if __name__ == "__main__":
    if sys.argv[1] == "snapshot":
        snapshot(sys.argv[2])
    elif sys.argv[1] == "report":
        report(sys.argv[2], sys.argv[3])
    else:
        compare(sys.argv[2], sys.argv[3])
