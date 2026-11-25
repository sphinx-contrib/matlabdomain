"""End-to-end scenarios: the real ``scmd`` and ``sphinx-build`` on real projects.

Usage, from the matlabdomain repo root:
  python test_slow/gauntlet/scenarios.py [NAME ...] [--out DIR] [--coverage] [--list]

The gauntlet (gauntlet.py) builds 14 real projects with the default
configuration. A scenario uses the rest of the interface on the same checkouts
(test_slow/repos/, see README.md) or on the repo's own docs: the other
configuration values, the CLI flags, hand-written pages
with every directive and role, incremental rebuilds after edits, intersphinx
between two projects, other builders, invalid configuration, broken input, and
quickstart answered on stdin. Each scenario states what correct behavior is
(exit codes, warnings, pages, links) and checks it.

A check marked with a bug id (``bug="E2E-3"``; the list:
matlabdomain-ai-files/gauntlet-coverage.md) is a known bug: while it fails it
is reported as known, not as a problem; when it passes, the run says to remove
the mark. Every command is also checked for a traceback (a crash).

A scenario that mutates a project works on a copy in OUT/<scenario>/; the
checkouts stay as they are. Writes OUT/results.json and a log of each
command (OUT/<scenario>/NN-<step>.log). Exit 1 on a failed check, a crash or a
scenario that raised. With --coverage, the children are measured with the test
suite's coverage settings (OUT/coverage, as gauntlet.py --coverage).
"""

import argparse
import html as html_mod
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

import gauntlet as G
import projects as P

from sphinxcontrib.mat_api_check import RULES as API_CHECK_RULES

REPO = G.REPO
REPOS = P.REPOS
DOCS = REPO / "docs"
SCMD = Path(sys.executable).with_name("scmd" + (".exe" if os.name == "nt" else ""))
SCENARIOS = {}
#: the base conf.py of a scenario; values are added with ``conf(..., **values)``
BASE_CONF = {
    "extensions": ["sphinx.ext.autodoc", "sphinxcontrib.matlab"],
    "exclude_patterns": ["_build"],
}


def scenario(func):
    """Register ``func`` as a scenario named after it (``_`` -> ``-``)."""
    SCENARIOS[func.__name__.replace("_", "-")] = func
    return func


class Failed(Exception):
    """A step whose failure makes the rest of the scenario meaningless."""


class Ctx:
    """One scenario's folder, commands and checks."""

    def __init__(self, name, folder):
        self.name = name
        self.dir = folder
        self.checks = []
        self.step = 0
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)

    # --- checks -------------------------------------------------------------
    def expect(self, ok, what, bug=None):
        """Record a check; return ``ok``."""
        status = "ok" if ok else "FAIL"
        if bug:
            status = "known" if not ok else "FIXED?"
        self.checks.append({"status": status, "what": what, "bug": bug})
        mark = {"ok": " ", "FAIL": "!", "known": "~", "FIXED?": "?"}[status]
        print(f"  {mark} {what}" + (f" [{bug}]" if bug else ""), flush=True)
        return ok

    def require(self, ok, what):
        """Record a check the rest depends on; stop the scenario when it fails."""
        if not self.expect(ok, what):
            raise Failed(what)

    # --- files --------------------------------------------------------------
    def path(self, *parts):
        """Return a path below the scenario's folder."""
        return self.dir.joinpath(*parts)

    def write(self, rel, text, encoding="utf-8"):
        """Write ``text`` (dedented) to ``self.dir / rel``; return the path."""
        path = self.dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_dedent(text), encoding=encoding, newline="\n")
        return path

    def copy_project(self, name, dest=None, root=""):
        """Copy the checkout ``name`` (without .git) to ``self.dir / dest``."""
        src = REPOS / name / root
        if not src.is_dir():
            raise Failed(f"no checkout {src} (run fetch.py)")
        dest = self.dir / (dest or name)
        shutil.copytree(src, dest, symlinks=True, ignore=shutil.ignore_patterns(".git"))
        return dest

    def conf(self, folder, **values):
        """Write ``folder/conf.py``: BASE_CONF updated with ``values``; a value
        of the class ``Raw`` is written as is.
        """
        settings = {**BASE_CONF, **values}
        lines = [
            f"{key} = {value if isinstance(value, Raw) else repr(value)}"
            for key, value in settings.items()
        ]
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "conf.py").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return folder

    # --- commands -----------------------------------------------------------
    def run(self, label, argv, cwd=None, stdin=None, crash_ok=False, env=None):
        """Run ``argv`` (after the Python prefix); log it; check for a crash."""
        self.step += 1
        start = time.perf_counter()
        proc = subprocess.run(
            [*argv],
            cwd=cwd or REPO,
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**G.ENV, **(env or {})},
        )
        wall = time.perf_counter() - start
        log = self.dir / f"{self.step:02d}-{_slug(label)}.log"
        log.write_text(
            f"$ {' '.join(map(str, argv))}\n(cwd {cwd or REPO}; exit "
            f"{proc.returncode}; {wall:.1f} s)\n--- stdout\n{proc.stdout}"
            f"--- stderr\n{proc.stderr}",
            encoding="utf-8",
        )
        if not crash_ok:
            self.expect(not crashed(proc.stderr), f"{label}: no traceback ({log.name})")
        return proc

    def scmd(self, label, *args, **kw):
        """Run the installed ``scmd`` console script with ``args``."""
        return self.run(label, [*python(), str(SCMD), *map(str, args)], **kw)

    def sphinx(
        self,
        label,
        src,
        out,
        *args,
        builder="html",
        fresh=True,
        doctrees=None,
        crash_ok=False,
    ):
        """Run sphinx-build; return a Build (exit code, warnings, out folder).

        ``fresh``: -E and an empty output folder; else the output and the
        doctrees (``doctrees`` or <out>.doctrees next to it) are kept.
        """
        out = Path(out)
        doctrees = Path(doctrees) if doctrees else out.with_name(out.name + ".doctrees")
        if fresh:
            shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True, exist_ok=True)
        warnfile = out.parent / f"{out.name}.warnings.txt"
        warnfile.unlink(missing_ok=True)
        argv = [
            *python(),
            "-m",
            "sphinx",
            "-b",
            builder,
            "-d",
            str(doctrees),
            "-w",
            str(warnfile),
            *(["-E"] if fresh else []),
            *map(str, args),
            str(src),
            str(out),
        ]
        proc = self.run(label, argv, crash_ok=crash_ok)
        text = warnfile.read_text(encoding="utf-8") if warnfile.exists() else ""
        return Build(proc, text, out)


EXCEPTION = re.compile(
    r"^\s*([A-Za-z_][\w.]*(?:Error|Exception|Interrupt)): ", re.MULTILINE
)


def crashed(stderr):
    """Whether ``stderr`` shows a crash: a traceback, unless it ends in a
    ``ConfigError`` (Sphinx prints its full report for every ``SphinxError``,
    also a deliberate configuration error).
    """
    if "Traceback" not in stderr and "Exception occurred" not in stderr:
        return False
    errors = EXCEPTION.findall(stderr)
    return not errors or errors[-1] != "sphinx.errors.ConfigError"


class Raw(str):
    """A conf.py value written as Python source."""


class Build:
    """The result of one sphinx-build."""

    def __init__(self, proc, warnings, out):
        self.proc = proc
        self.rc = proc.returncode
        self.warnings = warnings
        self.records = G.records(warnings)
        self.subtypes = G.subtypes(warnings)
        self.out = out
        self.stdout = proc.stdout
        self.stderr = proc.stderr

    def html(self, rel):
        """Return the text of the output file ``rel`` ("" if missing)."""
        path = self.out / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def files(self, suffix=".html"):
        """Return the output files ending in ``suffix`` -> their bytes."""
        return {
            p.relative_to(self.out).as_posix(): p.read_bytes()
            for p in self.out.rglob(f"*{suffix}")
        }

    def warned(self, pattern):
        """Return the warning records that match the regular expression ``pattern``."""
        return [r for r in self.records if re.search(pattern, r)]


def mat_warnings(build):
    """Return the warning records of matlabdomain (``[mat.*]``)."""
    return build.warned(r"\[mat\.")


def ref_warnings(build):
    """Return the warning records of Sphinx's references (``[ref.*]``)."""
    return build.warned(r"\[ref\.")


def python():
    """Return the Python prefix of a child process (with coverage under --coverage)."""
    return G.PY_M[:-1]


def _dedent(text):
    import textwrap

    return textwrap.dedent(text).lstrip("\n")


def _slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")[:50]


def html_text(html):
    """Return the text of an HTML page, tags removed and white space collapsed."""
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


# ---------------------------------------------------------------------------
# Scenarios, each a function of a Ctx.
# ---------------------------------------------------------------------------


@scenario
def docs(ctx):
    """Build the repo's own documentation: strict, serial and -j, other builders."""
    serial = ctx.sphinx("html", DOCS, ctx.path("html"), "-n", "-W", "--keep-going")
    ctx.expect(serial.rc == 0, f"strict build: exit 0 (got {serial.rc})")
    ctx.expect(not serial.records, f"no warnings ({len(serial.records)})")
    par = ctx.sphinx("html -j", DOCS, ctx.path("html-j"), "-n", "-j", "auto")
    ctx.expect(par.rc == 0 and not par.records, "-j build: exit 0, no warnings")
    differ = [
        f
        for f, data in serial.files().items()
        if par.files().get(f) != data and not f.startswith("_")
    ]
    ctx.expect(not differ, f"-j pages equal the serial ones ({differ[:3]})")
    api = ctx.sphinx("api-check", DOCS, ctx.path("api"), builder="matlab-api-check")
    ctx.expect(api.rc in (0, 1), f"api-check: exit 0 or 1 (got {api.rc})")
    report = api.out / "api-check.json"
    ctx.expect(report.exists(), "api-check writes api-check.json")
    for builder in ("dirhtml", "singlehtml", "text", "latex", "epub"):
        b = ctx.sphinx(builder, DOCS, ctx.path(builder), "-n", builder=builder)
        ctx.expect(b.rc == 0, f"-b {builder}: exit 0 (got {b.rc})")
        ctx.expect(
            not mat_warnings(b),
            f"-b {builder}: no matlabdomain warnings ({mat_warnings(b)[:2]})",
        )


def apidoc_project(ctx, name, folder="docs", root="", **values):
    """Write ``ctx.dir/<folder>/conf.py`` documenting the checkout ``name``."""
    return ctx.conf(
        ctx.path(folder),
        matlab_src_code_project_root=str(REPOS / name / root),
        matlab_apidoc_output_dir="api",
        **values,
    )


def rst_pages(folder):
    """Return the generated pages below ``folder`` -> their text."""
    return {
        p.relative_to(folder).as_posix(): p.read_text(encoding="utf-8")
        for p in sorted(folder.rglob("*.rst"))
        if "_build" not in p.parts
    }


SUMMARY = re.compile(r"(\d+) pages?: (\d+) created, (\d+) updated, (\d+) unchanged")


def counts(proc):
    """Return the (pages, created, updated, unchanged) of an apidoc summary, or None."""
    m = SUMMARY.search(proc.stdout)
    return tuple(map(int, m.groups())) if m else None


@scenario
def apidoc_options(ctx):
    """Run scmd apidoc's options and flags on real projects: folder grouping,
    separate pages, private files, page size, depth, toc file, -n, -k, -q, -f,
    switching the grouping back, and a build of each result.
    """
    # Markdown sidecars in folder grouping; a toc file named like a namespace
    sc = apidoc_project(
        ctx,
        "matnwb",
        folder="sidecars",
        extensions=["sphinx.ext.autodoc", "sphinxcontrib.matlab", "myst_parser"],
        matlab_src_sidecar_suffixes=[".md"],
        matlab_apidoc_group="folder",
    )
    ctx.write("sidecars/index.rst", "S\n=\n\n.. toctree::\n\n   api/index\n")
    g = ctx.scmd("sidecars apidoc", "apidoc", "-c", sc)
    ctx.expect(
        g.returncode == 0
        and any("README" in t for t in rst_pages(sc / "api").values()),
        "folder grouping with sidecar docs puts them on the folder pages",
    )
    b = ctx.sphinx("sidecars html", sc, ctx.path("sidecars-html"))
    ctx.expect(
        b.rc == 0 and not b.warned(r"\[mat\.sidecar\]"),
        "... and they render without a mat.sidecar warning",
    )
    io = apidoc_project(ctx, "matnwb", folder="tocio", matlab_apidoc_tocfile="io")
    ctx.write("tocio/index.rst", "T\n=\n\n.. toctree::\n\n   api/io\n")
    g = ctx.scmd("tocfile io", "apidoc", "-c", io)
    pages = rst_pages(io / "api")
    ctx.expect(
        g.returncode == 0
        and "io.rst" in pages
        and sum("namespace io\n" in t for t in pages.values()) == 1,
        "a toc file named like a namespace: both pages are written",
    )
    b = ctx.sphinx("tocfile io html", io, ctx.path("tocio-html"))
    ctx.expect(b.rc == 0 and not b.warned(r"duplicate|nonexisting"), "... and build")
    # an empty project and names that differ only by case
    ctx.write("empty/README.md", "# Nothing\n")
    em = ctx.conf(
        ctx.path("emptydocs"),
        matlab_src_code_project_root=str(ctx.path("empty")),
        matlab_apidoc_output_dir="api",
    )
    g = ctx.scmd("empty", "apidoc", "-c", em)
    ctx.expect(g.returncode == 0, f"an empty project: exit 0 ({g.returncode})")
    for rel in ("Helper.m", "helper.m", "+Pkg/f.m", "+pkg/f.m"):
        ctx.write(f"cases/{rel}", "function f\nend\n")
    for group in ("namespace", "folder"):
        cd = ctx.conf(
            ctx.path(f"cases-{group}"),
            matlab_src_code_project_root=str(ctx.path("cases")),
            matlab_apidoc_output_dir="api",
            matlab_apidoc_group=group,
            matlab_apidoc_separate=True,
        )
        g = ctx.scmd(f"cases {group}", "apidoc", "-c", cd)
        names = sorted(p.lower() for p in rst_pages(cd / "api"))
        ctx.expect(
            g.returncode == 0 and len(names) == len(set(names)),
            f"{group}: names that differ by case get page names that differ "
            f"in any case ({names})",
        )

    for name in ("matnwb", "vhlab-toolbox-matlab"):
        docs = apidoc_project(
            ctx,
            name,
            folder=name,
            matlab_apidoc_group="folder",
            matlab_apidoc_separate=True,
            matlab_apidoc_private=True,
            matlab_apidoc_page_size=7,
            matlab_apidoc_maxdepth=2,
            matlab_apidoc_tocfile="reference",
        )
        (docs / "index.rst").write_text(
            f"{name}\n{'=' * len(name)}\n\n.. toctree::\n\n   api/reference\n",
            encoding="utf-8",
        )
        dry = ctx.scmd(f"{name} -n", "apidoc", "-c", docs, "-n")
        ctx.expect(dry.returncode == 0, f"{name}: -n exits 0")
        ctx.expect(not (docs / "api").exists(), f"{name}: -n writes nothing")
        stale = ctx.scmd(f"{name} -k before", "apidoc", "-c", docs, "-k")
        ctx.expect(stale.returncode == 1, f"{name}: -k exits 1 before the first run")
        gen = ctx.scmd(f"{name} apidoc", "apidoc", "-c", docs)
        ctx.require(gen.returncode == 0, f"{name}: apidoc exits 0")
        pages = rst_pages(docs / "api")
        n = counts(gen)
        ctx.expect(
            n is not None and n[0] == n[1] == len(pages),
            f"{name}: the summary counts every page as created ({n}, {len(pages)})",
        )
        ctx.expect("reference.rst" in pages, f"{name}: the toc file is reference.rst")
        ctx.expect(
            any("mat:autofolder" in t for t in pages.values()),
            f"{name}: folder grouping writes mat:autofolder",
        )
        ctx.expect(
            any(p.endswith("-2.rst") for p in pages),
            f"{name}: page_size 7 splits a long folder into pages",
        )
        if name == "matnwb":
            ctx.expect(
                any("private" in p for p in pages),
                f"{name}: matlab_apidoc_private documents private folders",
            )
        quiet = ctx.scmd(f"{name} -q", "apidoc", "-c", docs, "-q")
        ctx.expect(
            quiet.returncode == 0 and not quiet.stdout,
            f"{name}: -q prints nothing on stdout",
        )
        check = ctx.scmd(f"{name} -k after", "apidoc", "-c", docs, "-k")
        ctx.expect(check.returncode == 0, f"{name}: -k exits 0 when up to date")
        force = ctx.scmd(f"{name} -f", "apidoc", "-c", docs, "-f")
        n = counts(force)
        ctx.expect(
            n is not None and n[1] == n[2] == 0,
            f"{name}: -f rerun creates and updates nothing ({n})",
        )
        b = ctx.sphinx(f"{name} html", docs, ctx.path(f"{name}-html"), "-n")
        ctx.expect(b.rc == 0, f"{name}: folder-grouped html: exit 0")
        ctx.expect(
            not b.warned(r"duplicate object|toctree contains reference to nonexisting"),
            f"{name}: no duplicate object or broken toctree",
        )
        ctx.expect(
            not b.warned(r"document isn't included in any toctree"),
            f"{name}: every generated page is in a toctree "
            f"({len(b.warned('isn.t included'))})",
        )
        # switch back to namespace grouping: the folder pages go
        text = (docs / "conf.py").read_text(encoding="utf-8")
        (docs / "conf.py").write_text(
            text.replace("'folder'", "'namespace'"), encoding="utf-8"
        )
        ctx.expect(
            ctx.scmd(f"{name} -k switched", "apidoc", "-c", docs, "-k").returncode == 1,
            f"{name}: -k exits 1 after switching the grouping",
        )
        ctx.scmd(f"{name} apidoc namespace", "apidoc", "-c", docs)
        after = rst_pages(docs / "api")
        ctx.expect(
            not any("mat:autofolder" in t for t in after.values()),
            f"{name}: switching to namespace grouping removes the folder pages",
        )
        b = ctx.sphinx(f"{name} html ns", docs, ctx.path(f"{name}-html-ns"), "-n")
        ctx.expect(
            b.rc == 0 and not b.warned(r"duplicate object"),
            f"{name}: namespace-grouped html after the switch: exit 0",
        )


ENV_COUNTS = re.compile(
    r"updating environment: (?:\[[^\]]*\] )?(\d+) added, (\d+) changed, (\d+) removed"
)


def env_counts(build):
    """Return the (added, changed, removed) of sphinx-build's "updating environment"."""
    m = ENV_COUNTS.search(build.stdout)
    return tuple(map(int, m.groups())) if m else None


def same_pages(ctx, what, a, b, suffixes=(".html", ".inv")):
    """Check that two builds wrote the same pages (byte for byte)."""
    fa, fb = {}, {}
    for suffix in suffixes:
        fa |= a.files(suffix)
        fb |= b.files(suffix)
    differ = sorted(f for f in set(fa) | set(fb) if fa.get(f) != fb.get(f))
    ctx.expect(not differ, f"{what} ({len(differ)} differ: {differ[:4]})")
    return differ


def auto_pages(docs):
    """Return the number of pages below ``docs`` with an auto directive."""
    return sum(".. mat:auto" in t for t in rst_pages(docs).values())


@scenario
def incremental(ctx):
    """Edit, add, delete and shadow files of a copy of matnwb between builds
    that keep their environment; rerun apidoc; change the configuration; the
    final incremental pages must equal a clean build's.
    """
    proj = ctx.copy_project("matnwb", "proj")
    docs = ctx.conf(
        ctx.path("docs"),
        matlab_src_code_project_root=str(proj),
        matlab_apidoc_output_dir="api",
    )
    ctx.write(
        "docs/index.rst",
        """
        matnwb
        ======

        .. toctree::

           api/index
        """,
    )
    html = ctx.path("html")

    def build(label, **kw):
        b = ctx.sphinx(label, docs, html, fresh=False, **kw)
        ctx.expect(b.rc == 0, f"{label}: exit 0 (got {b.rc})")
        return b

    ctx.require(ctx.scmd("apidoc", "apidoc", "-c", docs).returncode == 0, "apidoc")
    first = build("first build")
    again = build("nothing changed")
    ctx.expect(
        env_counts(again) == (0, 0, 0),
        f"a rebuild with nothing changed reads nothing ({env_counts(again)})",
    )
    # the index-stage warnings repeat on every build (reference/warnings.rst)
    ctx.expect(
        set(again.records) <= set(first.records)
        and set(again.subtypes) <= {"mat.encoding", "mat.empty_code_file"},
        f"... and repeats only the index-stage warnings ({again.subtypes})",
    )

    # edit the help of a global function: only its page is read again
    f = proj / "nwbRead.m"
    f.write_text(
        f.read_text(encoding="utf-8").replace(
            "% NWBREAD - Read an NWB file.", "% NWBREAD - Read an NWB file. Zebra42."
        ),
        encoding="utf-8",
    )
    edited = build("help edited")
    ctx.expect(
        env_counts(edited) == (0, 1, 0),
        f"editing one help reads one page again ({env_counts(edited)})",
    )
    ctx.expect(
        any(b"Zebra42" in d for d in edited.files().values()),
        "the edited help is in the HTML",
    )
    ctx.expect(
        ctx.scmd("-k help", "apidoc", "-c", docs, "-k").returncode == 0,
        "apidoc -k: editing a help changes no page",
    )

    # add a function: apidoc -k sees it, apidoc adds it, the build documents it
    ctx.write(
        "proj/+io/zebraNew.m",
        """
        function out = zebraNew(in)
        %ZEBRANEW Return the input. Added by the incremental scenario.
        out = in;
        end
        """,
    )
    ctx.expect(
        ctx.scmd("-k added", "apidoc", "-c", docs, "-k").returncode == 1,
        "apidoc -k exits 1 after a function is added",
    )
    n = counts(ctx.scmd("apidoc added", "apidoc", "-c", docs))
    ctx.expect(n is not None and n[2] >= 1, f"apidoc updates the io page ({n})")
    added = build("function added")
    page = added.html("api/io.html")
    ctx.expect("zebraNew" in page, "the added function is on api/io.html")
    # a file added: every page that looked up sources is read again
    # (developer-guide/architecture.rst: env-get-outdated)
    ctx.expect(
        env_counts(added) == (0, auto_pages(docs), 0),
        f"every API page is read again after a file is added ({env_counts(added)})",
    )

    # delete a function that others name in "See also" and code
    (proj / "+io" / "isBool.m").unlink()
    ctx.scmd("apidoc deleted", "apidoc", "-c", docs)
    deleted = build("function deleted")
    page = deleted.html("api/io.html")
    ctx.expect(
        'id="+io/isBool.m"' not in page and "io.isBool" not in page,
        "the deleted function is gone from api/io.html",
    )
    ctx.expect(
        not deleted.warned(r"isBool"),
        f"no warning names it ({deleted.warned('isBool')[:2]})",
    )

    # a MEX file next to a function: MATLAB calls the MEX file, the help stays
    (proj / "+io" / "getMatType.mexa64").write_bytes(b"\x7fELF")
    mex = build("mex added")
    ctx.expect(
        "getMatType" in mex.html("api/io.html"),
        "a function with a MEX file next to it stays documented",
    )

    # a function file turned into a script, and a class removed from a namespace
    s = proj / "+io" / "pathParts.m"
    s.write_text("% PATHPARTS A script now.\ndisp(1)\n", encoding="utf-8")
    ctx.scmd("apidoc script", "apidoc", "-c", docs)
    script = build("function became a script")
    ctx.expect(
        not script.warned(r"pathParts"),
        f"a function that became a script: no warning "
        f"({script.warned('pathParts')[:1]})",
    )

    # a configuration change reads every page again
    conf = docs / "conf.py"
    conf.write_text(
        conf.read_text(encoding="utf-8") + "matlab_auto_link = 'all'\n",
        encoding="utf-8",
    )
    configured = build("config changed")
    n = env_counts(configured)
    # Sphinx starts a fresh environment: every page counts as added
    ctx.expect(
        n is not None and n[0] + n[1] > auto_pages(docs),
        f"a changed matlab_ value reads every page again ({n})",
    )
    # a page of the user's in the output folder (no marker) stays; a dangling
    # symlink there is no problem
    ctx.write("docs/api/mine.rst", "Mine\n====\n\nHand-written.\n")
    (docs / "api" / "dangling.rst").symlink_to(ctx.path("nowhere.rst"))
    g = ctx.scmd("apidoc with a user page", "apidoc", "-c", docs)
    ctx.expect(
        g.returncode == 0 and (docs / "api" / "mine.rst").is_file(),
        "apidoc keeps a page without its marker",
    )
    (docs / "api" / "dangling.rst").unlink()
    (docs / "api" / "mine.rst").unlink()
    # rename a file by case only, and delete a whole folder
    (proj / "nwbExport.m").rename(proj / "NwbExport.m")
    shutil.rmtree(proj / "+misc")
    g = ctx.scmd("apidoc renamed", "apidoc", "-c", docs)
    ctx.expect(
        g.returncode == 0 and not (docs / "api" / "misc.rst").exists(),
        "apidoc removes the page of a deleted folder",
    )
    r = build("renamed and deleted")
    ctx.expect(
        "NwbExport" in r.html("api/global.html") and not r.warned(r"nwbExport|\+misc"),
        "a file renamed by case is documented under its new name, no warning",
    )
    # an incremental parallel build after an edit
    f.write_text(
        f.read_text(encoding="utf-8").replace("Zebra42", "Zebra43"), encoding="utf-8"
    )
    j = ctx.sphinx("-j after an edit", docs, html, "-j", "auto", fresh=False)
    ctx.expect(
        j.rc == 0 and any(b"Zebra43" in d for d in j.files().values()),
        "an incremental -j build picks up the edit",
    )
    final = build("final incremental")
    clean = ctx.sphinx("clean build", docs, ctx.path("clean"))
    same_pages(ctx, "the incremental build equals a clean build", final, clean)


MANUAL = """
    User manual
    ===========

    .. mat:currentfolder:: .

    .. mat:autofunction:: nwbRead

    .. mat:autofunction:: nwbExport(nwb, filename)

       Content after the help text.

    .. mat:autoclass:: NwbFile
       :members:
       :undoc-members:
       :show-inheritance:
       :inherited-members:
       :member-order: bysource

    .. mat:autoclass:: types.untyped.Set
       :members: validateAll, export, add
       :private-members:
       :protected-members:
       :hidden-members:
       :access-list-members: ?matnwb.mixin.HasUnnamedGroups
       :exclude-members: export
       :member-order: groupwise

    .. mat:autoclass:: +types/+untyped/@DataStub/DataStub.m
       :members:

    .. mat:automethod:: types.untyped.Set.validateAll
       :noindex:

    .. mat:autoclass:: spec.enum.Primitives
       :members:
       :undoc-members:

    .. mat:autoscript:: tutorials/convertTrials.m

    .. mat:autodata:: tutorials/dataPipe.m

    .. mat:autofolder:: +misc/
       :members:
       :synopsis: Small helpers.
       :platform: any
       :deprecated:

    .. mat:autonamespace:: file.interface
       :members:
       :undoc-members:
       :synopsis: The interfaces.

    .. mat:autonamespace:: io.space
       :members: segmentSelection

    .. mat:folder:: +io/+config/
       :synopsis: Configuration.

    .. mat:namespace:: types.untyped
       :synopsis: Untyped containers.

    .. mat:currentfolder:: +types/+untyped

    Links, one per item:

    * L01 :mat:class:`Set.m`
    * L02 :mat:class:`~types.untyped.Set`
    * L03 :mat:func:`.nwbRead`
    * L04 :mat:meth:`types.untyped.Set.add`
    * L05 :mat:obj:`the reader <nwbRead>`
    * L06 :any:`nwbRead`
    * L07 :mat:folder:`+misc/`
    * L08 :mat:namespace:`types.untyped`
    * L09 :mat:class:`spec.enum.Primitives`
    * L10 :mat:scpt:`tutorials/convertTrials.m`
    * L11 :mat:func:`+misc/str2validName.m`
    * L12 :mat:class:`@DataStub/DataStub.m`

    .. mat:currentfolder:: None

    Hand-written descriptions
    -------------------------

    .. mat:function:: handWritten(a, [b, ]c) -> y
       :annotation: helper

       A hand-written function.

    .. mat:class:: Shape(x)
       :abstract:

       A hand-written class.

       .. mat:method:: area()

       .. mat:staticmethod:: fromJson(text)

       .. mat:attribute:: Sides

       .. mat:event:: Changed

    .. mat:script:: setupAll

    .. mat:application:: Viewer

    .. mat:data:: settings

    * L13 :mat:func:`handWritten`
    * L14 :mat:meth:`Shape.area`
    * L15 :mat:event:`Shape.Changed`
    """

MORE = """
    More forms
    ==========

    .. mat:function:: nwbRead(f)
       :noindex:

    .. mat:function:: g() -> y

    Mat helper
    ----------

    .. mat:function:: helper

    .. mat:method:: area()

    .. mat:attribute:: W

    .. mat:folder:: +io/+spec/

    .. mat:folder:: +io/+spec/
       :synopsis: Described twice; the last one is the link target.

    .. mat:autoclass:: types.untyped.Set
       :noindex:
       :members: add
       :exclude-members:

       .. mat:automethod:: add
          :noindex:

    .. mat:autofolder:: +misc/
       :noindex:
       :members:
       :member-order: bysource

    .. mat:autofolder:: ./
       :noindex:
       :members:

    .. mat:autoattribute:: +types/+untyped/@DataStub/DataStub.m.filename
       :annotation: "a file name"
       :noindex:

    .. mat:autoattribute:: +types/+untyped/@DataStub/DataStub.m.path
       :annotation:
       :noindex:

    .. mat:autoenum:: spec.enum.Primitives.Groups
       :noindex:

    .. mat:namespace:: types.untyped

    * N01 :mat:class:`Set`
    * N02 :mat:meth:`~+types/+untyped/Set.m.add`
    * N03 :mat:func:`~nwbRead.m`
    * N04 :any:`nwbRead()`
    * N05 :mat:folder:`+io/+spec/`
    * N06 :mat:func:`helper`
    * N07 :mat:obj:`NwbFile.m.acquisition`
    """

MISTAKES = """
    Mistakes
    ========

    Each one should warn.

    .. mat:autofunction:: noSuchFunction

    .. mat:namespace:: no.such.namespace

    .. mat:folder:: +types/+untyped/@DataStub/

    .. mat:autonamespace:: io.space
       :members: segmentSelection, noSuchMember
       :noindex:

    .. mat:autoclass:: types.untyped.Set
       :noindex:
       :no-such-option:

    .. mat:autoclass:: types.untyped.Set
       :noindex:
       :member-order: sideways

    .. mat:currentfolder:: +types/+untyped

    MATLAB does not see a bare ``Set`` from inside ``+types/+untyped``:

    .. mat:autoclass:: Set
       :noindex:

    * M02 :mat:class:`Set`

    .. mat:autofolder:: +misc/
       :noindex:

    .. mat:autofunction:: str2validName
       :noindex:

    .. mat:folder:: no_such_folder/

    .. mat:currentfolder:: no_such_folder

    .. mat:autofolder:: +misc/(x)
       :noindex:

    .. mat:autofolder:: +misc/
       :noindex:
       :members: str2validName, nopeFile

    .. mat:autonamespace:: no.such
       :noindex:

    .. mat:autonamespace:: io.space(x)
       :noindex:

    * M01 :mat:func:`noSuchFunction`
    """


def link_items(html):
    """``{"L01": True, ...}``: whether each list item ``Lnn``/``Mnn`` has a link."""
    out = {}
    for item in re.findall(r"<li>(.*?)</li>", html, flags=re.DOTALL):
        m = re.match(r"\s*(?:<p>)?\s*([LM]\d\d)\b", item)
        if m:
            out[m.group(1)] = "<a " in item
    return out


@scenario
def handwritten(ctx):
    """Hand-written pages on matnwb with every directive, option and role
    (as a user writes them, no apidoc), and a page of mistakes that must warn.
    """
    docs = ctx.conf(
        ctx.path("docs"),
        matlab_src_code_project_root=str(REPOS / "matnwb"),
        matlab_inherited_members=True,
        nitpicky=True,
    )
    ctx.write(
        "docs/index.rst",
        """
        matnwb by hand
        ==============

        .. toctree::

           manual
           more
           mistakes
        """,
    )
    ctx.write("docs/manual.rst", MANUAL)
    ctx.write("docs/mistakes.rst", MISTAKES)
    ctx.write("docs/more.rst", MORE)
    b = ctx.sphinx("html", docs, ctx.path("html"))
    ctx.require(b.rc == 0, f"build: exit 0 (got {b.rc})")
    manual = [r for r in b.records if "manual.rst" in r or "docstring of" in r]
    mat_warnings = [r for r in manual if re.search(r"\[(mat|ref)\.", r)]
    ctx.expect(
        not mat_warnings,
        f"the manual gives no mat.* or ref.* warning ({len(mat_warnings)}: "
        f"{[w[-160:] for w in mat_warnings[:3]]})",
    )
    links = link_items(b.html("manual.html"))
    unlinked = sorted(k for k, v in links.items() if not v)
    ctx.expect(len(links) == 15, f"the manual has its 15 link items ({len(links)})")
    ctx.expect(not unlinked, f"every role on the manual links ({unlinked})")
    page = b.html("manual.html")
    for what, needle in (
        ("an inherited member says where it comes from", "Inherited from"),
        ("show-inheritance adds Bases:", "Bases:"),
        ("the explicit signature replaces the file's", "nwbExport</span></span><span"),
        ("content after the help is kept", "Content after the help text."),
        ("the enumeration values are listed", "Datasets"),
        ("the folder synopsis is not dropped", "Small helpers."),
        ("an abstract hand-written class says so", "abstract"),
    ):
        ctx.expect(needle in page, what)
    ctx.expect(
        "export"
        not in re.findall(r'id="([^"]*Set[^"]*)"', page).__str__().split("Set.")[-1]
        or 'id="+types/+untyped/Set.m.export"' not in page,
        "exclude-members leaves out export",
    )
    ctx.expect(
        "matlab-folder-index.html" in b.files()
        or "mat-folderindex.html" in b.files()
        or any("folder" in f and "index" in f for f in b.files()),
        f"the folder index is written ({[f for f in b.files() if 'index' in f]})",
    )

    def warned(pattern, what, bug=None):
        hits = [r for r in b.records if "mistakes.rst" in r and re.search(pattern, r)]
        ctx.expect(bool(hits), what, bug=bug)

    warned(
        r"noSuchFunction.*\[mat\.not_found\]|don't know which object.*noSuchFunction",
        "an unknown name in an auto directive warns mat.not_found",
    )
    warned(r"no\.such\.namespace", "an unknown namespace warns")
    warned(r"@DataStub", "an @ class folder in mat:folder warns")
    warned(r"noSuchMember", "a :members: name that is not there warns")
    warned(r"no-such-option", "an unknown option is an error")
    warned(
        r"\+misc/\(x\).*\[mat\.directive\]|arguments.*\+misc",
        "arguments given to mat:autofolder warn mat.directive",
    )
    warned(r"nopeFile", "a :members: file that is not in the folder warns")
    warned(r"no\.such.*\[mat\.not_found\]", "mat:autonamespace of no namespace warns")
    warned(
        r"io\.space\(x\)|arguments.*io\.space",
        "arguments given to mat:autonamespace warn",
    )
    # a heading "Mat helper" and the function helper want the same id: one
    # mat.duplicate, and the function is not linkable (reference/warnings.rst)
    more = [r for r in b.records if "more.rst" in r]
    dup = [r for r in more if "'mat-helper'" in r and "[mat.duplicate]" in r]
    rest = [r for r in more if r not in dup and "target not found: helper" not in r]
    ctx.expect(
        len(dup) == 1 and not rest,
        f"the second page: one mat.duplicate for the shared id, nothing else "
        f"({len(dup)}, {rest[:2]})",
    )
    links = links_of(b.html("more.html"), "N")
    links.pop("N06", None)
    ctx.expect(
        len(links) == 6 and all(links.values()),
        f"every role on the second page links "
        f"({[k for k, v in links.items() if not v]})",
    )
    page = b.html("more.html")
    ctx.expect(
        'filename = "a file name"' in html_text(html_mod.unescape(page)),
        "autoattribute :annotation: is shown as = <value>",
    )
    warned(r"sideways", "a bad :member-order: value is an error")
    # directives.rst, "Description directives": they "never read a file and
    # never warn about a missing one", so a folder described by hand may be
    # one the build does not index; mat:currentfolder does not check either
    ctx.expect(
        not [r for r in b.records if "no_such_folder" in r],
        "mat:folder and mat:currentfolder of a folder that is not indexed do "
        "not warn (description directives)",
    )
    warned(
        r"don't know which object to document for 'Set'",
        "an auto directive does not resolve a name MATLAB cannot see "
        "(as the role does not)",
    )
    warned(
        r"don't know which object to document for 'str2validName'",
        "after mat:autofolder:: +misc/, a bare name MATLAB cannot see is not resolved",
    )
    warned(
        r"mat:class reference target not found: Set\b",
        "a role does not resolve a name MATLAB cannot see",
    )
    ctx.expect(
        "mat/ref/no_such_folder/index.html" in b.files(),
        "a folder described by hand has its stable address, indexed or not",
    )
    warned(
        r"noSuchFunction.*\[ref\.|M01|"
        r"mat:func reference target not found: noSuchFunction",
        "-n: a role to a missing object warns",
    )

    # the same objects documented by apidoc and by hand: a duplicate warns
    ctx.conf(
        ctx.path("dup"),
        matlab_src_code_project_root=str(REPOS / "matnwb"),
        matlab_apidoc_output_dir="api",
    )
    ctx.write(
        "dup/index.rst",
        """
        Duplicates
        ==========

        .. toctree::

           api/index

        .. mat:autofunction:: nwbRead
        """,
    )
    ctx.scmd("dup apidoc", "apidoc", "-c", ctx.path("dup"))
    for jobs in ((), ("-j", "auto")):
        d = ctx.sphinx(
            f"dup {' '.join(jobs)}",
            ctx.path("dup"),
            ctx.path("dup-html" + "-j" * bool(jobs)),
            *jobs,
        )
        hits = d.warned(r"nwbRead.*(duplicate|described)")
        ctx.expect(
            len(hits) == 1,
            f"{'-j: ' if jobs else ''}describing nwbRead "
            f"twice warns once ({len(hits)})",
        )


def library(ctx, name, project, toc="api/index", **values):
    """Apidoc and an html build of the checkout ``project`` as ``name``; return
    the build (its objects.inv is the inventory of the library).
    """
    docs = apidoc_project(ctx, project, folder=name, **values)
    (docs / "index.rst").write_text(
        f"{name}\n{'=' * len(name)}\n\n.. toctree::\n\n   {toc}\n", encoding="utf-8"
    )
    ctx.require(
        ctx.scmd(f"{name} apidoc", "apidoc", "-c", docs, "-q").returncode == 0,
        f"{name}: apidoc",
    )
    b = ctx.sphinx(f"{name} html", docs, ctx.path(f"{name}-html"))
    ctx.require(
        b.rc == 0 and (b.out / "objects.inv").is_file(),
        f"{name}: html with objects.inv",
    )
    return b


INTERSPHINX_PAGE = """
    Links to other projects
    =======================

    * X01 :mat:class:`types.untyped.Set`
    * X02 :mat:func:`nwbRead.m`
    * X03 :mat:meth:`types.untyped.Set.add`
    * X04 :mat:namespace:`types.untyped`
    * X05 :mat:func:`one:nwbRead.m`
    * X06 :external+one:mat:func:`nwbRead`
    * X07 :mat:namespace:`one:types.untyped`
    * X08 :external+one:mat:namespace:`types.untyped`
    * X09 :mat:folder:`vh:neuroscience/anatomy/`
    * X10 :mat:func:`intfireleakyel_init`
    * X11 :mat:obj:`types.untyped.Set`
    * X12 :mat:func:`Read it <nwbRead.m>`
    * X13 :mat:namespace:`vlt.app`
    * X14 :mat:namespace:`vh:vlt.app`
    * X15 :external+vh:mat:namespace:`vlt.app`
    * X16 :external:mat:namespace:`vlt.app`
    """

TWO_VERSIONS_PAGE = """
    Two versions of one library
    ===========================

    * Y01 :mat:func:`nwbRead.m`
    * Y02 :mat:func:`one:nwbRead.m`
    * Y03 :mat:func:`two:nwbRead`
    * Y04 :mat:class:`one:types.untyped.Set`
    * Y05 :external:mat:func:`nwbRead`
    * Y06 :external:mat:class:`one:types.untyped.Set`
    * Y07 :external:mat:func:`one:nwbRead.m`
    """


def links_of(html, prefix):
    """``{"X01": "<href>" or None, ...}`` for the list items starting ``prefix``."""
    out = {}
    for item in re.findall(r"<li>(.*?)</li>", html, flags=re.DOTALL):
        m = re.match(r"\s*(?:<p>)?\s*(" + prefix + r"\d\d)\b", item)
        if m:
            href = re.search(r'<a [^>]*href="([^"]*)"', item)
            out[m.group(1)] = href.group(1) if href else None
    return out


@scenario
def intersphinx(ctx):
    """Cross-project links: WEC-Sim_Applications to WEC-Sim with auto-links;
    a hand-written page to matnwb and vhlab (namespace and folder grouping,
    chooser pages); two versions of matnwb at once.
    """
    wecsim = library(ctx, "wecsim", "WEC-Sim")
    one = library(ctx, "one", "matnwb")
    two = library(ctx, "two", "matnwb")
    vh = library(
        ctx,
        "vh",
        "vhlab-toolbox-matlab",
        matlab_apidoc_group="folder",
        matlab_link_shadowed_files_to_chooser_pages=True,
    )

    def inv(b, url):
        return (url, str(b.out / "objects.inv"))

    # a real consumer of a real library, auto-linked
    apps = apidoc_project(
        ctx,
        "WEC-Sim_Applications",
        folder="apps",
        matlab_auto_link="all",
        extensions=[
            "sphinx.ext.autodoc",
            "sphinxcontrib.matlab",
            "sphinx.ext.intersphinx",
        ],
        intersphinx_mapping={"wecsim": inv(wecsim, "https://wecsim.example/")},
    )
    (apps / "index.rst").write_text("Apps\n====\n\n.. toctree::\n\n   api/index\n")
    ctx.scmd("apps apidoc", "apidoc", "-c", apps, "-q")
    a = ctx.sphinx("apps html", apps, ctx.path("apps-html"))
    ctx.expect(a.rc == 0, "WEC-Sim_Applications with intersphinx: exit 0")
    # matlab_auto_link links the project's own objects; the count of links
    # into the library is recorded, not checked (configuration.rst does not say)
    n = sum(d.count(b"https://wecsim.example/") for d in a.files().values())
    print(f"    (note: {n} auto-links into WEC-Sim)")
    # warnings.rst: mat.ambiguous is given where the name is used
    names = a.warned(r"in the docstring of .*\[mat\.ambiguous\]")
    ctx.expect(
        all(re.match(r"\S.*:docstring of .*:\d+: WARNING", r) for r in names)
        and len(names) == len(set(names)),
        f"an ambiguous auto-link warns once, at the help's file and line "
        f"({len(names)})",
    )

    # a hand-written page
    ext = ["sphinxcontrib.matlab", "sphinx.ext.intersphinx"]
    docs = ctx.conf(
        ctx.path("consumer"),
        extensions=ext,
        nitpicky=True,
        matlab_link_shadowed_files_to_chooser_pages=True,
        intersphinx_mapping={
            "one": inv(one, "https://one.example/"),
            "vh": inv(vh, "https://vh.example/"),
        },
    )
    ctx.write("consumer/index.rst", INTERSPHINX_PAGE)
    c = ctx.sphinx("consumer html", docs, ctx.path("consumer-html"))
    ctx.expect(c.rc == 0, "the consumer builds")
    links = links_of(c.html("index.html"), "X")
    bugs = {}
    for key, href in sorted(links.items()):
        site = (
            "https://vh.example/"
            if key in ("X09", "X10", "X13", "X14", "X15", "X16")
            else "https://one.example/"
        )
        ctx.expect(
            bool(href) and href.startswith(site),
            f"{key} links to {site} ({href})",
            bug=bugs.get(key),
        )
    ctx.expect(len(links) == 16, f"16 link items ({len(links)})")
    ctx.expect(
        "mat/name/intfireleakyel_init" in (links.get("X10") or ""),
        "an ambiguous name links to the library's chooser page",
    )
    ctx.expect(not c.warned(r"intfireleakyel_init"), "... without a warning")

    # without chooser pages: the ambiguous name warns, lists both, stays text
    plain = ctx.conf(
        ctx.path("plain"),
        extensions=ext,
        nitpicky=True,
        intersphinx_mapping={"vh": inv(vh, "https://vh.example/")},
    )
    ctx.write(
        "plain/index.rst", "Plain\n=====\n\n* X10 :mat:func:`intfireleakyel_init`\n"
    )
    pl = ctx.sphinx("no choosers", plain, ctx.path("plain-html"))
    ctx.expect(
        links_of(pl.html("index.html"), "X").get("X10") is None
        and len(pl.warned(r"intfireleakyel_init.*\[mat\.ambiguous\]")) == 1,
        "without chooser pages an ambiguous name is text with one mat.ambiguous",
    )
    # a library without stable URLs: links go to the page addresses
    flat = library(ctx, "flat", "matnwb", matlab_stable_urls=False)
    fc = ctx.conf(
        ctx.path("flatc"),
        extensions=ext,
        intersphinx_mapping={"flat": inv(flat, "https://flat.example/")},
    )
    ctx.write("flatc/index.rst", "Flat\n====\n\n* F01 :mat:func:`nwbRead`\n")
    f = ctx.sphinx("flat consumer", fc, ctx.path("flatc-html"))
    href = links_of(f.html("index.html"), "F").get("F01") or ""
    ctx.expect(
        href.startswith("https://flat.example/")
        and "/mat/ref/" not in href
        and "#mat-nwbRead.m" in href,
        f"a library without stable URLs: the link goes to the page ({href})",
    )

    # two versions of one library
    docs2 = ctx.conf(
        ctx.path("versions"),
        extensions=ext,
        nitpicky=True,
        intersphinx_mapping={
            "one": inv(one, "https://one.example/"),
            "two": inv(two, "https://two.example/"),
        },
    )
    ctx.write("versions/index.rst", TWO_VERSIONS_PAGE)
    v = ctx.sphinx("versions html", docs2, ctx.path("versions-html"))
    links = links_of(v.html("index.html"), "Y")
    ctx.expect(links.get("Y01") is None, "Y01: a path reference in both is not linked")
    ctx.expect(
        len(
            v.warned(
                r"nwbRead.m.*one:nwbRead.m.*two:nwbRead.m|"
                r"one:nwbRead.m, two:nwbRead.m"
            )
        )
        >= 1,
        "... and the warning lists one:nwbRead.m and two:nwbRead.m",
    )
    for key, site in (
        ("Y02", "https://one.example/"),
        ("Y03", "https://two.example/"),
        ("Y04", "https://one.example/"),
        ("Y06", "https://one.example/"),
        ("Y07", "https://one.example/"),
    ):
        href = links.get(key)
        ctx.expect(
            bool(href) and href.startswith(site),
            f"{key} links to {site} ({href})",
        )
    y05 = [r for r in v.records if "index.rst:8:" in r]
    ctx.expect(
        len(y05) == 1 and "[mat.ambiguous]" in y05[0],
        f"Y05: one warning, mat.ambiguous, for an ambiguous :external: role "
        f"({len(y05)})",
    )


#: (values, outcomes, message) of each invalid configuration, run in
#: "apidoc" (scmd apidoc), "html" (sphinx-build) and "api" (-b
#: matlab-api-check). A run stops for a bad value it uses and warns once for
#: one that only another run uses (reference/configuration.rst):
#: "stop": exit 2 and the message (a regular expression), no traceback;
#: "warn": one mat.config warning that matches the message, and exit 0;
#: "type": Sphinx's own type warning for a value it does not use, no
#: mat.config, exit 0; "ok": no warning naming it, exit 0.
BAD_CONFIG = [
    (
        {"matlab_src_code_project_root": "../no_such_root"},
        "apidoc=stop html=stop api=stop",
        r"matlab_src_code_project_root \'.*no_such_root\' is not a folder",
    ),
    (
        {"matlab_src_code_project_root": 5},
        "apidoc=stop html=stop api=stop",
        r"matlab_src_code_project_root",
    ),
    (
        {"matlab_src_include_patterns": "*.m"},
        "apidoc=stop html=stop api=stop",
        r"matlab_src_include_patterns",
    ),
    (
        {"matlab_src_include_patterns": ["src\\*.m"]},
        "apidoc=stop html=stop api=stop",
        r"matlab_src_include_patterns",
    ),
    (
        {"matlab_src_include_patterns": ["/abs/*.m"]},
        "apidoc=stop html=stop api=stop",
        r"matlab_src_include_patterns",
    ),
    (
        {"matlab_src_exclude_patterns": ["../*.m"]},
        "apidoc=stop html=stop api=stop",
        r"matlab_src_exclude_patterns",
    ),
    (
        {"matlab_src_exclude_patterns": [""]},
        "apidoc=stop html=stop api=stop",
        r"matlab_src_exclude_patterns",
    ),
    (
        {"matlab_src_sidecar_suffixes": ["md"]},
        "apidoc=stop html=stop api=stop",
        r"matlab_src_sidecar_suffixes",
    ),
    ({"matlab_src_sidecar_suffixes": [".md"]}, "apidoc=ok html=stop api=stop", r"myst"),
    (
        {"matlab_src_encoding": "no-such-codec"},
        "apidoc=stop html=stop api=stop",
        r"no-such-codec",
    ),
    ({"matlab_version": "R2020c"}, "apidoc=stop html=stop api=stop", r"R2020c"),
    (
        {"matlab_auto_link": "some"},
        "apidoc=warn html=stop api=stop",
        r"matlab_auto_link",
    ),
    (
        {"matlab_external_names": "abc"},
        "apidoc=warn html=stop api=stop",
        r"matlab_external_names",
    ),
    (
        {"matlab_external_names": [1]},
        "apidoc=warn html=stop api=stop",
        r"matlab_external_names",
    ),
    (
        {"matlab_external_names": ["("]},
        "apidoc=warn html=stop api=stop",
        r"matlab_external_names",
    ),
    (
        {"matlab_inherited_members": "yes"},
        "apidoc=warn html=stop api=stop",
        r"matlab_inherited_members",
    ),
    (
        {"matlab_show_property_default_value": "no"},
        "apidoc=warn html=stop api=stop",
        r"matlab_show_property_default_value must be bool",
    ),
    (
        {"matlab_show_property_specs": 0},
        "apidoc=warn html=stop api=stop",
        r"matlab_show_property_specs must be bool",
    ),
    (
        {"matlab_class_signature": "no"},
        "apidoc=warn html=stop api=stop",
        r"matlab_class_signature must be bool",
    ),
    (
        {"matlab_add_namespace_names": "no"},
        "apidoc=warn html=stop api=stop",
        r"matlab_add_namespace_names must be bool",
    ),
    (
        {"matlab_link_shadowed_files_to_chooser_pages": "no"},
        "apidoc=warn html=stop api=stop",
        r"matlab_link_shadowed_files_to_chooser_pages must be bool",
    ),
    (
        {"matlab_stable_urls": "no"},
        "apidoc=warn html=stop api=type",
        r"matlab_stable_urls",
    ),
    (
        {"matlab_stable_urls": 0},
        "apidoc=warn html=stop api=warn",
        r"matlab_stable_urls must be bool",
    ),
    ({"matlab_src_dir": "src"}, "apidoc=stop html=stop api=stop", r"matlab_src_dir"),
    (
        {"matlab_keep_package_prefix": True},
        "apidoc=stop html=stop api=stop",
        r"matlab_keep_package_prefix",
    ),
    (
        {"matlab_short_links": True},
        "apidoc=stop html=stop api=stop",
        r"matlab_short_links",
    ),
    (
        {"matlab_api_check_rules": []},
        "apidoc=warn html=type api=stop",
        r"matlab_api_check_rules",
    ),
    (
        {"matlab_api_check_rules": {"no_such_rule": "error"}},
        "apidoc=warn html=warn api=stop",
        r"no_such_rule",
    ),
    (
        {"matlab_api_check_rules": {"description": "fatal"}},
        "apidoc=warn html=warn api=stop",
        r"fatal",
    ),
    (
        {"matlab_api_check_section_labels": []},
        "apidoc=warn html=type api=stop",
        r"matlab_api_check_section_labels",
    ),
    (
        {"matlab_api_check_section_labels": {"Nope": "X"}},
        "apidoc=warn html=warn api=stop",
        r"Nope",
    ),
    (
        {"matlab_api_check_ignore_patterns": "x"},
        "apidoc=warn html=type api=stop",
        r"matlab_api_check_ignore_patterns",
    ),
    (
        {"matlab_api_check_files": 5},
        "apidoc=warn html=warn api=stop",
        r"matlab_api_check_files",
    ),
    (
        {"matlab_api_check_files": ["../x.m"]},
        "apidoc=warn html=warn api=stop",
        r"matlab_api_check_files: '../x.m' leaves",
    ),
    (
        {"matlab_api_check_files_from": ""},
        "apidoc=warn html=warn api=stop",
        r"matlab_api_check_files_from",
    ),
    (
        {"matlab_api_check_files_from": "no_such_list.txt"},
        "apidoc=ok html=ok api=stop",
        r"no_such_list",
    ),
    (
        {"matlab_api_check_ignore_unmatched": "no"},
        "apidoc=warn html=type api=stop",
        r"matlab_api_check_ignore_unmatched",
    ),
    (
        {"matlab_apidoc_output_dir": None},
        "apidoc=stop html=ok api=ok",
        r"matlab_apidoc_output_dir",
    ),
    (
        {"matlab_apidoc_output_dir": 5},
        "apidoc=stop html=stop api=type",
        r"matlab_apidoc_output_dir",
    ),
    ({"matlab_apidoc_output_dir": "conf.py"}, "apidoc=stop html=ok api=ok", r"conf.py"),
    (
        {"matlab_apidoc_templatedir": "no_such_templates"},
        "apidoc=stop html=ok api=ok",
        r"no_such_templates",
    ),
    (
        {"matlab_apidoc_group": "x"},
        "apidoc=stop html=warn api=warn",
        r"matlab_apidoc_group",
    ),
    (
        {"matlab_apidoc_page_size": 0},
        "apidoc=stop html=warn api=warn",
        r"matlab_apidoc_page_size",
    ),
    (
        {"matlab_apidoc_tocfile": "a/b"},
        "apidoc=stop html=warn api=warn",
        r"matlab_apidoc_tocfile",
    ),
    (
        {"matlab_apidoc_tocfile": ""},
        "apidoc=stop html=warn api=warn",
        r"matlab_apidoc_tocfile",
    ),
    (
        {"matlab_apidoc_maxdepth": "x"},
        "apidoc=stop html=type api=type",
        r"matlab_apidoc_maxdepth",
    ),
    (
        {"matlab_apidoc_maxdepth": 0},
        "apidoc=stop html=warn api=warn",
        r"matlab_apidoc_maxdepth must be 1 or more, or -1",
    ),
    (
        {"matlab_apidoc_maxdepth": -1},
        "apidoc=ok html=ok api=ok",
        r"matlab_apidoc_maxdepth",
    ),
    (
        {"matlab_apidoc_separate": "yes"},
        "apidoc=stop html=type api=type",
        r"matlab_apidoc_separate",
    ),
    ({"suppress_warnings": "mat.apidoc"}, "apidoc=stop", r"suppress_warnings"),
    (
        {"matlab_src_code_project_root": None},
        "apidoc=stop html=ok api=ok",
        r"matlab_src_code_project_root",
    ),
    (
        {"matlab_src_code_project_root": None, "matlab_src_sidecar_suffixes": [".rst"]},
        "apidoc=stop html=stop api=stop",
        r"matlab_src_sidecar_suffixes|matlab_src_code_project_root",
    ),
    (
        {"matlab_src_code_project_root": None, "matlab_src_include_patterns": ["*.m"]},
        "apidoc=stop html=stop api=stop",
        r"matlab_src_include_patterns|matlab_src_code_project_root",
    ),
    (
        {"matlab_src_code_project_root": ".", "matlab_src_sidecar_suffixes": [".rst"]},
        "apidoc=stop html=stop api=stop",
        r"matlab_src_code_project_root|source folder|source directory",
    ),
    (
        {"matlab_src_include_patterns": ["."]},
        "apidoc=stop html=stop api=stop",
        r"matlab_src_include_patterns",
    ),
    (
        {"matlab_src_sidecar_suffixes": ".md"},
        "apidoc=stop html=stop api=stop",
        r"matlab_src_sidecar_suffixes",
    ),
    (
        {"matlab_api_check_section_labels": {"inputs": "Inputs"}},
        "apidoc=warn html=warn api=stop",
        r"matlab_api_check_section_labels",
    ),
    (
        {"matlab_api_check_section_labels": {"inputs": ["a:b"]}},
        "apidoc=warn html=warn api=stop",
        r"a:b",
    ),
]


@scenario
def bad_config(ctx):
    """Every invalid matlab_* value (and a few Sphinx ones the tools read):
    the run that uses it stops with exit 2 and names the setting, no
    traceback; another run warns once (mat.config) and goes on; a misspelled
    matlab_ name stops every run.
    """
    root = str(REPOS / "regularizeNd")
    # No finding fails the check, so a run that goes on exits with 0.
    quiet = dict.fromkeys(API_CHECK_RULES, "ignore")
    for i, (values, outcomes, message, *bug) in enumerate(BAD_CONFIG):
        bug = bug[0] if bug else None
        docs = ctx.conf(
            ctx.path(f"c{i:02d}"),
            **{
                "matlab_src_code_project_root": root,
                "matlab_apidoc_output_dir": "api",
                "matlab_api_check_rules": quiet,
                **values,
            },
        )
        (docs / "index.rst").write_text("Bad\n===\n", encoding="utf-8")
        what = ", ".join(f"{k}={v!r}" for k, v in values.items())
        names = [k for k in values if k.startswith("matlab_")]
        for tool, outcome in (o.split("=") for o in outcomes.split()):
            if tool == "apidoc":
                proc = ctx.scmd(f"{i:02d} apidoc", "apidoc", "-n", "-c", docs)
                rc, text = proc.returncode, proc.stdout + proc.stderr
                warned = proc.stderr.splitlines()
            else:
                b = ctx.sphinx(
                    f"{i:02d} {tool}",
                    docs,
                    ctx.path(f"c{i:02d}-{tool}"),
                    builder="html" if tool == "html" else "matlab-api-check",
                )
                rc, text = b.rc, b.stdout + b.stderr + b.warnings
                warned = b.warnings.splitlines()
            ours = [line for line in warned if "[mat.config]" in line]
            sphinx = [
                line
                for line in warned
                if any(f"The config value `{n}'" in line for n in names)
            ]
            if outcome == "stop":
                ok = rc == 2 and re.search(message, text) is not None
            elif outcome == "warn":
                ok = rc == 0 and len(ours) == 1 and re.search(message, ours[0])
                ok = ok and not sphinx
            elif outcome == "type":
                ok = rc == 0 and not ours and len(sphinx) == 1
            else:
                ok = rc == 0 and not ours and not sphinx
            # the message: the last line of Sphinx's report (8.2 and later)
            lines = text.strip().splitlines() or [""]
            first = next(
                (line.strip() for line in lines if "ConfigError: " in line),
                (ours or sphinx or lines)[-1],
            )[:150]
            ctx.expect(
                bool(ok),
                f"{tool}: {what}: {outcome} (exit {rc}: {first})",
                bug=bug if tool == "html" else None,
            )

    # a misspelled matlab_ name and no conf.py at all
    docs = ctx.conf(
        ctx.path("typo"),
        matlab_src_code_project_root=root,
        matlab_apidoc_output_dir="api",
        matlab_auto_links="all",
    )
    (docs / "index.rst").write_text("Typo\n====\n", encoding="utf-8")
    # an error that suggests the name (reference/configuration.rst)
    b = ctx.sphinx("typo html", docs, ctx.path("typo-html"))
    ctx.expect(
        b.rc == 2 and "did you mean matlab_auto_link?" in b.stderr,
        "a misspelled matlab_ name stops the build and suggests the name",
    )
    proc = ctx.scmd("typo apidoc", "apidoc", "-c", docs)
    ctx.expect(
        proc.returncode == 2 and "matlab_auto_link?" in proc.stderr,
        "... scmd apidoc too",
    )
    proc = ctx.scmd("no conf.py", "apidoc", "-c", ctx.path("empty"))
    ctx.expect(
        proc.returncode == 2 and "conf.py" in proc.stderr,
        f"scmd apidoc without conf.py: exit 2 naming conf.py ({proc.returncode})",
    )


FULL_ANSWERS = """
    project = "matlab2tikz by answers"
    author = "The scenario"
    matlab_version = "R2024b"
    group = "folder"
    theme = "alabaster"
    exclude = ["test"]
    markdown = false
    sidecars = false
    make = "plain"
    guide = false
    api_pages = "generate"
    napoleon_custom_sections = [["Inputs", "params_style"], "Description"]
    """

#: (answers file, message) of each invalid answers file: exit 2 naming it
BAD_ANSWERS = [
    ("nope = 1\n", r"nope"),
    ('markdown = "yes"\n', r"markdown"),
    ('group = "x"\n', r"group"),
    ("theme = 5\n", r"theme"),
    ('exclude = "tests"\n', r"exclude"),
    ('make = "cmake"\n', r"make"),
    ('api_pages = "x"\n', r"api_pages"),
    ('matlab_version = "R2020c"\n', r"R2020c"),
    ("napoleon_custom_sections = [5]\n", r"napoleon_custom_sections"),
    ("markdown = false\nsidecars = true\n", r"sidecars"),
    ('project = "unterminated\n', r"TOML|toml|line 1"),
    ('napoleon_custom_sections = "Inputs"\n', r"napoleon_custom_sections"),
]


def clone(ctx, project, dest, git=True):
    """Copy a checkout: a git clone (``git``), else a plain copy; return it."""
    path = ctx.path(dest)
    if git:
        subprocess.run(
            ["git", "clone", "-q", "--shared", str(REPOS / project), str(path)],
            check=True,
        )
    else:
        ctx.copy_project(project, dest)
    return path


def commit_all(path):
    """Commit everything in the git repository ``path``."""
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=s",
            "-c",
            "user.email=s@x",
            "commit",
            "-qm",
            "scenario",
        ],
        cwd=path,
        check=True,
    )


def git_status(path):
    """Return ``git status --porcelain`` of ``path``."""
    return subprocess.run(
        ["git", "status", "--porcelain"], cwd=path, capture_output=True, text=True
    ).stdout


@scenario
def quickstart(ctx):
    """Run scmd quickstart beyond -q: answered on stdin, from answers files (good
    and bad), -n, -f, outside git, a dirty .gitignore, a docs/ in use, a uv
    project; and scmd skills.
    """
    # 1. every question answered with its default, on stdin
    a = clone(ctx, "matlab2tikz", "a")
    proc = ctx.scmd("interactive", "quickstart", a, stdin="\n" * 40, cwd=a)
    ctx.require(
        proc.returncode == 0,
        f"interactive with defaults: exit 0 "
        f"({proc.returncode}: {proc.stderr.strip()[-200:]})",
    )
    ctx.expect(
        proc.stdout.count("?") >= 8 or proc.stdout.count("[") >= 8,
        "it asked its questions",
    )
    ctx.expect((a / "docs" / "conf.py").is_file(), "it wrote docs/conf.py")
    b = ctx.sphinx("a html", a / "docs", ctx.path("a-html"), "-n")
    ctx.expect(b.rc == 0, f"its docs build: exit 0 ({b.rc})")
    again = ctx.scmd("again without -f", "quickstart", a, "-q", cwd=a)
    ctx.expect(
        again.returncode == 2 and "conf.py" in again.stderr,
        "a second run without -f stops: exit 2 naming conf.py",
    )
    # its own edits of .gitignore and .gitattributes must be committed first
    # (reference/cli.rst: it stops when one has uncommitted changes)
    commit_all(a)
    before = (a / "docs" / "index.rst").read_text(encoding="utf-8")
    (a / "docs" / "index.rst").write_text("changed\n", encoding="utf-8")
    forced = ctx.scmd("again with -f", "quickstart", a, "-q", "-f", cwd=a)
    ctx.expect(forced.returncode == 0, "with -f: exit 0")
    ctx.expect(
        (a / "docs" / "index.rst").read_text(encoding="utf-8") == before,
        "-f rewrites index.rst",
    )

    # 2. a full answers file, saved again at the end
    answers = ctx.write("answers.toml", FULL_ANSWERS)
    c = clone(ctx, "matlab2tikz", "c")
    proc = ctx.scmd(
        "answers + save", "quickstart", c, "-a", answers, stdin="y\nsaved.toml\n", cwd=c
    )
    ctx.expect(proc.returncode == 0, f"-a FILE, then save: exit 0 ({proc.returncode})")
    saved = c / "saved.toml"
    ctx.expect(saved.is_file(), "the answers are saved to the path typed")
    conf = (
        (c / "docs" / "conf.py").read_text(encoding="utf-8")
        if (c / "docs" / "conf.py").exists()
        else ""
    )
    for what, needle in (
        ("project", "matlab2tikz by answers"),
        ("theme", "alabaster"),
        ("group", "folder"),
        ("version", "R2024b"),
        ("exclude", "test"),
    ):
        ctx.expect(needle in conf, f"conf.py has the answer {what}")
    ctx.expect(
        not (c / "docs" / "BUILDING_DOCS.md").exists(),
        "guide = false writes no BUILDING_DOCS.md",
    )
    b = ctx.sphinx("c html", c / "docs", ctx.path("c-html"), "-n")
    ctx.expect(b.rc == 0, "its docs build")

    # 3. the same file with -q, and without -q in CI (stdin at its end)
    d = clone(ctx, "matlab2tikz", "d")
    proc = ctx.scmd("answers -q", "quickstart", d, "-a", answers, "-q", cwd=d)
    ctx.expect(proc.returncode == 0, "-a FILE -q: exit 0")
    e = clone(ctx, "matlab2tikz", "e")
    proc = ctx.scmd(
        "answers, stdin closed", "quickstart", e, "-a", answers, stdin="", cwd=e
    )
    ctx.expect(
        proc.returncode == 0,
        f"-a FILE in CI (stdin at its end): exit 0, not 'interrupted' "
        f"({proc.returncode})",
    )

    # 4. invalid answers files (with -n nothing is written)
    fresh = clone(ctx, "matlab2tikz", "fresh")
    for i, (text, message) in enumerate(BAD_ANSWERS):
        bad = ctx.write(f"bad{i}.toml", text)
        proc = ctx.scmd(
            f"bad answers {i}", "quickstart", fresh, "-a", bad, "-q", "-n", cwd=fresh
        )
        ctx.expect(
            proc.returncode == 2 and re.search(message, proc.stderr),
            f"answers {text.strip()!r}: exit 2 naming it "
            f"({proc.returncode}: {proc.stderr.strip()[-120:]})",
        )

    # 5. a dry run writes nothing
    f = clone(ctx, "matlab2tikz", "f")
    proc = ctx.scmd("dry run", "quickstart", f, "-n", "-q", cwd=f)
    ctx.expect(
        proc.returncode == 0 and not git_status(f) and not (f / "docs").exists(),
        "-n -q writes nothing",
    )
    ctx.expect("conf.py" in proc.stdout, "-n lists the files it would write")

    # 6. outside git, also when OUT is inside a repository (the default OUT is)
    g = clone(ctx, "matlab2tikz", "g", git=False)
    proc = ctx.scmd(
        "outside git",
        "quickstart",
        g,
        "-q",
        cwd=g,
        env={"GIT_CEILING_DIRECTORIES": str(g.parent)},
    )
    ctx.expect(proc.returncode == 0, "outside git: exit 0")
    ctx.expect(
        not (g / ".gitignore").exists()
        or "_build" not in (g / ".gitignore").read_text(encoding="utf-8"),
        "outside git it edits no .gitignore (prints the lines)",
    )
    ctx.expect("_build" in proc.stdout, "... and prints the .gitignore lines")

    # 7. uncommitted .gitignore stops it, naming the file
    h = clone(ctx, "matlab2tikz", "h")
    with open(h / ".gitignore", "a", encoding="utf-8") as fh:
        fh.write("scratch/\n")
    proc = ctx.scmd("dirty gitignore", "quickstart", h, "-q", cwd=h)
    ctx.expect(proc.returncode == 2, "an uncommitted .gitignore: exit 2")
    ctx.expect(
        ".gitignore has uncommitted" in proc.stderr,
        f"... naming .gitignore ({proc.stderr.strip()[-80:]})",
    )

    # 8. docs/ in use (an MkDocs folder): -q stops; interactive asks for another
    k = clone(ctx, "matlab2tikz", "k")
    ctx.write("k/docs/index.md", "# MkDocs\n")
    proc = ctx.scmd("docs in use -q", "quickstart", k, "-q", cwd=k)
    ctx.expect(
        proc.returncode == 2 and "docs" in proc.stderr, "docs/ in use with -q: exit 2"
    )
    proc = ctx.scmd(
        "docs in use", "quickstart", k, stdin="sphinx-docs\n" + "\n" * 40, cwd=k
    )
    ctx.expect(
        proc.returncode == 0 and (k / "sphinx-docs" / "conf.py").is_file(),
        "interactive: the folder typed instead is used",
    )

    # 9. usage errors
    proc = ctx.scmd("root is a file", "quickstart", a / "README.md", "-q")
    ctx.expect(proc.returncode == 2, "ROOT that is a file: exit 2")
    proc = ctx.scmd(
        "docs outside root", "quickstart", a, "-q", "-o", ctx.path("x"), cwd=a
    )
    ctx.expect(proc.returncode == 2, "DOCS outside ROOT: exit 2")
    # -o is relative to the working folder, not to ROOT
    (a / "sub").mkdir(exist_ok=True)
    proc = ctx.scmd(
        "-o from a subfolder", "quickstart", a, "-q", "-o", "d2", cwd=a / "sub"
    )
    ctx.expect(
        proc.returncode == 0 and (a / "sub" / "d2" / "conf.py").is_file(),
        f"-o is relative to the working folder ({proc.returncode})",
    )
    proc = ctx.scmd(
        "missing answers", "quickstart", a, "-q", "-a", ctx.path("none.toml")
    )
    ctx.expect(proc.returncode == 2, "a missing answers file: exit 2")

    # 10. a uv project gets the docs dependency group
    u = clone(ctx, "matlab2tikz", "u")
    (u / "pyproject.toml").write_text(
        '[project]\nname = "m2t"\nversion = "0"\nrequires-python = ">=3.11"\n\n'
        "[tool.uv]\n",
        encoding="utf-8",
    )
    commit_all(u)
    proc = ctx.scmd("uv project", "quickstart", u, "-q", cwd=u)
    text = (u / "pyproject.toml").read_text(encoding="utf-8")
    ctx.expect(
        proc.returncode == 0
        and "docs" in text
        and "sphinxcontrib-matlabdomain" in text,
        f"a uv project gets the docs group ({proc.returncode})",
    )

    # 11. scmd skills
    proc = ctx.scmd("skills list", "skills", "list")
    names = re.findall(r"^(\S+)$", proc.stdout, flags=re.MULTILINE)
    ctx.expect(proc.returncode == 0 and len(names) >= 2, f"skills list: {names}")
    dest = ctx.path("skills")
    proc = ctx.scmd("skills install", "skills", "install", "-d", dest)
    ctx.expect(
        proc.returncode == 0 and all((dest / n / "SKILL.md").is_file() for n in names),
        "skills install copies every skill",
    )
    proc = ctx.scmd("skills install again", "skills", "install", "-d", dest)
    ctx.expect(
        proc.returncode == 1, f"installing over them: exit 1 ({proc.returncode})"
    )
    (dest / names[0] / "SKILL.md").write_text("changed", encoding="utf-8")
    proc = ctx.scmd(
        "skills install -f", "skills", "install", "-d", dest, "-f", names[0]
    )
    ctx.expect(
        proc.returncode == 0
        and (dest / names[0] / "SKILL.md").read_text(encoding="utf-8") != "changed",
        "-f replaces a skill",
    )
    proc = ctx.scmd("skills unknown", "skills", "install", "-d", dest, "no-such-skill")
    ctx.expect(
        proc.returncode == 2 and "no-such-skill" in proc.stderr,
        f"an unknown skill: exit 2 naming it ({proc.returncode})",
    )


@scenario
def broken_input(ctx):
    """Build a copy of regularizeNd with every kind of broken or unusual input
    added: each gets its documented warning once (reference/warnings.rst),
    the rest is documented, nothing crashes; apidoc and api-check too.
    """
    proj = ctx.copy_project("regularizeNd", "proj")
    bad = proj / "broken"
    bad.mkdir()
    files = {
        "latin1Help.m": "function latin1Help\n% Gr\xfc\xdfe aus K\xf6ln.\nend\n".encode(
            "latin-1"
        ),
        "nulBytes.m": b"function nulBytes\n% NUL \x00 here\nend\n",
        "bomHelp.m": "﻿function bomHelp\n% BOMHELP Help after a BOM.\nend\n".encode(),
        "emptyFile.m": b"\n\n",
        "unreadable.m": b"function unreadable\n% UNREADABLE\nend\n",
    }
    for name, data in files.items():
        (bad / name).write_bytes(data)
    (bad / "unreadable.m").chmod(0)
    (bad / "private").mkdir()
    (bad / "private" / "2bad.m").write_text("function x = 2bad\nend\n")
    (bad / "folder.m").mkdir()
    (bad / "folder.m" / "inside.m").write_text("function inside\nend\n")
    (bad / "café.m").write_text("function cafe1\n% NFC\nend\n")
    (bad / "café.m").write_text("function cafe2\n% NFD\nend\n")
    os.makedirs(os.fsencode(str(bad)) + b"/badname", exist_ok=True)
    with open(os.fsencode(str(bad)) + b"/badname/caf\xe9.m", "wb") as fh:
        fh.write(b"function x\nend\n")
    outside = ctx.path("outside")
    outside.mkdir()
    (outside / "outsideFun.m").write_text("function outsideFun\nend\n")
    (bad / "linkOut").symlink_to(outside, target_is_directory=True)
    (bad / "linkCycle").symlink_to("..", target_is_directory=True)
    old = bad / "oldsite"
    (old / "_downloads").mkdir(parents=True)
    (old / "objects.inv").write_bytes(b"# Sphinx inventory version 2\n")
    (old / "searchindex.js").write_text("Search.setIndex({})")
    shutil.copy(
        proj / "source" / "regularizeNd.m", old / "_downloads" / "regularizeNd.m"
    )
    unreadable_dir = bad / "noAccess"
    unreadable_dir.mkdir()
    (unreadable_dir / "hidden.m").write_text("function hidden\nend\n")
    unreadable_dir.chmod(0)
    try:
        docs = ctx.conf(
            ctx.path("docs"),
            matlab_src_code_project_root=str(proj),
            matlab_apidoc_output_dir="api",
        )
        ctx.write("docs/index.rst", "Broken\n======\n\n.. toctree::\n\n   api/index\n")
        gen = ctx.scmd("apidoc", "apidoc", "-c", docs)
        ctx.expect(gen.returncode == 0, f"apidoc: exit 0 ({gen.returncode})")
        b = ctx.sphinx("html", docs, ctx.path("html"), "-n")
        ctx.expect(b.rc == 0, f"html: exit 0 ({b.rc})")
        api = ctx.sphinx("api-check", docs, ctx.path("api"), builder="matlab-api-check")
        ctx.expect(api.rc in (0, 1), f"api-check: exit 0 or 1 ({api.rc})")
    finally:
        unreadable_dir.chmod(0o755)
        (bad / "unreadable.m").chmod(0o644)
    expected = [
        ("unreadable.m", "mat.parse_error"),
        ("latin1Help.m", "mat.encoding"),
        ("nulBytes.m", "mat.invalid_matlab"),
        ("emptyFile.m", "mat.empty_code_file"),
        ("folder.m", "mat.folder_name"),
        ("differ only by Unicode form", "mat.parse_error"),
        ("is not valid UTF-8; it is not documented", "mat.parse_error"),
        ("linkOut", "mat.outside_root"),
        ("linkCycle", "mat.link_cycle"),
        ("noAccess", "mat.parse_error"),
    ]
    for needle, subtype in expected:
        hits = [r for r in b.records if needle in r and f"[{subtype}]" in r]
        ctx.expect(len(hits) == 1, f"html: {needle}: one {subtype} ({len(hits)})")
    # a file apidoc cannot read: one line with the cause, and it is left out
    hits = [ln for ln in gen.stderr.splitlines() if "unreadable.m" in ln]
    ctx.expect(
        len(hits) == 1
        and re.search(
            r"unreadable\.m cannot be read \(.+\); it is left out\. \[mat\.apidoc\]$",
            hits[0],
        )
        is not None,
        f"apidoc: unreadable.m: one mat.apidoc warning with the cause ({hits})",
    )
    ctx.expect(not b.warned(r"bomHelp"), "a file with a BOM: no warning")
    ctx.expect(
        "Help after a BOM"
        in "".join(d.decode("utf-8", "replace") for d in b.files().values()),
        "a file with a BOM is documented",
    )
    ctx.expect(
        "Köln" in "".join(d.decode("utf-8", "replace") for d in b.files().values()),
        "a Latin-1 help is decoded",
    )
    ctx.expect(
        not b.warned(r"regularizeNd.*several|oldsite"),
        "an old HTML output folder in the tree is not indexed",
    )
    ctx.expect(
        not any(
            "outsideFun" in d.decode("utf-8", "replace") for d in b.files().values()
        ),
        "a link out of the root is not followed",
    )
    # files below private/ never get mat.not_callable (user-guide/referencing.rst)
    ctx.expect(not b.warned(r"2bad"), "private/2bad.m: no warning")
    # regularizeNd's own README has an image that is not there (the baseline)
    unexpected = {
        k: v
        for k, v in b.subtypes.items()
        if not k.startswith("mat.") and k not in ("docutils", "image.not_readable")
    }
    ctx.expect(not unexpected, f"no other kinds of warning ({unexpected})")


#: (label, -D arguments, what must be true of the pages; None: they differ)
OPTION_BUILDS = [
    (
        "inherited",
        [
            "-D",
            "matlab_inherited_members=1",
            "-D",
            "autodoc_default_options.inherited-members=",
        ],
        lambda html: "Inherited from" in html,
    ),
    ("bysource", ["-D", "autodoc_member_order=bysource"], None),
    # members are already in sections by kind, so groupwise may equal the default
    ("groupwise", ["-D", "autodoc_member_order=groupwise"], lambda _html: True),
    ("autoclass both", ["-D", "autoclass_content=both"], None),
    ("autoclass init", ["-D", "autoclass_content=init"], None),
    ("class signature", ["-D", "matlab_class_signature=1"], None),
    ("no property defaults", ["-D", "matlab_show_property_default_value=0"], None),
    ("no property specs", ["-D", "matlab_show_property_specs=0"], None),
    ("no namespace names", ["-D", "matlab_add_namespace_names=0"], None),
    (
        "no parentheses",
        ["-D", "add_function_parentheses=0", "-D", "matlab_auto_link=all"],
        None,
    ),
    (
        "no docstring signature",
        ["-D", "autodoc_docstring_signature=0"],
        lambda _html: True,
    ),
    ("R2024a", ["-D", "matlab_version=R2024a"], lambda _html: True),
    ("no stable urls", ["-D", "matlab_stable_urls=0"], lambda _html: True),
]


@scenario
def options(ctx):
    """Build the configuration values and autodoc options on matnwb, each against
    the default build; chooser pages, other builders and an encoding on
    vhlab and YALMIP; a stable-URL clash; a removed hand-written page.
    """
    docs = apidoc_project(ctx, "matnwb", folder="nwb")
    ctx.write("nwb/index.rst", "matnwb\n======\n\n.. toctree::\n\n   api/index\n")
    ctx.scmd("nwb apidoc", "apidoc", "-c", docs, "-q")
    base = ctx.sphinx("default", docs, ctx.path("nwb-default"))
    ctx.require(base.rc == 0, "the default build")
    base_pages = {f: d for f, d in base.files().items() if f.startswith("api/")}
    for label, args, check in OPTION_BUILDS:
        b = ctx.sphinx(label, docs, ctx.path(f"nwb-{_slug(label)}"), *args)
        new = set(b.subtypes) - set(base.subtypes)
        ctx.expect(
            b.rc == 0 and not new,
            f"{label}: exit 0, no new kind of warning ({b.rc}, {sorted(new)})",
        )
        pages = {f: d for f, d in b.files().items() if f.startswith("api/")}
        if check is None:
            ctx.expect(pages != base_pages, f"{label}: changes the pages")
        else:
            ctx.expect(
                check("".join(d.decode("utf-8") for d in pages.values())),
                f"{label}: the pages show it",
            )
        if label == "no stable urls":
            ctx.expect(not (b.out / "mat").exists(), "no stable urls: no mat/ folder")

    # matlab_external_names silences -n for MATLAB's own names; emptied, they warn
    n0 = ctx.sphinx("-n", docs, ctx.path("nwb-n"), "-n")
    n1 = ctx.sphinx(
        "-n no external names",
        docs,
        ctx.path("nwb-n-ext"),
        "-n",
        "-D",
        "matlab_external_names=",
    )
    hits = n1.warned(r"reference target not found: (handle|matlab\.|dynamicprops)")
    ctx.expect(
        not n0.warned(r"reference target not found: (handle|matlab\.)") and hits,
        f"matlab_external_names: MATLAB's names warn only when "
        f"it is emptied ({len(hits)})",
    )

    # chooser pages for shadowed names, with every builder
    vh = apidoc_project(
        ctx,
        "vhlab-toolbox-matlab",
        folder="vh",
        matlab_link_shadowed_files_to_chooser_pages=True,
        matlab_auto_link="all",
    )
    ctx.write("vh/index.rst", "vhlab\n=====\n\n.. toctree::\n\n   api/index\n")
    ctx.scmd("vh apidoc", "apidoc", "-c", vh, "-q")
    b = ctx.sphinx("vh html", vh, ctx.path("vh-html"))
    ctx.expect(
        b.rc == 0 and not b.warned(r"\[mat\.ambiguous\]"),
        f"chooser pages: no mat.ambiguous ({len(b.warned('ambiguous'))})",
    )
    ctx.expect(
        (b.out / "mat" / "name" / "intfireleakyel_init.html").is_file(),
        "a shadowed name has its chooser page",
    )
    for builder in (
        "dirhtml",
        "singlehtml",
        "text",
        "latex",
        "epub",
        "texinfo",
        "man",
        "json",
        "xml",
        "htmlhelp",
    ):
        o = ctx.sphinx(f"vh {builder}", vh, ctx.path(f"vh-{builder}"), builder=builder)
        ctx.expect(o.rc == 0, f"-b {builder}: exit 0 ({o.rc})")
    # the encoding of a project with Latin-1 files
    y = apidoc_project(ctx, "YALMIP", folder="yalmip", matlab_src_encoding="latin-1")
    ctx.write("yalmip/index.rst", "YALMIP\n======\n\n.. toctree::\n\n   api/index\n")
    ctx.scmd("yalmip apidoc", "apidoc", "-c", y, "-q")
    b = ctx.sphinx("yalmip latin-1", y, ctx.path("yalmip-html"))
    ctx.expect(
        b.rc == 0 and not b.warned(r"\[mat\.encoding\]"),
        "matlab_src_encoding = latin-1: no mat.encoding warning",
    )

    # a file of html_extra_path where a stable address goes: a configuration
    # error (Sphinx 8.2 and later print their report for it, FAQ.rst) that
    # names the file and the fix, and the file is kept
    ctx.write("nwb-extra/mat/ref/nwbRead.m.html", "<html>mine</html>\n")
    c = ctx.sphinx(
        "stable url clash",
        docs,
        ctx.path("nwb-clash"),
        "-D",
        f"html_extra_path={ctx.path('nwb-extra')}",
    )
    ctx.expect(
        c.rc == 2, f"a clash of a stable address with a user file fails ({c.rc})"
    )
    ctx.expect(
        re.search(
            r"ConfigError: matlab_stable_urls: '.*nwbRead\.m\.html' is in the way"
            r".*Remove or rename it.*set matlab_stable_urls = False\.",
            c.stderr,
        )
        is not None,
        "... with an error that names the file and the fix",
    )
    ctx.expect(
        c.html("mat/ref/nwbRead.m.html") == "<html>mine</html>\n",
        "... and the user's file is not overwritten",
    )

    # a hand-written page next to the API pages (output dir "."), then removed
    hw = ctx.conf(
        ctx.path("hw"),
        matlab_src_code_project_root=str(REPOS / "matnwb"),
        matlab_apidoc_output_dir=".",
    )
    ctx.scmd("hw apidoc", "apidoc", "-c", hw, "-q")
    ctx.write("hw/notes.rst", "Notes\n=====\n\nHand-written.\n")
    text = (hw / "index.rst").read_text(encoding="utf-8")
    (hw / "index.rst").write_text(
        text + "\n.. toctree::\n\n   notes\n", encoding="utf-8"
    )
    ctx.sphinx("hw first", hw, ctx.path("hw-html"), fresh=False)
    (hw / "notes.rst").unlink()
    (hw / "index.rst").write_text(text, encoding="utf-8")
    h = ctx.sphinx("hw notes removed", hw, ctx.path("hw-html"), fresh=False)
    ctx.expect(
        (h.out / "notes.html").exists(),
        "a removed hand-written page keeps its HTML, as Sphinx does "
        "(linking-projects.rst: only pages apidoc removed are removed)",
    )


def report(build):
    """Return the summary of a build's api-check.json, or {}."""
    path = build.out / "api-check.json"
    return (
        json.loads(path.read_text(encoding="utf-8"))["summary"] if path.exists() else {}
    )


def checked(summary, kinds=None):
    """Return the number of checked objects (of ``kinds``) in an api-check summary."""
    return sum(
        n for k, n in summary.get("checked", {}).items() if kinds is None or k in kinds
    )


def findings(summary, rule):
    """Return the number of findings of ``rule`` in an api-check summary."""
    n = summary.get("findings", {}).get(rule, {})
    return n.get("error", 0) + n.get("warning", 0)


@scenario
def api_check(ctx):
    """matlab-api-check settings on matnwb: rules, ignore patterns, file
    selections (list, file, unmatched), section labels; with Markdown sidecar
    docs (the +contrib READMEs) rendered, linked and checked.
    """
    docs = apidoc_project(
        ctx,
        "matnwb",
        folder="docs",
        extensions=["sphinx.ext.autodoc", "sphinxcontrib.matlab", "myst_parser"],
        matlab_src_sidecar_suffixes=[".md"],
        exclude_patterns=["_build"],
    )
    ctx.write(
        "docs/index.rst",
        """
        matnwb
        ======

        .. toctree::

           api/index
           contrib

        * C01 :mat:sidecar:`+contrib/+tdt/README.md`
        """,
    )
    ctx.write(
        "docs/contrib.rst",
        """
        Contributions
        =============

        .. mat:autosidecar:: +contrib/+blackrock/README.md

        .. mat:autosidecar:: +contrib/no/README.md
        """,
    )
    ctx.require(
        ctx.scmd("apidoc", "apidoc", "-c", docs, "-q").returncode == 0,
        "apidoc with sidecars",
    )
    html = ctx.sphinx("html", docs, ctx.path("html"), "-n")
    ctx.expect(html.rc == 0, "html with Markdown sidecars: exit 0")
    ctx.expect(
        all(links_of(html.html("index.html"), "C").values()),
        "a :mat:sidecar: role links",
    )
    ctx.expect(
        len(html.warned(r"\+contrib/no/README.md.*\[mat\.sidecar\]")) == 1,
        "mat:autosidecar of a missing sidecar warns mat.sidecar once",
    )
    ctx.expect(
        any(
            "blackrock" in f.lower() or "Blackrock" in html.html(f)
            for f in html.files()
            if f.startswith("contrib")
        ),
        "mat:autosidecar renders the README",
    )

    def check(label, *args):
        b = ctx.sphinx(
            label, docs, ctx.path(_slug(label)), *args, builder="matlab-api-check"
        )
        summary = report(b)
        ctx.expect(b.rc in (0, 1) and summary, f"{label}: a report ({b.rc})")
        return b, summary

    _, s0 = check("default")
    ctx.expect(
        checked(s0, ("function", "class")) > 400,
        f"the default checks every file ({s0.get('checked')})",
    )
    ctx.expect(
        findings(s0, "sidecar-documented") + findings(s0, "sidecar-links") >= 0
        and "sidecar-documented" in s0.get("findings", {}),
        "the sidecar rules run",
    )
    # a dict cannot be given with -D: the rules and labels go into conf.py
    conf = docs / "conf.py"
    original = conf.read_text(encoding="utf-8")

    def with_conf(label, extra):
        conf.write_text(original + extra + "\n", encoding="utf-8")
        try:
            return check(label)
        finally:
            conf.write_text(original, encoding="utf-8")

    b, s1 = with_conf(
        "rules", "matlab_api_check_rules = {'description': 'ignore', 'inputs': 'error'}"
    )
    ctx.expect(
        findings(s1, "description") == 0 and findings(s0, "description") > 0,
        "a rule set to ignore reports nothing",
    )
    ctx.expect(
        s1["findings"].get("inputs", {}).get("error", 0) == findings(s0, "inputs")
        and (b.rc == 1) == (findings(s0, "inputs") > 0),
        "a rule set to error reports errors, and exit 1 with one",
    )
    _, s2 = check(
        "ignore patterns", "-D", "matlab_api_check_ignore_patterns=+tests/**,+types/**"
    )
    ctx.expect(
        0 < checked(s2) < checked(s0),
        f"ignore patterns check fewer objects ({checked(s2)} < {checked(s0)})",
    )
    b, s3 = check("files", "-D", "matlab_api_check_files=+io/")
    io_files = len(list((REPOS / "matnwb" / "+io").rglob("*.m")))
    n = checked(s3, ("function", "class", "script"))
    ctx.expect(
        0 < n <= io_files,
        f"a folder selection checks the files below it ({n} of {io_files})",
    )
    lst = ctx.write("changed.txt", "nwbRead.m\n\n  nwbExport.m  \n")
    _, s4 = check("files from", "-D", f"matlab_api_check_files_from={lst}")
    n = checked(s4, ("function", "class", "script"))
    ctx.expect(n == 2, f"a files_from list checks its 2 files ({s4['checked']})")
    b, _ = check("unmatched", "-D", "matlab_api_check_files=nwbRead.m,deleted.m")
    ctx.expect(
        b.rc == 1 and b.warned(r"deleted\.m"),
        "an entry that selects nothing: an error and exit 1",
    )
    b, _ = check(
        "why unmatched",
        "-D",
        "matlab_api_check_files=nwbRead.m,README.md,+nope/,docs/conf.py",
    )
    for entry in ("README.md", "+nope/", "docs/conf.py"):
        ctx.expect(
            len(b.warned(f"selection entry '{re.escape(entry)}'")) == 1,
            f"a selection entry that selects nothing ({entry}): one error "
            "that says why",
        )
    empty = ctx.write("empty.txt", "\n")
    _, se = check("empty files_from", "-D", f"matlab_api_check_files_from={empty}")
    ctx.expect(checked(se) == 0, f"an empty files_from selects nothing ({checked(se)})")
    _, sm = check(
        "ignore members",
        "-D",
        "matlab_api_check_ignore_patterns=NwbFile.m.*,+contrib/**",
    )
    ctx.expect(
        checked(sm) < checked(s0), "ignore patterns of members check fewer objects"
    )
    b, _ = check(
        "unmatched ignored",
        "-D",
        "matlab_api_check_files=nwbRead.m,deleted.m",
        "-D",
        "matlab_api_check_ignore_unmatched=1",
    )
    ctx.expect(
        not b.warned(r"deleted\.m")
        and "deleted.m" in (b.out / "api-check.txt").read_text(encoding="utf-8"),
        "with ignore_unmatched it is listed as ignored, no error",
    )
    _, s7 = with_conf(
        "labels",
        "matlab_api_check_section_labels = "
        "{'inputs': ['<built-in>', 'Input Arguments'], 'example': []}",
    )
    ctx.expect(
        findings(s7, "inputs") <= findings(s0, "inputs"),
        f"an extra inputs label finds no more missing inputs "
        f"({findings(s7, 'inputs')} <= {findings(s0, 'inputs')})",
    )
    ctx.expect(
        findings(s7, "example") >= findings(s0, "example"),
        "accepting no example label finds no fewer missing examples",
    )


EVENTS_PAGE = """
    Events
    ======

    .. mat:autoclass:: wt.RangeField
       :members:
       :show-inheritance:
       :inherited-members:
       :noindex:

    .. mat:autoevent:: wt.ProgressBar.CancelPressed
       :noindex:

    .. mat:autoapplication:: widgets/examples/WidgetsExampleApp.mlapp
       :noindex:

    * E01 :mat:event:`wt.ProgressBar.CancelPressed`
    * E02 :mat:event:`wt.abstract.BaseWidget.WidgetThemeChanged`
    * E03 :mat:event:`wt.RangeField.WidgetThemeChanged`
    * E04 :mat:app:`widgets/examples/WidgetsExampleApp.mlapp`
    """


def source_events(root):
    """``(class reference, event)`` of every public event declared below ``root``."""
    out = []
    for f in sorted(root.rglob("*.m")):
        inside = False
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            text = line.split("%")[0].strip()
            if re.match(r"events\b", text):
                # public events only: an access list, private, protected or
                # Hidden needs an option (reference/directives.rst)
                inside = not re.search(
                    r"ListenAccess\s*=\s*[?{'\"]*(\?|private|protected)|Hidden", text
                )
            elif inside and re.fullmatch(r"end\b.*", text):
                inside = False
            elif inside and (name := re.match(r"\w+", text)):
                out.append((f.relative_to(root).as_posix(), name.group()))
    return out


@scenario
def events(ctx):
    """widgets-toolbox (MathWorks), the project with classes that declare
    events and App Designer apps: every event documented with an anchor,
    inherited events, event roles, mat:autoevent and mat:autoapplication.
    """
    root = REPOS / "widgets-toolbox"
    docs = apidoc_project(
        ctx,
        "widgets-toolbox",
        folder="docs",
        matlab_inherited_members=True,
        nitpicky=True,
        autodoc_default_options={"inherited-members": True},
    )
    ctx.write(
        "docs/index.rst",
        """
        Widgets
        =======

        .. toctree::

           api/index
           events
        """,
    )
    ctx.write("docs/events.rst", EVENTS_PAGE)
    ctx.require(
        ctx.scmd("apidoc", "apidoc", "-c", docs, "-q").returncode == 0, "apidoc"
    )
    b = ctx.sphinx("html", docs, ctx.path("html"))
    ctx.expect(b.rc == 0, "html: exit 0")
    pages = "".join(
        d.decode("utf-8") for f, d in b.files().items() if f.startswith("api/")
    )
    declared = source_events(root)
    missing = [
        f"{c}.{e}"
        for c, e in declared
        if f'id="mat-{c}.{e}"' not in pages
        and f'id="mat-{c.replace("+", "%2B")}.{e}"' not in pages
    ]
    ctx.expect(
        declared and not missing,
        f"every declared event has an anchor on the API pages "
        f"({len(declared) - len(missing)} of {len(declared)}: {missing[:3]})",
    )
    ctx.expect("Events" in pages, "the class pages have an Events section")
    page = b.html("events.html")
    links = links_of(page, "E")
    ctx.expect(
        len(links) == 4 and all(links.values()),
        f"every event and app role links ({[k for k, v in links.items() if not v]})",
    )
    ctx.expect(
        "Inherited from" in page and "WidgetThemeChanged" in page,
        "an inherited event is listed with the subclass",
    )
    mine = [
        r for r in b.records if "events.rst" in r and re.search(r"\[(mat|ref)\.", r)
    ]
    ctx.expect(not mine, f"no mat.* or ref.* warning on the page ({mine[:2]})")
    api = ctx.sphinx("api-check", docs, ctx.path("api"), builder="matlab-api-check")
    hits = api.warned(r"CancelPressed")
    ctx.expect(
        len(hits) == 1,
        f"api-check: the one event without help is found once ({len(hits)})",
    )


#: file -> text of the naming-layouts project (folders and files that test
#: MATLAB's naming rules; "classdef" files get a class of the file's name)
LAYOUT = {
    "plain.m": "function plain\n% PLAIN A global function.\nend\n",
    "end.m": "function end_\nend\n",
    "+for/f.m": "function f\nend\n",
    "@C/C.m": "classdef C\n% C A class folder.\nend\n",
    "@C/method1.m": "function method1(obj)\n% METHOD1 A method file.\nend\n",
    "@C/sub/f.m": "function f\n% F In a subfolder of a class folder.\nend\n",
    "@C/sub/K.m": "classdef K\nend\n",
    "@C/D.m": "classdef D\nend\n",
    "@C/1bad.m": "function x = 1bad\nend\n",
    "@1bad/f.m": "function f\nend\n",
    "+1bad/@C/C.m": "classdef C\nend\n",
    "+1bad/private/h.m": "function h\nend\n",
    "@A/A.m": "classdef A\nend\n",
    "@A/@B/B.m": "classdef B\nend\n",
    "@A/+p/h.m": "function h\nend\n",
    "@A/+p/@B/B.m": "classdef B\nend\n",
    "private/private/g.m": "function g\nend\n",
    "+p/+1x/f.m": "function f\nend\n",
    "+p/inPkg.m": "function inPkg\n% INPKG In a namespace.\nend\n",
    "+/t.m": "function t\nend\n",
    "a" * 64 + ".m": "function x\nend\n",
    "odd/Odd.m": """classdef (Sealed = ~true, Hidden = 0x1F) Odd < handle
    % ODD A class with rare syntax.
    properties
        A@double scalar = 1  % old-style typed property
    end
    events
        Changed
        % help of Changed, on the next line
    end
    enumeration
    end
    methods
        function obj = Odd(x)
            arguments
            end
        end
    end
end
""",
    "odd/blockHelp.m": (
        "function blockHelp\n%{\nBLOCKHELP Help in a block comment.\n%}\nend\n"
    ),
    "odd/badName.m": "classdef 3x\nend\n",
    "odd/brokenClass.m": "classdef\nend\n",
}


@scenario
def naming_layouts(ctx):
    """Document a project of folder and file shapes that MATLAB's naming rules
    decide on (class folders in class folders, invalid and keyword names,
    nested private/, long names) and of rare class syntax, for R2026a,
    R2025b and R2024a: every file is documented by its path, a file MATLAB
    cannot call warns once, and the rules change with the release.
    """
    proj = ctx.path("proj")
    for rel, text in LAYOUT.items():
        ctx.write(f"proj/{rel}", text)
    docs = apidoc_project(
        ctx, "regularizeNd", folder="docs", matlab_apidoc_private=True
    )
    text = (docs / "conf.py").read_text(encoding="utf-8")
    (docs / "conf.py").write_text(
        text.replace(repr(str(REPOS / "regularizeNd")), repr(str(proj))),
        encoding="utf-8",
    )
    ctx.write("docs/index.rst", "Layouts\n=======\n\n.. toctree::\n\n   api/index\n")
    ctx.require(ctx.scmd("apidoc", "apidoc", "-c", docs).returncode == 0, "apidoc")
    builds = {}
    for version in ("R2026a", "R2025b", "R2024a"):
        b = ctx.sphinx(
            version,
            docs,
            ctx.path(f"html-{version}"),
            "-n",
            "-D",
            f"matlab_version={version}",
        )
        ctx.expect(b.rc == 0, f"{version}: exit 0 ({b.rc})")
        builds[version] = b
        per_file = {}
        for r in b.warned(r"\[mat\.not_callable\]"):
            m = re.search(r"\] (\S+) is not callable", r)
            if m:
                per_file[m.group(1)] = per_file.get(m.group(1), 0) + 1
        twice = {f: n for f, n in per_file.items() if n > 1}
        ctx.expect(not twice, f"{version}: each uncallable file warns once ({twice})")
        builds[version].uncallable = set(per_file)
    b = builds["R2026a"]
    inv = ctx.run(
        "inventory",
        [*python(), "-m", "sphinx.ext.intersphinx", str(b.out / "objects.inv")],
    ).stdout
    # a function file in a class folder is a method of the class
    methods = {"@C/method1.m", "@C/1bad.m"}
    undocumented = [
        rel
        for rel in LAYOUT
        if not rel.startswith(("private/", "+1bad/private"))
        and rel not in methods | {"odd/badName.m"}
        and rel not in inv
    ]
    ctx.expect(
        not undocumented, f"every public file is in the inventory ({undocumented[:5]})"
    )
    new_rule = "@C/sub/f.m"
    ctx.expect(
        new_rule in builds["R2026a"].uncallable
        and new_rule not in builds["R2025b"].uncallable,
        "a function in a subfolder of a class folder: not callable from "
        "R2026a on, callable before",
    )
    long = "a" * 64 + ".m"
    ctx.expect(
        long in builds["R2024a"].uncallable,
        "a 64-character file name is not callable in R2024a (63 max)",
    )
    pages = "".join(d.decode("utf-8") for d in b.files().values())
    for needle in ("Changed", "help of Changed"):
        ctx.expect(needle in pages, f"rare class syntax: {needle!r} is documented")
    # help is the first run of % lines, so a block comment gives "{"
    # (user-guide/help-text.rst, as MATLAB's help)
    ctx.expect(
        "Help in a block comment" not in pages,
        "a %{ %} block comment is not help, as in MATLAB",
    )
    ctx.expect(
        len(b.warned(r"badName\.m")) == 1 and len(b.warned(r"brokenClass\.m")) == 1,
        "a classdef named unlike its file, and an empty classdef line: "
        "one warning each",
    )
    ctx.expect(
        not ref_warnings(b),
        f"-n: no broken reference ({ref_warnings(b)[:2]})",
    )


PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)


def hrefs(html):
    """Return link text marker (``LNKn``) -> href of the links on a page."""
    out = {}
    link = re.compile(r'<a [^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL)
    for href, text in link.findall(html):
        m = re.search(r"LNK\d+", text)
        if m:
            out[m.group()] = href
    return out


@scenario
def help_links(ctx):
    """Relative links, images, downloads and includes in help text and in
    reST and Markdown sidecar docs (user-guide/help-text.rst, sidecars.rst):
    a code file links to its API entry, any other file is a download, an
    image is copied, a missing file is left as written.
    """
    proj = ctx.copy_project("regularizeNd", "proj")
    ctx.write("proj/sub/bar.m", "function bar\n% BAR The target of links.\nend\n")
    ctx.write("proj/sub/data.csv", "a,b\n1,2\n")
    (proj / "sub" / "fig.png").write_bytes(PNG)
    ctx.write(
        "proj/sub/withLinks.m",
        """
        function withLinks
        % WITHLINKS Help with relative paths.
        %
        % .. image:: fig.png
        %
        % The `LNK1 <bar.m>`_, the `LNK2 <data.csv>`_, the `LNK3 <nope.csv>`_
        % and :download:`LNK4 <data.csv>`.
        end
        """,
    )
    ctx.write(
        "proj/sub/notes.rst",
        """
        Notes
        =====

        Usage
        -----

        The `LNK5 <bar.m>`_ and the `LNK6 <data.csv>`_.

        .. image:: fig.png

        .. include:: inc.txt
        """,
    )
    ctx.write("proj/sub/inc.txt", "Included: the `LNK7 <bar.m>`_.\n")
    ctx.write(
        "proj/sub/guide.md",
        """
        # Guide

        The [LNK8](data.csv), the [LNK9](bar.m), [LNK10](notes.rst),
        [LNK11](notes.rst#usage) and ![a figure](fig.png).
        """,
    )
    docs = apidoc_project(
        ctx,
        "regularizeNd",
        folder="docs",
        extensions=["sphinx.ext.autodoc", "sphinxcontrib.matlab", "myst_parser"],
        # regularizeNd's own Sphinx source (docs/conf.py) is not sidecar docs
        matlab_src_sidecar_suffixes=[".md", ".rst"],
    )
    text = (docs / "conf.py").read_text(encoding="utf-8")
    (docs / "conf.py").write_text(
        text.replace(repr(str(REPOS / "regularizeNd")), repr(str(proj))),
        encoding="utf-8",
    )
    ctx.write("docs/index.rst", "Links\n=====\n\n.. toctree::\n\n   api/index\n")
    ctx.require(
        ctx.scmd("apidoc", "apidoc", "-c", docs, "-q").returncode == 0, "apidoc"
    )
    b = ctx.sphinx("html", docs, ctx.path("html"), "-n")
    ctx.expect(b.rc == 0, f"html: exit 0 ({b.rc})")
    links = {}
    for page in b.files():
        links |= hrefs(b.html(page))
    api = ("mat/ref/sub/bar.m", "#mat-sub/bar.m")

    def check(key, what, ok, bug=None):
        ctx.expect(
            ok(links.get(key) or ""), f"{key} {what} ({links.get(key)})", bug=bug
        )

    check(
        "LNK1",
        "help: a code file links to its API entry",
        lambda h: any(a in h for a in api),
    )
    check("LNK2", "help: another file is a download", lambda h: "_downloads/" in h)
    check("LNK3", "help: a missing file is left as written", lambda h: h == "nope.csv")
    check("LNK4", "help: :download: is a download", lambda h: "_downloads/" in h)
    check(
        "LNK5",
        "reST sidecar: a code file links to its API entry",
        lambda h: any(a in h for a in api),
    )
    check(
        "LNK6", "reST sidecar: another file is a download", lambda h: "_downloads/" in h
    )
    check(
        "LNK7",
        "a file included by a sidecar resolves its links too",
        lambda h: any(a in h for a in api),
    )
    check(
        "LNK8", "Markdown sidecar: a file is a download", lambda h: "_downloads/" in h
    )
    check(
        "LNK9",
        "Markdown sidecar: a code file links to its API entry",
        lambda h: any(a in h for a in api),
    )
    check(
        "LNK10",
        "Markdown sidecar: a sidecar links to its document",
        lambda h: "notes" in h,
    )
    check(
        "LNK11",
        "Markdown sidecar: an anchor goes to the section",
        lambda h: h.endswith("#usage"),
    )
    images = list((b.out / "_images").glob("fig*.png"))
    ctx.expect(images, "the images are copied")
    pages = "".join(b.html(f) for f in b.files())
    ctx.expect(
        pages.count("_images/fig") >= 3,
        f"each image is shown ({pages.count('_images/fig')} of 3)",
    )
    ctx.expect(
        not b.warned(r"withLinks|notes\.rst|guide\.md|inc\.txt"),
        f"no warning ({b.warned('withLinks|notes|guide|inc')[:2]})",
    )


@scenario
def quickstart_detect(ctx):
    """Run scmd quickstart on what it detects and on how it fails: a
    matlab.toml project path (valid, unreadable, no folders, outside the
    root), a broken .gitmodules, help headings that become napoleon sections
    (matnwb), a bad reply typed and asked again, make = uv without uv, a
    pyproject.toml uv cannot edit, -n on a dirty tree.
    """
    # a matlab.toml project path: the code folders off the path are suggested
    a = clone(ctx, "matlab2tikz", "a")
    (a / "matlab.toml").write_text(
        '[project]\nstartup-files = ["src/startup.m"]\n\n[folders]\npath = ["src"]\n'
    )
    commit_all(a)
    q = ctx.scmd("matlab.toml", "quickstart", a, "-q", cwd=a)
    conf = (
        (a / "docs" / "conf.py").read_text(encoding="utf-8")
        if q.returncode == 0
        else ""
    )
    ctx.expect(
        q.returncode == 0 and re.search(r"#.*test", conf) is not None,
        "matlab.toml: a code folder off the MATLAB path is a commented-out "
        "exclusion in conf.py",
    )
    for label, text in (
        ("unreadable", "[folders\n"),
        ("no folders", "[folders]\n"),
        ("outside", '[folders]\npath = ["../x"]\n'),
    ):
        c = clone(ctx, "matlab2tikz", _slug(label))
        (c / "matlab.toml").write_text(text)
        commit_all(c)
        q = ctx.scmd(f"matlab.toml {label}", "quickstart", c, "-q", "-n", cwd=c)
        ctx.expect(
            q.returncode == 0 and "matlab.toml" in q.stdout,
            f"matlab.toml {label}: exit 0, the report names it",
        )
    # a .gitmodules that cannot be read gives no exclusions, no failure
    g = clone(ctx, "matlab2tikz", "gitmodules")
    (g / ".gitmodules").write_text('[submodule "x"\n\tpath = ext\n')
    commit_all(g)
    q = ctx.scmd(".gitmodules", "quickstart", g, "-q", "-n", cwd=g)
    ctx.expect(q.returncode == 0, f"a broken .gitmodules: exit 0 ({q.returncode})")

    # help headings: matnwb's "Syntax:", "Input Arguments:" ... become sections
    n = clone(ctx, "matnwb", "nwb")
    # matnwb's docs/ is in use: the folder prompt has no default
    q = ctx.scmd("headings", "quickstart", n, stdin="sphinx-docs\n" + "\n" * 40, cwd=n)
    conf = (
        (n / "sphinx-docs" / "conf.py").read_text(encoding="utf-8")
        if q.returncode == 0
        else ""
    )
    ctx.expect(
        q.returncode == 0 and "napoleon_custom_sections" in conf,
        "help headings in 10 or more files become napoleon sections",
    )
    b = ctx.sphinx("nwb html", n / "sphinx-docs", ctx.path("nwb-html"))
    ctx.expect(b.rc == 0, "matnwb's quickstart docs build")

    # a bad reply is asked again
    r = clone(ctx, "matlab2tikz", "reask")
    q = ctx.scmd(
        "bad reply", "quickstart", r, cwd=r, stdin="\n\n\nR2020c\n" + "\n" * 40
    )
    ctx.expect(
        q.returncode == 0 and q.stdout.count("R2020c") + q.stderr.count("R2020c") >= 1,
        "a bad release typed is reported and asked again",
    )

    # make = uv in a project without uv
    m = clone(ctx, "matlab2tikz", "make-uv")
    answers = ctx.write("uv.toml", 'make = "uv"\n')
    q = ctx.scmd("make uv", "quickstart", m, "-q", "-a", answers, cwd=m)
    ctx.expect(
        q.returncode == 0
        and "uv run" in (m / "docs" / "Makefile").read_text(encoding="utf-8"),
        "make = uv: the make files run sphinx-build through uv",
    )
    # uv add fails: exit 1, nothing half-written is left unexplained
    u = clone(ctx, "matlab2tikz", "uv-fails")
    (u / "pyproject.toml").write_text(
        "[project]\nname = 'x'\n[tool.uv]\ndev-dependencies = 5\n"
    )
    commit_all(u)
    q = ctx.scmd("uv add fails", "quickstart", u, "-q", cwd=u)
    ctx.expect(
        q.returncode == 1 and "uv" in q.stderr,
        f"uv add failing: exit 1 naming uv ({q.returncode})",
    )
    # -n on a dirty tree writes nothing and does not stop
    d = clone(ctx, "matlab2tikz", "dirty")
    with open(d / ".gitignore", "a", encoding="utf-8") as fh:
        fh.write("x/\n")
    q = ctx.scmd("dry run dirty", "quickstart", d, "-n", "-q", cwd=d)
    ctx.expect(
        q.returncode in (0, 2) and not (d / "docs").exists(),
        f"-n on a dirty tree writes nothing ({q.returncode})",
    )


def main():
    """Run the selected scenarios and print the summary."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("names", nargs="*", help="run the scenarios named so")
    parser.add_argument(
        "--out", type=Path, default=P.HERE / "runs" / "scenarios", help="%(default)s"
    )
    parser.add_argument("--coverage", action="store_true")
    parser.add_argument("--list", action="store_true", help="list the scenarios")
    args = parser.parse_args()
    if args.list:
        for name, func in SCENARIOS.items():
            print(f"{name:24} {(func.__doc__ or '').strip().splitlines()[0]}")
        return
    unknown = set(args.names) - set(SCENARIOS)
    if unknown:
        sys.exit(f"unknown scenarios: {', '.join(sorted(unknown))} (see --list)")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    rcfile = G.start_coverage(out / "coverage") if args.coverage else None
    results = {"environment": G.environment(), "scenarios": {}}
    for name, func in SCENARIOS.items():
        if args.names and name not in args.names:
            continue
        print(f"== {name}", flush=True)
        ctx = Ctx(name, out / name)
        start = time.perf_counter()
        error = None
        try:
            func(ctx)
        except Failed as err:
            error = f"stopped: {err}"
        except Exception:
            error = traceback.format_exc()
            print(error, flush=True)
        results["scenarios"][name] = {
            "wall_s": round(time.perf_counter() - start, 1),
            "error": error,
            "checks": ctx.checks,
        }
        (out / "results.json").write_text(
            json.dumps(results, indent=1) + "\n", encoding="utf-8"
        )
    if rcfile:
        G.report_coverage(rcfile)
    summary(results["scenarios"], out)


def summary(rows, out):
    """Print the counts and the problems; exit 1 on one."""
    problems, known, fixed = [], [], []
    for name, row in rows.items():
        if row["error"]:
            problems.append(f"{name}: {row['error'].strip().splitlines()[-1]}")
        for c in row["checks"]:
            if c["status"] == "FAIL":
                problems.append(f"{name}: {c['what']}")
            elif c["status"] == "known":
                known.append(f"{name}: [{c['bug']}] {c['what']}")
            elif c["status"] == "FIXED?":
                fixed.append(f"{name}: [{c['bug']}] {c['what']}")
    checks = sum(len(r["checks"]) for r in rows.values())
    print(
        f"\n{len(rows)} scenarios, {checks} checks: {len(problems)} problems, "
        f"{len(known)} known bugs, {len(fixed)} marked bugs that passed; "
        f"results in {out}"
    )
    for title, items in (
        ("Problems", problems),
        ("Known bugs", known),
        ("Marked as a bug but passed (remove the mark?)", fixed),
    ):
        if items:
            print(f"{title}:")
            for item in items:
                print(f"  {item}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
