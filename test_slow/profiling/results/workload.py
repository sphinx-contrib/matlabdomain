"""Run ``profile_build.main()`` against a chosen code root; print ENV/RESULT JSON lines.

Usage (run with the interpreter under test)::

    python workload.py --env-only [CODE_ROOT]
    python workload.py CODE_ROOT PROF_OUT [--old-row-getter]

CODE_ROOT is the repository whose ``sphinxcontrib`` package is imported (prepended
to the ``sphinxcontrib`` namespace path so other ``sphinxcontrib.*`` packages keep
working). ``--old-row-getter`` restores the pre-fix ``point.row`` access.
"""

import argparse
import importlib.metadata as md
import json
import pathlib
import platform
import runpy
import subprocess
import sys
import sysconfig

HARNESS = pathlib.Path(__file__).resolve().parent.parent / "profile_build.py"

ap = argparse.ArgumentParser()
ap.add_argument("code_root", nargs="?")
ap.add_argument("prof_out", nargs="?")
ap.add_argument("--env-only", action="store_true")
ap.add_argument("--old-row-getter", action="store_true")
args = ap.parse_args()

import sphinxcontrib  # noqa: E402

if args.code_root:
    pkg = pathlib.Path(args.code_root).resolve() / "sphinxcontrib"
    rest = [p for p in sphinxcontrib.__path__ if pathlib.Path(p).resolve() != pkg]
    sphinxcontrib.__path__ = [str(pkg), *rest]

import sphinxcontrib.mat_tree_sitter_parser as tsp  # noqa: E402
import sphinxcontrib.mat_types as mt  # noqa: E402

if args.old_row_getter:
    tsp.get_row = lambda point: point.row


def _git(root, *cmd):
    out = subprocess.run(["git", "-C", str(root), *cmd], capture_output=True, text=True)
    return out.stdout.strip()


code_root = pathlib.Path(mt.__file__).resolve().parent.parent


def _ver(dist):
    try:
        return md.version(dist)
    except md.PackageNotFoundError:
        return None


env = {
    "python": platform.python_version(),
    "executable": sys.executable,
    "py_gil_disabled_build": bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
    "gil_enabled_at_runtime": getattr(sys, "_is_gil_enabled", lambda: True)(),
    "tree_sitter": _ver("tree-sitter"),
    "tree_sitter_matlab": _ver("tree-sitter-matlab"),
    "sphinx": _ver("sphinx"),
    "mat_types": mt.__file__,
    "code_rev": _git(code_root, "rev-parse", "HEAD"),
    "code_dirty_files": _git(
        code_root, "status", "--porcelain", "--", "sphinxcontrib"
    ).splitlines(),
    "old_row_getter": args.old_row_getter,
}
print("ENV " + json.dumps(env), flush=True)
if args.env_only:
    sys.exit(0)

ns = runpy.run_path(str(HARNESS))
g = ns["main"].__globals__
g["PROFILE_OUT"] = pathlib.Path(args.prof_out).resolve()
sys.argv = [str(HARNESS)]
ns["main"]()
print("RESULT " + json.dumps({"ok": g["_ok"], "failures": g["_failures"]}), flush=True)
