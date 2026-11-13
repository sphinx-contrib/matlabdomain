"""Compare two gauntlet runs, or a run and a saved summary.

Usage, from anywhere:
  python test_slow/gauntlet/compare.py A B

A and B are run folders (gauntlet.py --out) or results.json files (such as
summaries/*.json). Per project: the commit, the CLI summary (pages, created,
updated, unchanged, files indexed, warnings), the warnings by subtype of the
CLI and each build, exit codes, the api-check summary, and whether serial
and -j builds matched. When both are run folders, also the generated pages
(manifest.json), the api-check findings (api-check.json) and the warnings
themselves, with paths normalized (project root, generated docs folder,
separators) and the fallback codec's name (Windows ANSI or ISO-8859-1)
replaced; prints a few warnings found on one side only. Exit 1 when a
project differs.
"""

import collections
import json
import re
import sys
from pathlib import Path

RECORD = re.compile(r"(^|: )(WARNING|ERROR|CRITICAL|SEVERE): ")
VARIANTS = ("conf", "all", "api")


def load(arg):
    """Return ``(environment, projects, manifest, folder)`` of a run folder or a
    ``results.json`` file; ``manifest`` and ``folder`` are None for a file.
    """
    path = Path(arg)
    folder = path if path.is_dir() else None
    data = json.loads(
        (folder / "results.json" if folder else path).read_text(encoding="utf-8")
    )
    pages = folder / "manifest.json" if folder else None
    manifest = (
        json.loads(pages.read_text(encoding="utf-8"))
        if pages and pages.exists()
        else None
    )
    return data["environment"], data["projects"], manifest, folder


def records(text):
    """Split a warnings log into records: a line with a level (``WARNING:``, ...) and
    the lines that continue it.
    """
    out = []
    # rstrip: a pre-commit hook may strip line-end spaces from committed results
    for line in (raw.rstrip() for raw in text.splitlines()):
        if RECORD.search(line) or not out:
            out.append(line)
        else:
            out[-1] += "\n" + line
    return out


def normalize(record, name):
    """Return a warning record of project ``name`` with what differs between machines
    replaced: the project root, the generated docs folder, path separators and the
    fallback codec's name.
    """
    root = r"[^\s'\"]*?test_slow[\\/]+(?:gauntlet[\\/]+)?repos[\\/]+" + re.escape(name)
    record = re.sub(root, "<ROOT>", record)
    record = re.sub(
        r"[^\s'\"]*?[\\/]" + re.escape(name) + r"[\\/]+trial0", "<DOCS>", record
    )
    record = re.sub(r"^.*?docstring of ", "docstring of ", record)
    record = re.sub(r"^[^\n]*?<autodoc>", "<autodoc>", record)
    first, _, rest = record.partition("\n")
    m = RECORD.search(first)
    if m:
        first = first[: m.start()].replace("\\", "/") + first[m.start() :]
    record = first + ("\n" + rest if rest else "")
    for codec in ("Windows ANSI", "ISO-8859-1"):
        record = record.replace(f"decoded as {codec}", "decoded as <FALLBACK>")
    return record


def warnings(folder, name, file):
    """Return the normalized records of the warnings log ``file`` of project ``name`` in
    run ``folder``, counted; empty when the log is missing.
    """
    path = folder / name / file
    if not path.exists():
        return collections.Counter()
    text = path.read_text(encoding="utf-8", errors="replace")
    return collections.Counter(normalize(r, name) for r in records(text))


def counts(a, b):
    """Return ``key a vs b`` for each key whose count differs between the counters ``a``
    and ``b``, joined by commas.
    """
    keys = sorted(set(a) | set(b))
    return ", ".join(
        f"{k} {a.get(k, 0)} vs {b.get(k, 0)}" for k in keys if a.get(k) != b.get(k)
    )


def compare(name, ra, rb, a, b):
    """Return the differences of project ``name`` between its results ``ra`` and ``rb``:
    commit, CLI summary and warnings, and per build its exit code, warnings, api-check
    summary and -j match.

    ``a`` and ``b`` are ``(manifest, folder)`` of the runs; when both are run folders,
    the generated pages, api-check findings and warning logs are compared too.
    """
    problems = []
    if ra.get("commit") != rb.get("commit"):
        problems.append(
            f"commit {str(ra.get('commit'))[:12]} vs {str(rb.get('commit'))[:12]}"
        )
    sa, sb = ra["trials"][0]["summary"], rb["trials"][0]["summary"]
    # pages, created, updated, unchanged, files indexed, warnings (not time)
    if (sa or [])[:6] != (sb or [])[:6]:
        problems.append(f"CLI summary {sa} vs {sb}")
    if ra.get("cli_warnings") != rb.get("cli_warnings"):
        problems.append(
            f"CLI warnings: {counts(ra['cli_warnings'], rb['cli_warnings'])}"
        )
    for variant in VARIANTS:
        va, vb = ra.get(variant), rb.get(variant)
        if va is None or vb is None:
            continue
        if va["rc"] != vb["rc"]:
            problems.append(f"{variant} exit {va['rc']} vs {vb['rc']}")
        if va["warnings"] != vb["warnings"]:
            problems.append(
                f"{variant} warnings: {counts(va['warnings'], vb['warnings'])}"
            )
        if va.get("api_check") != vb.get("api_check"):
            problems.append(
                f"{variant} api-check: {va.get('api_check')} vs {vb.get('api_check')}"
            )
        ja, jb = ra.get(f"{variant}_jobs"), rb.get(f"{variant}_jobs")
        if ja and jb and (ja["diff"] == "identical") != (jb["diff"] == "identical"):
            problems.append(f"{variant} -j: {ja['diff']} vs {jb['diff']}")
    if a[0] is not None and b[0] is not None:
        ma, mb = a[0].get(name, {}), b[0].get(name, {})
        changed = sorted(f for f in set(ma) | set(mb) if ma.get(f) != mb.get(f))
        if changed:
            problems.append(
                f"{len(changed)} generated files differ, e.g. {changed[:3]}"
            )
    if a[1] is not None and b[1] is not None:
        fa, fb = (folder / name / "api-check.json" for folder in (a[1], b[1]))
        if fa.exists() and fb.exists():
            ja, jb = (json.loads(f.read_text(encoding="utf-8")) for f in (fa, fb))
            if ja != jb:
                keys = [
                    {json.dumps(x, sort_keys=True) for x in j["findings"]}
                    for j in (ja, jb)
                ]
                problems.append(
                    f"api-check.json: {len(keys[0] - keys[1])} findings only in A, "
                    f"{len(keys[1] - keys[0])} only in B"
                )
        built = [f"{v}.warnings.txt" for v in VARIANTS if v in ra and v in rb]
        for file in ["cli_stderr.txt", *built]:
            wa, wb = warnings(a[1], name, file), warnings(b[1], name, file)
            if wa != wb:
                only_a, only_b = wa - wb, wb - wa
                count_a, count_b = sum(only_a.values()), sum(only_b.values())
                problems.append(f"{file}: {count_a} only in A, {count_b} only in B")
                problems.extend(
                    f"    {side}: {rec.splitlines()[0][:200]}"
                    for side, only in (("A", only_a), ("B", only_b))
                    for rec in list(only)[:3]
                )
    return problems


def main():
    """Compare the two runs given on the command line, print the projects that differ,
    and exit 1 if any does.
    """
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    env_a, res_a, *a = load(sys.argv[1])
    env_b, res_b, *b = load(sys.argv[2])
    print(f"A: {json.dumps(env_a)}\nB: {json.dumps(env_b)}\n")
    names = sorted(set(res_a) | set(res_b), key=str.casefold)
    differ = 0
    for name in names:
        ra, rb = res_a.get(name), res_b.get(name)
        if ra is None or rb is None:
            print(f"{name}: only in {'B' if ra is None else 'A'}")
            differ += 1
            continue
        if not ra.get("trials") or not rb.get("trials"):
            print(f"{name}: not run in {'A' if not ra.get('trials') else 'B'}")
            differ += 1
            continue
        problems = compare(name, ra, rb, a, b)
        differ += bool(problems)
        pages = (ra["trials"][0]["summary"] or ["?"])[0]
        print(f"{name}: {pages} pages; " + ("DIFFERS" if problems else "IDENTICAL"))
        for p in problems:
            print(f"  {p}")
    print(f"\n{differ} of {len(names)} projects differ")
    sys.exit(1 if differ else 0)


if __name__ == "__main__":
    main()
