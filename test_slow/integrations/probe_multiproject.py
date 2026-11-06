"""Probe: matlabdomain with sphinx-multiproject and a unified search.

Copies ``multiproject/`` to a work folder and runs every step there, so
the checkout stays clean. Steps:

``prepare``
    apidoc and builds of Alpha and Beta (standalone and through
    sphinx-multiproject), the checks listed in ``README.md``, a combined
    single-root build for comparison, then the unified search site
    ``<work>/serve/docs-prefix/`` indexed by Pagefind.
``update``
    Changes Alpha's help text, removes Beta's ``+gizmo`` namespace,
    rebuilds and re-indexes the site.

Run with the Python of the environment under test::

    .venv/Scripts/python test_slow/integrations/probe_multiproject.py prepare
    .venv/Scripts/python test_slow/integrations/probe_multiproject.py update

Then serve ``<work>/serve`` (``python -m http.server -d <work>/serve``) and
open ``/docs-prefix/search/index.html?q=zorblax``. Writes
``<work>/<step>.json`` with every check; exit 1 when one fails.
"""

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, cast

import sphinx
from sphinx.util.inventory import InventoryFile

HERE = Path(__file__).resolve().parent
CHECKOUT = HERE.parents[1]
FIXTURE = HERE / "multiproject"
PAGEFIND = "uvx --from pagefind[bin]==1.6.0 python -m pagefind"
PROJECTS = ("alpha", "beta")


class Probe:
    def __init__(self, work, step):
        self.work = work
        self.step = step
        self.checks = []
        self.notes = {}

    def check(self, name, ok, detail: object = ""):
        self.checks.append({"check": name, "ok": bool(ok), "detail": detail})
        print(
            f"{'ok  ' if ok else 'FAIL'} {name}"
            + (f": {detail}" if detail and not ok else "")
        )

    def run(self, cmd, env=None, cwd=None):
        full_env = {**os.environ, "NO_COLOR": "1", **(env or {})}
        for key, value in (env or {}).items():
            if value is None:
                full_env.pop(key)
        proc = subprocess.run(
            cmd,
            cwd=cwd or self.work,
            env=full_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return proc.returncode, proc.stdout + proc.stderr

    def apidoc(self, confdir):
        return self.run(
            [sys.executable, "-m", "sphinxcontrib.matlab_apidoc", "-c", confdir, "-q"]
        )

    def build(self, srcdir, name, env=None, strict=True, fresh=False):
        """Build ``srcdir`` into ``docs/_build/<name>``; return (code, log, record)."""
        out = self.work / "docs" / "_build" / name
        if fresh and out.exists():
            shutil.rmtree(out)
        record = self.work / f"record-{name}.json"
        record.unlink(missing_ok=True)
        cmd = [sys.executable, "-m", "sphinx", "-b", "html", "-n"]
        cmd += ["-W", "--keep-going"] if strict else []
        cmd += ["-d", str(out / "doctrees"), srcdir, str(out / "html")]
        code, log = self.run(cmd, env={"PROBE_RECORD": str(record), **(env or {})})
        data = (
            json.loads(record.read_text(encoding="utf-8")) if record.exists() else None
        )
        return code, log, data

    def html(self, name, page):
        return (self.work / "docs" / "_build" / name / "html" / page).read_text(
            encoding="utf-8"
        )

    def save(self):
        failed = [c for c in self.checks if not c["ok"]]
        path = self.work / f"{self.step}.json"
        path.write_text(
            json.dumps({"checks": self.checks, "notes": self.notes}, indent=1),
            encoding="utf-8",
        )
        print(
            f"{len(self.checks) - len(failed)}/{len(self.checks)} checks passed; {path}"
        )
        return 1 if failed else 0


def lines(log, *words):
    """Lines of ``log`` that contain one of ``words``."""
    return [line for line in log.splitlines() if any(w in line for w in words)]


def inventory(path):
    with open(path, "rb") as f:
        inv = InventoryFile.load(cast(Any, f), "", lambda _base, uri: uri)
    return {
        f"{kind} {name}": item.uri
        for kind, items in inv.items()
        for name, item in items.items()
    }


def html_tree(root):
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*.html"))
    }


def assemble_and_index(probe, builds):
    """Copy the builds to ``serve/docs-prefix/<project>`` and run Pagefind."""
    site = probe.work / "serve" / "docs-prefix"
    if site.exists():
        shutil.rmtree(site)
    for project, html in builds.items():
        shutil.copytree(
            html, site / project, ignore=shutil.ignore_patterns(".buildinfo")
        )
    shutil.copytree(FIXTURE / "search", site / "search")
    cmd = [
        *shlex.split(os.environ.get("PAGEFIND", PAGEFIND), posix=os.name != "nt"),
        "--site",
        str(site),
    ]
    code, log = probe.run(cmd)
    probe.check("pagefind indexes the assembled site", code == 0, log[-2000:])
    probe.notes["pagefind_log"] = [
        line for line in log.splitlines() if "Indexed" in line or "Found" in line
    ]
    return site


def prepare(probe):
    work = probe.work
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(
        FIXTURE, work, ignore=shutil.ignore_patterns("_build", "api", "__pycache__")
    )

    # apidoc reads one project's conf.py; the multiproject root has no root.
    code, log = probe.apidoc("docs")
    probe.check(
        "apidoc -c docs (multiproject root) stops", code == 2 and "required" in log, log
    )
    for project in PROJECTS:
        code, log = probe.apidoc(f"docs/{project}")
        probe.check(f"apidoc -c docs/{project}", code == 0, log)
    alpha_pages = sorted(p.name for p in (work / "docs/alpha/api").iterdir())
    beta_pages = sorted(p.name for p in (work / "docs/beta/api").iterdir())
    probe.notes["api_pages"] = {"alpha": alpha_pages, "beta": beta_pages}
    probe.check(
        "same page names, own pages",
        "shared.rst" in alpha_pages
        and "gizmo.rst" in beta_pages
        and "gizmo.rst" not in alpha_pages,
    )

    # Standalone builds, Alpha first (Beta reads Alpha's inventory).
    records = {}
    for project in PROJECTS:
        code, log, record = probe.build(f"docs/{project}", project)
        probe.check(f"standalone build {project} (-n -W)", code == 0, log[-3000:])
        records[project] = record
    probe.notes["records"] = records
    for project, record in records.items():
        root = os.path.normcase(str(work / project / "src"))
        probe.check(
            f"{project}: srcdir is its own folder",
            Path(record["srcdir"]) == work / "docs" / project,
        )
        probe.check(
            f"{project}: root relative to srcdir",
            os.path.normcase(record["project_root"]) == root,
        )
        probe.check(
            f"{project}: index stays below its root",
            all(
                os.path.normcase(p).startswith(root + os.sep)
                for p in record["indexed"] + record["sidecars"]
            ),
        )
        probe.check(
            f"{project}: matlabdomain from this checkout",
            Path(record["matlabdomain_file"]).resolve().is_relative_to(CHECKOUT),
            record["matlabdomain_file"],
        )

    a, b = probe.html("alpha", "api/shared.html"), probe.html("beta", "api/shared.html")
    anchor = 'id="mat-+shared/compute.m"'
    probe.check("same anchor on both pages", anchor in a and anchor in b)
    probe.check(
        "Alpha page has Alpha's text only",
        "doubles zorblax" in a
        and "quuxalpha" in a
        and "halves" not in a
        and "quuxbeta" not in a,
    )
    probe.check(
        "Beta page has Beta's text only",
        "halves zorblax" in b
        and "quuxbeta" in b
        and "doubles" not in b
        and "Widget" not in b,
    )
    probe.check(
        "sidecars render per project",
        "alphanotes" in a and "betanotes" not in a and "betanotes" in b,
    )
    for project, label in (("alpha", "ALPHA"), ("beta", "BETA")):
        svg = (work / "docs/_build" / project / "html/_images/diagram.svg").read_text(
            encoding="utf-8"
        )
        probe.check(f"{project}: same-named sidecar image is its own", label in svg)

    beta_index = probe.html("beta", "index.html")
    probe.check(
        "local role resolves locally",
        'href="api/shared.html#mat-+shared/compute.m"' in beta_index,
    )
    probe.check(
        "explicit external+alpha role goes to Alpha",
        'href="../alpha/api/shared.html#mat-+shared/compute.m"' in beta_index,
    )
    probe.check(
        "external class link goes to Alpha",
        'href="../alpha/api/shared.html#mat-+shared/Widget.m"' in beta_index,
    )

    inv_a = inventory(work / "docs/_build/alpha/html/objects.inv")
    inv_b = inventory(work / "docs/_build/beta/html/objects.inv")
    probe.notes["inventories"] = {"alpha": inv_a, "beta": inv_b}
    probe.check(
        "inventories share the reference, each its own URL",
        inv_a.get("mat:function +shared/compute.m")
        == inv_b.get("mat:function +shared/compute.m")
        == "api/shared.html#mat-+shared/compute.m",
    )
    probe.check(
        "inventories hold only their project's objects",
        "mat:class +shared/Widget.m" in inv_a
        and "mat:class +shared/Widget.m" not in inv_b
        and "mat:class +gizmo/Gadget.m" in inv_b
        and "mat:class +gizmo/Gadget.m" not in inv_a,
    )

    # sphinx-multiproject, default mode: reads <project>/conf.py itself.
    code, log, record = probe.build(
        "docs",
        "mp-file-alpha",
        env={"PROJECT": "alpha", "PROBE_MULTIPROJECT_MODE": "file"},
        strict=False,
    )
    probe.notes["multiproject_file_mode"] = lines(log, "has no attribute", "WARNING")
    if sphinx.version_info >= (9,):
        probe.check(
            "multiproject default mode fails on Sphinx 9",
            code != 0 and "has no attribute 'parent'" in log,
            log[-1500:],
        )
    else:
        # The project's conf.py also sets extensions (to build on its own),
        # which sphinx-multiproject warns about.
        probe.check(
            "multiproject default mode builds on Sphinx 8",
            code == 0 and record and record["indexed"] == records["alpha"]["indexed"],
            log[-1500:],
        )

    # sphinx-multiproject, values through the ``config`` option.
    for project in PROJECTS:
        code, log, record = probe.build(
            "docs", f"mp-{project}", env={"PROJECT": project}
        )
        probe.check(f"multiproject build {project} (-n -W)", code == 0, log[-3000:])
        if record:
            probe.notes[f"multiproject_record_{project}"] = {
                k: record[k] for k in ("srcdir", "confdir", "project_root")
            }
            probe.check(
                f"multiproject {project}: srcdir moved, confdir shared",
                Path(record["srcdir"]) == work / "docs" / project
                and Path(record["confdir"]) == work / "docs",
            )
            probe.check(
                f"multiproject {project}: same index as standalone",
                record["indexed"] == records[project]["indexed"],
            )
        same = html_tree(work / "docs/_build" / f"mp-{project}" / "html") == html_tree(
            work / "docs/_build" / project / "html"
        )
        probe.check(f"multiproject {project}: HTML identical to standalone", same)

    # One output folder for both projects (the Makefile pitfall).
    for project in PROJECTS:
        code, log, _ = probe.build("docs", "mp-shared", env={"PROJECT": project})
        probe.notes[f"shared_outdir_{project}"] = lines(log, "environment", "changed")[
            :5
        ]
    probe.check(
        "shared output folder keeps Alpha-only page after Beta",
        (work / "docs/_build/mp-shared/html/tutorial.html").exists(),
    )

    # Unknown matlab_* names.
    conf = work / "docs/alpha/conf.py"
    original = conf.read_text(encoding="utf-8")
    conf.write_text(
        original + '\nmatlab_src_code_projct_root = "x"\n', encoding="utf-8"
    )
    code, log = probe.apidoc("docs/alpha")
    probe.check(
        "typo: apidoc stops", code == 2 and "matlab_src_code_projct_root" in log, log
    )
    code, log, _ = probe.build("docs/alpha", "typo-standalone")
    probe.check(
        "typo: standalone build stops",
        code != 0 and "matlab_src_code_projct_root" in log,
        log[-800:],
    )
    code, log, _ = probe.build("docs", "typo-mp", env={"PROJECT": "alpha"})
    probe.notes["typo_multiproject"] = {
        "exit": code,
        "mentions_name": "matlab_src_code_projct_root" in log,
    }
    probe.check(
        "typo: multiproject build stops",
        code != 0 and "matlab_src_code_projct_root" in log,
        log[-800:],
    )
    conf.write_text(original, encoding="utf-8")

    # Comparison: one build whose root holds both projects.
    code, log = probe.apidoc("docs/combined")
    probe.notes["combined_apidoc"] = log.strip().splitlines()
    code, log, record = probe.build("docs/combined", "combined", strict=False)
    probe.check("combined build runs", code == 0, log[-2000:])
    probe.notes["combined_warnings"] = lines(log, "WARNING")

    site = assemble_and_index(
        probe, {p: work / "docs/_build" / p / "html" for p in PROJECTS}
    )
    probe.notes["site"] = str(site)


def update(probe):
    work = probe.work
    compute = work / "alpha/src/+shared/compute.m"
    compute.write_text(
        compute.read_text(encoding="utf-8").replace(
            "doubles zorblax", "doubles frobnitz"
        ),
        encoding="utf-8",
    )
    shutil.rmtree(work / "beta/src/+gizmo")
    for project in PROJECTS:
        code, log = probe.apidoc(f"docs/{project}")
        probe.check(f"apidoc -c docs/{project} after the change", code == 0, log)
        probe.notes[f"apidoc_{project}"] = log.strip().splitlines()
    probe.check(
        "apidoc removed Beta's gizmo page",
        not (work / "docs/beta/api/gizmo.rst").exists(),
    )

    beta_before = {
        p: p.stat().st_mtime_ns
        for p in (work / "docs/_build/beta/html").rglob("*.html")
    }
    code, log, _ = probe.build("docs/alpha", "alpha")
    probe.check("incremental Alpha rebuild", code == 0, log[-2000:])
    probe.notes["alpha_incremental"] = lines(log, "reading", "out of date", "changed")
    probe.check(
        "Alpha rebuild leaves Beta's output alone",
        all(p.stat().st_mtime_ns == t for p, t in beta_before.items()),
    )
    code, log, _ = probe.build("docs/beta", "beta")
    probe.check("incremental Beta rebuild", code == 0, log[-2000:])
    stale = work / "docs/_build/beta/html/api/gizmo.html"
    probe.notes["stale_after_incremental"] = stale.exists()
    probe.check(
        "incremental build leaves the removed page's HTML (indexing it would be stale)",
        stale.exists(),
    )

    for project in PROJECTS:
        code, log, _ = probe.build(f"docs/{project}", f"{project}-clean", fresh=True)
        probe.check(f"clean {project} build", code == 0, log[-2000:])
    probe.check(
        "clean build has no stale page",
        not (work / "docs/_build/beta-clean/html/api/gizmo.html").exists(),
    )
    site = assemble_and_index(
        probe, {p: work / "docs/_build" / f"{p}-clean" / "html" for p in PROJECTS}
    )
    probe.check(
        "site has Alpha's new text",
        "doubles frobnitz"
        in (site / "alpha/api/shared.html").read_text(encoding="utf-8"),
    )
    probe.check("site has no gizmo page", not (site / "beta/api/gizmo.html").exists())


def main(argv=None):
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("step", choices=("prepare", "update"))
    parser.add_argument(
        "--work",
        type=Path,
        default=Path(tempfile.gettempdir()) / "matlabdomain-probe-multiproject",
    )
    args = parser.parse_args(argv)
    probe = Probe(args.work.resolve(), args.step)
    (prepare if args.step == "prepare" else update)(probe)
    return probe.save()


if __name__ == "__main__":
    sys.exit(main())
