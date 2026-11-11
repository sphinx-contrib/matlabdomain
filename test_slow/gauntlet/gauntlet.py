"""Real-project gauntlet: scmd apidoc and sphinx-build on each checkout.

Usage, from anywhere (--fetch runs fetch.py first; without it, nothing is
cloned and a missing checkout is a problem):
  python test_slow/gauntlet/gauntlet.py [NAME ...] [--fetch] [--out DIR]
      [--trials N] [--jobs] [--variant {all,api,conf}] [--projects FILE]

For each enabled project in the list (NAME arguments keep the projects whose
name contains one of them), on its checkout test_slow/repos/<name>:
- generates N times (default 3) into fresh folders, each with a conf.py
  (the checkout as the root, the folder as the output): exit code, wall
  time and the CLI summary; CLI warnings by subtype
  (OUT/<name>/cli_stderr.txt);
- reruns into the first folder with -f (expect 0 created or updated);
- builds that output with sphinx-build -E (no -W), once per variant:
  ``conf`` (the defaults), ``all`` (``-D matlab_auto_link=all``) and ``api``
  (``-b matlab-api-check`` with the default rules; its reports are kept as
  OUT/<name>/api-check.{txt,json}); exit code, wall time, warnings by
  subtype (OUT/<name>/<variant>.warnings.txt), a traceback or crash log in
  stderr; for ``api`` also the report's summary;
- with --jobs, builds each variant again with -j auto and compares exit
  codes, the bytes of every *.html and objects.inv (the api-check reports),
  and the warnings (Windows has no fork, so -j runs serially there).

With --quickstart, instead: runs scmd quickstart -q on a temporary
git worktree of each checkout (the Sphinx source folder ``docs``, or
``sphinx-docs`` when ``docs`` exists), then a sphinx-build -E -n of what it
wrote; the worktree is removed and the checkout stays as it was. Records
the exit codes, wall times, the command's summary (files, API pages,
indexed files, warnings) and the build's warnings by subtype
(OUT/<name>/quickstart.warnings.txt, quickstart.stdout.txt).

Writes OUT/results.json (the summary: the environment and, per project, the
commit and the numbers above) and OUT/manifest.json (SHA-256 of every
generated file per project). Prints the problems: a checkout not at its
pinned or locked commit, a nonzero exit code (for ``api``: other than 1
with findings of severity error, 0 without), a traceback, a duplicate
object, a rerun that changes pages, and a serial vs -j difference (unless
``parallel_may_differ``). Exit 1 when there is one.
"""

import argparse
import collections
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import time
from importlib import metadata
from pathlib import Path

import projects as P

REPO = P.HERE.parents[1]
PY = sys.executable
SUBTYPE = re.compile(r"\[([\w.-]+)\]\s*$")
RECORD = re.compile(r"(^|: )(WARNING|ERROR|CRITICAL|SEVERE): ")
SUMMARY = re.compile(
    r"(\d+) pages?: (\d+) created, (\d+) updated, (\d+) unchanged.*?"
    r"(\d+) files? indexed, (\d+) warnings?, ([\d.]+) s\."
)
QUICKSTART_SUMMARY = re.compile(
    r"(\d+) files? in (\S+), (\d+) API pages?; (\d+) files? indexed, "
    r"(\d+) warnings?, ([\d.]+) s\."
)
# variant -> (builder, extra sphinx-build arguments)
VARIANTS = {
    "conf": ("html", []),
    "all": ("html", ["-D", "matlab_auto_link=all"]),
    "api": ("matlab-api-check", []),
}
API_REPORTS = ("api-check.json", "api-check.txt")
CONF = (
    'extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]\n'
    "matlab_src_code_project_root = {root!r}\n"
    'matlab_apidoc_output_dir = "."\n'
    'exclude_patterns = ["_build"]\n'
)
ENV = dict(os.environ)
if sysconfig.get_config_var("Py_GIL_DISABLED"):
    # tree-sitter would re-enable the GIL with a warning on every run
    ENV["PYTHON_GIL"] = "1"


def records(text):
    """Split warning output into records (a docutils message spans lines)."""
    out = []
    for line in text.splitlines():
        if RECORD.search(line) or not out:
            out.append(line)
        else:
            out[-1] += "\n" + line
    return out


def subtypes(text):
    counts = collections.Counter()
    for record in records(text):
        m = SUBTYPE.search(record)
        counts[m.group(1) if m else "(none)"] += 1
    return dict(sorted(counts.items()))


def run(*args):
    start = time.perf_counter()
    proc = subprocess.run(
        [PY, "-m", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=ENV,
    )
    return proc, time.perf_counter() - start


def apidoc(docs, *flags):
    proc, wall = run("sphinxcontrib.matlab_cli", "apidoc", *flags, "-c", str(docs))
    m = SUMMARY.search(proc.stdout)
    return proc, wall, m.groups() if m else None


def manifest(folder):
    return {
        p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(folder.rglob("*.rst"))
        if "_build" not in p.parts
    }


def build(docs, outdir, root, variant, extra=()):
    shutil.rmtree(outdir, ignore_errors=True)
    warnfile = outdir.parent / f"{outdir.name}.warnings.txt"
    builder, args = VARIANTS[variant]
    proc, wall = run(
        "sphinx",
        "-E",
        "-b",
        builder,
        "-q",
        "-w",
        str(warnfile),
        *extra,
        *args,
        str(docs),
        str(outdir),
    )
    text = warnfile.read_text(encoding="utf-8") if warnfile.exists() else ""
    files = {
        p.relative_to(outdir).as_posix(): p.read_bytes()
        for p in outdir.rglob("*")
        if p.is_file()
        and (p.suffix == ".html" or p.name == "objects.inv" or p.name in API_REPORTS)
    }
    row = {
        "rc": proc.returncode,
        "wall_s": round(wall, 2),
        "warnings": subtypes(text),
        "warning_records": len(records(text)),
        "duplicate_objects": text.count("duplicate object description"),
        "traceback": "Traceback" in proc.stderr or "Traceback" in text,
        "html_files": sum(f.endswith(".html") for f in files),
    }
    if "api-check.json" in files:
        summary = json.loads(files["api-check.json"])["summary"]
        row["api_check"] = {
            key: summary[key]
            for key in ("checked", "not_checked", "errors", "warnings")
        }
        row["api_check"]["findings"] = {
            rule: n["error"] + n["warning"] for rule, n in summary["findings"].items()
        }
    if proc.returncode or row["traceback"]:
        (outdir.parent / f"{outdir.name}.stderr.txt").write_text(
            proc.stderr, encoding="utf-8"
        )
    norm = collections.Counter(text.replace(str(root), "<ROOT>").splitlines())
    return row, files, norm


def expected_rc(row):
    """0, or 1 for an api-check build with findings of severity error."""
    return 1 if row.get("api_check", {}).get("errors") else 0


def compare_jobs(serial, files, warnings, par, pfiles, pwarnings):
    problems = []
    if par["rc"] != serial["rc"]:
        problems.append(f"exit {serial['rc']} vs {par['rc']}")
    changed = sorted(
        f for f in set(files) | set(pfiles) if files.get(f) != pfiles.get(f)
    )
    if changed:
        problems.append(f"{len(changed)} files differ: {', '.join(changed[:5])}")
    if warnings != pwarnings:
        serial_count, parallel_count = sum(warnings.values()), sum(pwarnings.values())
        problems.append(
            f"warnings differ: serial {serial_count}, parallel {parallel_count}"
        )
    return "; ".join(problems) or "identical"


def environment():
    status = P.git(REPO, "status", "--porcelain", "--untracked-files=no")
    return {
        "date": time.strftime("%Y-%m-%d"),
        "platform": sys.platform,
        "python": sys.version.split()[0],
        **{
            name: metadata.version(name)
            for name in ("sphinx", "tree-sitter", "tree-sitter-matlab")
        },
        "matlabdomain": P.git(REPO, "rev-parse", "--short=12", "HEAD")
        + (" with changes" if status else ""),
    }


def problems(project, row):
    out = [
        f"apidoc: exit {t['rc']}, traceback {t['traceback']}, summary {t['summary']}"
        for t in row["trials"]
        if t["rc"] or t["traceback"] or t["summary"] is None
    ]
    rerun = row["rerun"]["summary"]
    if rerun is None or list(rerun[1:3]) != ["0", "0"]:
        out.append(f"the -f rerun created or updated pages: {rerun}")
    for variant in VARIANTS:
        b = row.get(variant)
        if b and (
            b["rc"] != expected_rc(b) or b["traceback"] or b["duplicate_objects"]
        ):
            out.append(
                f"{variant}: exit {b['rc']}, traceback {b['traceback']}, "
                f"duplicate objects {b['duplicate_objects']}"
            )
        jobs = row.get(f"{variant}_jobs")
        if jobs and jobs["diff"] != "identical" and not project.parallel_may_differ:
            out.append(f"{variant} -j: {jobs['diff']}")
    return out


def run_project(project, lock, args, out):
    """Return the row, the manifest (None without a checkout) and the problems."""
    root = project.source
    row = {"commit": None, "changed_files": None, "root": project.root}
    if not (project.checkout / ".git").exists() or not root.is_dir():
        return row, None, [f"no checkout {root} (run fetch.py)"]
    found = check_commit(project, lock, row)

    (out / project.name).mkdir(parents=True, exist_ok=True)
    row["trials"] = []
    for t in range(args.trials):
        docs = out / project.name / f"trial{t}"
        shutil.rmtree(docs, ignore_errors=True)
        docs.mkdir()
        (docs / "conf.py").write_text(CONF.format(root=str(root)), encoding="utf-8")
        proc, wall, summary = apidoc(docs)
        row["trials"].append(
            {
                "rc": proc.returncode,
                "wall_s": round(wall, 3),
                "summary": summary,
                "traceback": "Traceback" in proc.stderr,
            }
        )
        if t == 0:
            row["cli_warnings"] = subtypes(proc.stderr)
            (out / project.name / "cli_stderr.txt").write_text(
                proc.stderr, encoding="utf-8"
            )
    docs = out / project.name / "trial0"
    proc, wall, summary = apidoc(docs, "-f")
    row["rerun"] = {"rc": proc.returncode, "summary": summary}
    for variant in args.variant or list(VARIANTS):
        base = out / project.name / variant
        serial, files, warnings = build(docs, base, root, variant)
        row[variant] = serial
        for report in API_REPORTS:
            if report in files:
                (out / project.name / report).write_bytes(files[report])
        if args.jobs:
            jobs = out / project.name / f"{variant}-j"
            par, pfiles, pwarnings = build(docs, jobs, root, variant, ["-j", "auto"])
            diff = compare_jobs(serial, files, warnings, par, pfiles, pwarnings)
            row[f"{variant}_jobs"] = {"wall_s": par["wall_s"], "diff": diff}
            shutil.rmtree(jobs, ignore_errors=True)
        shutil.rmtree(base, ignore_errors=True)
    return row, manifest(docs), found + problems(project, row)


def check_commit(project, lock, row):
    """Fill in the commit and the changed files; return the problems."""
    found = []
    row["commit"] = P.git(project.checkout, "rev-parse", "HEAD")
    row["changed_files"] = P.changed_files(project.checkout)
    expected = project.commit or P.locked_commit(project, lock)
    if expected is None:
        found.append("not in the lock file (run fetch.py)")
    elif P.resolve(project.checkout, expected) != row["commit"]:
        found.append(f"at {row['commit'][:12]}, not {expected[:12]} (run fetch.py)")
    if row["changed_files"]:
        changed = row["changed_files"]
        print(f"{project.name}: WARNING: {changed} changed files", flush=True)
    return found


def quickstart(root, name, folder):
    """Run scmd quickstart -q in ``root``; return its row."""
    start = time.perf_counter()
    proc = subprocess.run(
        [
            PY,
            "-m",
            "sphinxcontrib.matlab_cli",
            "quickstart",
            str(root),
            "-q",
            "-o",
            name,
        ],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=ENV,
    )
    wall = time.perf_counter() - start
    (folder / "quickstart.stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (folder / "quickstart.stderr.txt").write_text(proc.stderr, encoding="utf-8")
    m = QUICKSTART_SUMMARY.search(proc.stdout)
    return {
        "rc": proc.returncode,
        "wall_s": round(wall, 2),
        "docs": name,
        "summary": m.groups() if m else None,
        "warnings": subtypes(proc.stderr),
        "traceback": "Traceback" in proc.stderr,
    }


def run_quickstart(project, lock, out):
    """Run scmd quickstart -q and a -n build of its output on a
    temporary worktree; return the row, None (no manifest) and the problems.
    """
    row = {"commit": None, "changed_files": None, "root": project.root}
    if not (project.checkout / ".git").exists() or not project.source.is_dir():
        return row, None, [f"no checkout {project.source} (run fetch.py)"]
    found = check_commit(project, lock, row)
    before = P.git(project.checkout, "status", "--porcelain")
    folder = out / project.name
    folder.mkdir(parents=True, exist_ok=True)
    tree = Path(tempfile.mkdtemp(prefix="qs-"))
    tree.rmdir()
    P.git(project.checkout, "worktree", "add", "--detach", "--quiet", str(tree), "HEAD")
    try:
        root = tree / project.root
        name = next(n for n in ("docs", "sphinx-docs") if not (root / n).exists())
        row["quickstart"] = qs = quickstart(root, name, folder)
        if qs["rc"] == 0:
            base = folder / "quickstart"
            row["quickstart_build"], _, _ = build(
                root / name, base, root, "conf", ["-n"]
            )
            shutil.rmtree(base, ignore_errors=True)
    finally:
        P.git(project.checkout, "worktree", "remove", "--force", str(tree))
    if qs["rc"] or qs["traceback"] or qs["summary"] is None:
        found.append(
            f"quickstart: exit {qs['rc']}, traceback {qs['traceback']}, "
            f"summary {qs['summary']}"
        )
    b = row.get("quickstart_build")
    if b and (b["rc"] or b["traceback"] or b["duplicate_objects"]):
        found.append(
            f"quickstart build: exit {b['rc']}, traceback {b['traceback']}, "
            f"duplicate objects {b['duplicate_objects']}"
        )
    if P.git(project.checkout, "status", "--porcelain") != before:
        found.append("the checkout changed")
    return row, None, found


def print_quickstart_table(rows):
    """Per project: API pages, files indexed, warnings and times."""
    print(
        f"\n{'project':<22} {'pages':>6} {'files':>6} {'qs warn':>8} "
        f"{'qs s':>7} {'build warn':>10} {'build s':>8}"
    )
    for name, row in rows.items():
        qs, b = row.get("quickstart") or {}, row.get("quickstart_build") or {}
        summary = qs.get("summary") or ("?",) * 6
        print(
            f"{name:<22} {summary[2]:>6} {summary[3]:>6} {summary[4]:>8} "
            f"{qs.get('wall_s', '?'):>7} {b.get('warning_records', '?'):>10} "
            f"{b.get('wall_s', '?'):>8}"
        )


def main():
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument(
        "names", nargs="*", help="keep projects whose name contains one"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=P.HERE / "runs" / "latest",
        help="default: %(default)s",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="run fetch.py for these projects first (clones what is missing)",
    )
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument(
        "--jobs", action="store_true", help="compare each build with -j auto"
    )
    parser.add_argument("--variant", action="append", choices=sorted(VARIANTS))
    parser.add_argument(
        "--quickstart",
        action="store_true",
        help="scmd quickstart and a -n build on a temporary worktree",
    )
    parser.add_argument(
        "--projects", default=P.LIST, help="the project list (default: %(default)s)"
    )
    args = parser.parse_args()
    if args.fetch:
        fetch = [sys.executable, str(P.HERE / "fetch.py"), *args.names]
        if subprocess.run([*fetch, "--projects", str(args.projects)]).returncode:
            sys.exit("fetch.py failed; nothing was run")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    lock = P.load_lock(args.projects)
    results = {"environment": environment(), "projects": {}}
    hashes, found = {}, {}
    for project in P.load(args.projects):
        if not project.enabled or (
            args.names and not any(n in project.name for n in args.names)
        ):
            continue
        if args.quickstart:
            row, pages, found[project.name] = run_quickstart(project, lock, out)
        else:
            row, pages, found[project.name] = run_project(project, lock, args, out)
        if pages is not None:
            hashes[project.name] = pages
        results["projects"][project.name] = row
        print(project.name, json.dumps(row), flush=True)
        # written after each project, so an interrupted run keeps what it has
        for file, data in (("results.json", results), ("manifest.json", hashes)):
            (out / file).write_text(
                json.dumps(data, indent=1) + "\n", encoding="utf-8", newline="\n"
            )

    bad = {name: p for name, p in found.items() if p}
    count = sum(map(len, bad.values()))
    if args.quickstart:
        print_quickstart_table(results["projects"])
    print(f"\n{len(found)} projects; {count} problems; results in {out}")
    for name, items in bad.items():
        for item in items:
            print(f"  {name}: {item}")
    platform = {"win32": "windows", "darwin": "macos"}.get(sys.platform, sys.platform)
    baseline = P.HERE / "summaries" / f"{platform}.json"
    if baseline.is_file() and not args.quickstart:
        print(
            f"Compare with the saved baseline:\n  python {P.HERE / 'compare.py'}"
            f" {baseline} {out}"
        )
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
