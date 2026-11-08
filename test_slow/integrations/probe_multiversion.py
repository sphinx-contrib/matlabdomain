"""Probe: matlabdomain with sphinx-multiversion.

Builds a disposable Git repository from ``multiversion/rev1`` (tag
``v1.0``) and ``rev1`` + ``rev2`` (tag ``v2.0`` and branch ``main``), then
runs sphinx-multiversion in these scenarios:

``naive``
    ``scmd apidoc`` once in the working tree, then
    sphinx-multiversion: the pages are not in Git, so no version has them.
``snapshot``
    The supported recipe: in a disposable clone, generate and commit each
    revision's pages, move the ref to that commit, then run
    sphinx-multiversion. Repeated three times (fresh, again into the same
    folder, and with one shared doctree folder).
``absolute``
    The snapshot clone with an absolute ``matlab_src_code_project_root``:
    every version documents the checkout's code.

Run with the Python of the environment under test::

    .venv/Scripts/python test_slow/integrations/probe_multiversion.py

Writes ``<work>/multiversion.json`` with every check (exit 1 when one
fails) and the site ``<work>/serve/mv-prefix/`` for a browser check.
"""

import argparse
import filecmp
import importlib.metadata
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, cast

from sphinx.util.inventory import InventoryFile

HERE = Path(__file__).resolve().parent
CHECKOUT = HERE.parents[1]
FIXTURE = HERE / "multiversion"
VERSIONS = ("main", "v1.0", "v2.0")
STRICT = ["-n", "-W", "--keep-going"]
MATLABDOMAIN = importlib.metadata.version("sphinxcontrib-matlabdomain")


def rmtree(path):
    """Remove ``path``, also the read-only Git objects (Windows)."""

    def writable(func, name, _exc):
        os.chmod(name, stat.S_IWRITE)
        func(name)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=writable)
    else:  # pragma: no cover
        shutil.rmtree(path, onerror=writable)


class Probe:
    def __init__(self, work):
        self.work = work
        self.checks = []
        self.notes = {}

    def check(self, name, ok, detail: object = ""):
        self.checks.append({"check": name, "ok": bool(ok), "detail": detail})
        print(
            f"{'ok  ' if ok else 'FAIL'} {name}"
            + (f": {detail}" if detail and not ok else "")
        )

    def run(self, cmd, cwd, env=None):
        full_env = {**os.environ, "NO_COLOR": "1", **(env or {})}
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env=full_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return proc.returncode, proc.stdout + proc.stderr

    def git(self, repo, *args, date=None):
        env = {"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date} if date else {}
        code, log = self.run(
            ["git", "-c", "core.autocrlf=false", *args], cwd=repo, env=env
        )
        if code:
            raise RuntimeError(f"git {' '.join(args)}: {log}")
        return log.strip()

    def apidoc(self, repo):
        return self.run(
            [
                sys.executable,
                "-m",
                "sphinxcontrib.matlab_cli",
                "apidoc",
                "-c",
                "docs",
                "-q",
            ],
            cwd=repo,
        )

    def multiversion(self, repo, out, records, *args, env=None):
        if records.exists():
            shutil.rmtree(records)
        records.mkdir(parents=True)
        cmd = [sys.executable, "-m", "sphinx_multiversion", "docs", str(out), *args]
        code, log = self.run(
            cmd, cwd=repo, env={"PROBE_RECORD_DIR": str(records), **(env or {})}
        )
        found = {
            p.stem: json.loads(p.read_text(encoding="utf-8"))
            for p in records.glob("*.json")
        }
        return code, log, found

    def save(self):
        failed = [c for c in self.checks if not c["ok"]]
        path = self.work / "multiversion.json"
        path.write_text(
            json.dumps({"checks": self.checks, "notes": self.notes}, indent=1),
            encoding="utf-8",
        )
        print(
            f"{len(self.checks) - len(failed)}/{len(self.checks)} checks passed; {path}"
        )
        return 1 if failed else 0


def make_repo(probe, repo):
    # shutil.copy, not copy2: a copied mtime can hide a same-size change from Git.
    shutil.copytree(FIXTURE / "rev1", repo, copy_function=shutil.copy)
    probe.git(repo, "init", "-q", "-b", "main")
    probe.git(repo, "config", "user.name", "Probe")
    probe.git(repo, "config", "user.email", "probe@example.invalid")
    probe.git(repo, "add", "-A")
    probe.git(repo, "commit", "-q", "-m", "Version one", date="2026-01-01T00:00:00Z")
    probe.git(repo, "tag", "v1.0")
    shutil.copytree(
        FIXTURE / "rev2", repo, dirs_exist_ok=True, copy_function=shutil.copy
    )
    (repo / "DELETED").unlink()
    for name in (FIXTURE / "rev2" / "DELETED").read_text(encoding="utf-8").split():
        (repo / name).unlink()
    probe.git(repo, "add", "-A")
    probe.git(repo, "commit", "-q", "-m", "Version two", date="2026-02-01T00:00:00Z")
    probe.git(repo, "tag", "v2.0")


def snapshot(probe, repo, clone, refs):
    """Commit each ref's generated pages in a disposable clone (the recipe)."""
    probe.git(repo.parent, "clone", "-q", str(repo), str(clone))
    probe.git(clone, "config", "user.name", "Probe")
    probe.git(clone, "config", "user.email", "probe@example.invalid")
    current_conf = (clone / "docs" / "conf.py").read_bytes()
    commits = {}
    for ref in refs:
        probe.git(clone, "checkout", "-q", "--detach", ref)
        source = probe.git(clone, "rev-parse", "HEAD")
        # Generate with the conf.py the builds will use (the checkout's).
        revision_conf = (clone / "docs" / "conf.py").read_bytes()
        (clone / "docs" / "conf.py").write_bytes(current_conf)
        code, log = probe.apidoc(clone)
        (clone / "docs" / "conf.py").write_bytes(revision_conf)
        probe.check(f"snapshot: apidoc at {ref}", code == 0, log)
        probe.git(clone, "add", "-f", "docs/api")
        probe.git(
            clone,
            "commit",
            "-q",
            "-m",
            f"API pages for {ref}",
            date="2026-03-01T00:00:00Z",
        )
        if ref.startswith("v"):
            probe.git(clone, "tag", "-f", ref)
        else:
            probe.git(clone, "branch", "-f", ref)
        commits[ref] = {
            "source": source,
            "snapshot": probe.git(clone, "rev-parse", "HEAD"),
        }
    probe.git(clone, "checkout", "-q", "main")
    return commits


def html(out, version, page):
    return (out / version / page).read_text(encoding="utf-8")


def warnings(log):
    """Return the distinct warning messages of ``log``."""
    found = {
        line.split("WARNING: ", 1)[1]
        for line in log.splitlines()
        if "WARNING: " in line
    }
    return sorted(found)


def environment(log):
    """Return the lines about loading the saved Sphinx environment."""
    return sorted({line.strip() for line in log.splitlines() if "pickled env" in line})


def inventory(path):
    with open(path, "rb") as f:
        inv = InventoryFile.load(cast(Any, f), "", lambda _base, uri: uri)
    return {f"{kind} {name}" for kind, items in inv.items() for name in items}


def same_trees(a, b):
    """Compare two outputs, without the doctrees and build info files."""
    diffs = []

    def walk(cmp, rel=""):
        diffs.extend(
            f"{rel}{n}"
            for n in cmp.left_only + cmp.right_only + cmp.diff_files + cmp.funny_files
        )
        for name, sub in cmp.subdirs.items():
            walk(sub, f"{rel}{name}/")

    walk(filecmp.dircmp(a, b, ignore=[".doctrees", ".buildinfo", ".buildinfo.bak"]))
    return diffs


def check_versions(probe, out, records, label):
    """Check that one sphinx-multiversion output is revision-correct."""
    probe.check(
        f"{label}: every version built",
        sorted(records) == sorted(VERSIONS),
        sorted(records),
    )
    for name, rec in records.items():
        probe.check(
            f"{label}: {name} built by this checkout's matlabdomain",
            Path(rec["matlabdomain_file"]).resolve().is_relative_to(CHECKOUT)
            and rec["python"] == sys.executable,
            rec["matlabdomain_file"],
        )
        probe.check(
            f"{label}: {name} source is its revision's copy",
            Path(rec["srcdir"]).name == "docs" and rec["documented_commit"] != "",
        )
    v1, v2 = records.get("v1.0", {}), records.get("v2.0", {})
    probe.check(
        f"{label}: v1.0 index has v1-only code",
        "+geo/legacyArea.m" in v1.get("references", [])
        and "+geo/perimeter.m" not in v1.get("references", []),
    )
    probe.check(
        f"{label}: v2.0 index has v2-only code",
        "+geo/perimeter.m" in v2.get("references", [])
        and "+geo/legacyArea.m" not in v2.get("references", []),
    )
    probe.check(
        f"{label}: release comes from the revision",
        v1.get("release") == "1.0" and v2.get("release") == "2.0",
    )
    commits = probe.notes.get("commits", {})
    probe.check(
        f"{label}: each version built from its snapshot commit",
        all(
            rec["documented_commit"] == commits[name]["snapshot"]
            for name, rec in records.items()
        ),
    )
    probe.check(
        f"{label}: conf.py comes from the checkout",
        len({r["confdir"] for r in records.values()}) == 1,
    )

    p1, p2 = html(out, "v1.0", "api/geo.html"), html(out, "v2.0", "api/geo.html")
    probe.check(
        f"{label}: v1.0 API page",
        "squarearea" in p1
        and 'id="mat-+geo/legacyArea.m"' in p1
        and "perimeter" not in p1
        and "rectanglearea" not in p1,
    )
    probe.check(
        f"{label}: v2.0 API page",
        "rectanglearea" in p2
        and 'id="mat-+geo/perimeter.m"' in p2
        and "legacy" not in p2.lower()
        and "squarearea" not in p2,
    )
    probe.check(
        f"{label}: sidecar text per version",
        "guidev1" in p1 and "guidev2" not in p1 and "guidev2" in p2,
    )
    for name, mark in (("v1.0", "V1"), ("v2.0", "V2")):
        svg = (out / name / "_images" / "fig.svg").read_text(encoding="utf-8")
        probe.check(f"{label}: {name} sidecar image is its own", f">{mark}<" in svg)
    i1, i2 = inventory(out / "v1.0/objects.inv"), inventory(out / "v2.0/objects.inv")
    probe.check(
        f"{label}: inventories per version",
        "mat:function +geo/legacyArea.m" in i1 - i2
        and "mat:function +geo/perimeter.m" in i2 - i1,
    )
    probe.check(
        f"{label}: v1.0 links its own objects",
        'href="api/geo.html#mat-+geo/legacyArea.m"' in html(out, "v1.0", "index.html"),
    )
    probe.check(
        f"{label}: v2.0 links its own objects",
        'href="api/geo.html#mat-+geo/perimeter.m"' in html(out, "v2.0", "index.html"),
    )
    probe.check(
        f"{label}: v1.0 page links the same page of v2.0",
        'href="../../v2.0/api/geo.html"' in p1,
    )
    legacy = html(out, "v1.0", "legacy.html")
    probe.check(
        f"{label}: page only in v1.0 links v2.0's index",
        'href="../v2.0/index.html"' in legacy and "not in this version" in legacy,
    )
    probe.check(
        f"{label}: footer names the version and matlabdomain",
        f'matlabdomain <span class="matlabdomain">{MATLABDOMAIN}</span>' in p1
        and '<span class="documented">v1.0</span>' in p1,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--work",
        type=Path,
        default=Path(tempfile.gettempdir()) / "matlabdomain-probe-multiversion",
    )
    args = parser.parse_args(argv)
    work = args.work.resolve()
    if work.exists():
        rmtree(work)
    work.mkdir(parents=True)
    probe = Probe(work)
    probe.notes["versions"] = {
        "python": sys.version,
        "sphinx": importlib.metadata.version("sphinx"),
        "sphinx-multiversion": importlib.metadata.version("sphinx-multiversion"),
        "sphinxcontrib-matlabdomain": MATLABDOMAIN,
        "git": probe.run(["git", "--version"], cwd=work)[1].strip(),
    }

    repo = work / "repo"
    make_repo(probe, repo)

    # naive: generated pages are untracked, so git archive leaves them out.
    code, log = probe.apidoc(repo)
    probe.check("naive: apidoc in the working tree", code == 0, log)
    code, log, records = probe.multiversion(
        repo, work / "out-naive", work / "rec-naive"
    )
    probe.check("naive: sphinx-multiversion runs", code == 0, log[-2000:])
    missing = [
        v
        for v in VERSIONS
        if not (work / "out-naive" / v / "api" / "geo.html").exists()
    ]
    probe.check("naive: no version has API pages", missing == list(VERSIONS), missing)
    probe.notes["naive_warnings"] = warnings(log)

    # snapshot: the supported recipe.
    clone = work / "snap"
    probe.notes["commits"] = snapshot(probe, repo, clone, ["v1.0", "v2.0", "main"])
    code, log = probe.run(
        [
            sys.executable,
            "-m",
            "sphinx_multiversion",
            "docs",
            str(work / "meta"),
            "--dump-metadata",
        ],
        cwd=clone,
    )
    meta = json.loads(log[log.index("{") :])
    probe.notes["metadata"] = {
        k: {f: v[f] for f in ("version", "release", "is_released", "docnames")}
        for k, v in meta.items()
    }
    out1 = work / "out-1"
    code, log, records = probe.multiversion(clone, out1, work / "rec-1", *STRICT)
    probe.check("snapshot: sphinx-multiversion -n -W", code == 0, log[-3000:])
    probe.notes["records"] = records
    check_versions(probe, out1, records, "snapshot")

    out2 = work / "out-2"
    code, log, _ = probe.multiversion(clone, out2, work / "rec-2", *STRICT)
    probe.check("repeat: second clean run", code == 0, log[-2000:])
    probe.check(
        "repeat: identical output", not same_trees(out1, out2), same_trees(out1, out2)
    )
    code, log, _ = probe.multiversion(clone, out1, work / "rec-3", *STRICT)
    probe.check("repeat: run into the same folder", code == 0, log[-2000:])
    probe.notes["rerun_environment"] = environment(log)
    probe.notes["rerun_buildinfo_bak"] = sorted(
        p.relative_to(out1).as_posix() for p in out1.rglob(".buildinfo.bak")
    )
    probe.check(
        "repeat: same folder gives the same output",
        not same_trees(out1, out2),
        same_trees(out1, out2),
    )

    # One token: sphinx-multiversion would take a separate value as a file name.
    out4 = work / "out-shared-doctrees"
    code, log, records4 = probe.multiversion(
        clone, out4, work / "rec-4", *STRICT, f"--doctree-dir={work / 'doctrees'}"
    )
    probe.check("shared -d: runs", code == 0, log[-2000:])
    probe.notes["shared_doctrees_environment"] = environment(log)
    check_versions(probe, out4, records4, "shared -d")

    # absolute project root: every version documents the checkout.
    code, log, records = probe.multiversion(
        clone, work / "out-abs", work / "rec-abs", env={"PROBE_ABSOLUTE_ROOT": "1"}
    )
    probe.check("absolute root: runs", code == 0, log[-2000:])
    leak = records.get("v1.0", {}).get("references", [])
    probe.notes["absolute_root_v1_references"] = leak
    probe.check(
        "absolute root: v1.0 indexes the checkout's code (leak)",
        "+geo/perimeter.m" in leak and "+geo/legacyArea.m" not in leak,
    )
    probe.notes["absolute_root_warnings"] = warnings(log)

    site = work / "serve" / "mv-prefix"
    shutil.copytree(
        out1, site, ignore=shutil.ignore_patterns(".doctrees", ".buildinfo")
    )
    probe.notes["site"] = str(site)

    # A revision with a top-level sphinxcontrib/ folder: ``python -m sphinx``
    # runs in the revision's copy, which is first on sys.path.
    decoy = work / "snap-decoy"
    shutil.copytree(clone, decoy)
    (decoy / "sphinxcontrib").mkdir()
    (decoy / "sphinxcontrib" / "matlab.py").write_text(
        'raise ImportError("DECOY sphinxcontrib.matlab")\n', encoding="utf-8"
    )
    probe.git(decoy, "add", "sphinxcontrib")
    probe.git(decoy, "commit", "-q", "-m", "Decoy", date="2026-04-01T00:00:00Z")
    only_main = ["-D", "smv_tag_whitelist=^$"]
    code, log, _ = probe.multiversion(
        decoy, work / "out-decoy", work / "rec-decoy", *only_main
    )
    probe.check(
        "decoy: the revision's sphinxcontrib/ shadows the installed one",
        code != 0 and "DECOY" in log,
        log[-1500:],
    )
    code, log, records = probe.multiversion(
        decoy,
        work / "out-decoy-safe",
        work / "rec-decoy-safe",
        *only_main,
        env={"PYTHONSAFEPATH": "1"},
    )
    probe.check(
        "decoy: PYTHONSAFEPATH=1 keeps the installed matlabdomain",
        code == 0
        and Path(records["main"]["matlabdomain_file"])
        .resolve()
        .is_relative_to(CHECKOUT),
        log[-1500:],
    )
    return probe.save()


if __name__ == "__main__":
    sys.exit(main())
