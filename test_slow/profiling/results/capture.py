"""Phase 1 evidence driver: run a command, record log + JSON metadata in this folder.

Usage::

    python capture.py LABEL [--probe PYTHON] -- CMD [ARGS...]
    python capture.py --summarize

Runs CMD from the ``matlabdomain`` checkout (faulthandler on, PYTHONPATH unset), writes
``LABEL.log`` (stdout+stderr) and ``LABEL.json`` (command, host, interpreter and
dependency versions, fixture revision, return code, wall time, parsed harness
summary, and whether the ``.prof`` named in the log loads with ``pstats``).
Environment details come from an ``ENV`` line printed by ``workload.py``; for
commands that do not print one, pass ``--probe PYTHON`` to query that interpreter.
``--summarize`` collects every ``*.json`` with a ``label`` into ``summary.json``.
"""

import datetime
import json
import os
import pathlib
import platform
import pstats
import re
import signal
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
FIXTURE = REPO / "test_slow" / "repos" / "vhlab-toolbox-matlab"


def _git(*cmd):
    return subprocess.run(
        ["git", "-C", str(FIXTURE), *cmd], capture_output=True, text=True
    ).stdout.strip()


def _cpu():
    for line in pathlib.Path("/proc/cpuinfo").read_text().splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return platform.processor()


def _json_line(text, tag):
    for line in text.splitlines():
        if line.startswith(tag + " "):
            return json.loads(line[len(tag) + 1 :])
    return None


def _harness(text):
    out = {}
    for key, pat in {
        "parsed_ok": r"^Parsed OK : (\d+)",
        "failed": r"^Failed    : (\d+)",
        "harness_wall_s": r"^Wall time : ([\d.]+)s",
    }.items():
        m = re.search(pat, text, re.MULTILINE)
        out[key] = (float if key.endswith("_s") else int)(m.group(1)) if m else None
    out["failures"] = re.findall(r"^  - (.+)\n\s+(.+)$", text, re.MULTILINE)
    return out


def _profile(text):
    m = re.search(r"^Profile   : (.+)$", text, re.MULTILINE)
    if not m:
        return None
    path = (REPO / m.group(1).strip()).resolve()
    info: dict = {
        "path": str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path)
    }
    try:
        st = pstats.Stats(str(path))
        info.update(
            loads=True,
            total_calls=getattr(st, "total_calls", 0),
            total_tt_s=round(getattr(st, "total_tt", 0.0), 3),
        )
    except Exception as exc:
        info.update(loads=False, error=f"{type(exc).__name__}: {exc}")
    return info


def capture(label, cmd, probe):
    # An inherited PYTHONPATH with an empty entry puts the checkout on sys.path and
    # shadows the sphinxcontrib namespace, so children run without it.
    env = dict(os.environ, PYTHONFAULTHANDLER="1")
    inherited_pythonpath = env.pop("PYTHONPATH", None)
    start = time.perf_counter()
    proc = subprocess.run(cmd, cwd=REPO, env=env, capture_output=True, text=True)
    wall = time.perf_counter() - start
    text = proc.stdout + proc.stderr
    (HERE / f"{label}.log").write_text(text)
    run_env = _json_line(text, "ENV")
    if run_env is None and probe:
        p = subprocess.run(
            [probe, str(HERE / "workload.py"), "--env-only"],
            cwd=REPO,
            env=env,
            capture_output=True,
            text=True,
        )
        run_env = _json_line(p.stdout, "ENV")
    rc = proc.returncode
    sig = -rc if rc < 0 else (rc - 128 if rc > 128 else None)
    record = {
        "label": label,
        "timestamp": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "cwd": str(REPO),
        "command": cmd,
        "env_overrides": {"PYTHONFAULTHANDLER": "1", "PYTHONPATH": "<unset>"},
        "inherited_pythonpath": inherited_pythonpath,
        "host": {
            "platform": platform.platform(),
            "cpu": _cpu(),
            "cpu_count": os.cpu_count(),
        },
        "env": run_env,
        "fixture": {
            "path": str(FIXTURE.relative_to(REPO)),
            "url": _git("remote", "get-url", "origin"),
            "rev": _git("rev-parse", "HEAD"),
            "dirty": bool(_git("status", "--porcelain")),
            "m_files": sum(1 for _ in FIXTURE.rglob("*.m")),
        },
        "returncode": rc,
        "signal": signal.Signals(sig).name
        if sig and sig in signal.Signals._value2member_map_
        else None,
        "wall_s": round(wall, 2),
        "harness": _harness(text),
        "profile": _profile(text),
    }
    (HERE / f"{label}.json").write_text(json.dumps(record, indent=1) + "\n")
    h = record["harness"]
    print(
        f"{label}: rc={rc} signal={record['signal']} wall={wall:.2f}s "
        f"ok={h['parsed_ok']} failed={h['failed']}"
    )


def summarize():
    rows = []
    for f in sorted(HERE.glob("*.json")):
        d = json.loads(f.read_text())
        if not isinstance(d, dict) or "label" not in d or f.name == "summary.json":
            continue
        e = d.get("env") or {}
        rows.append(
            {
                "label": d["label"],
                "python": e.get("python"),
                "free_threaded": e.get("py_gil_disabled_build"),
                "tree_sitter": e.get("tree_sitter"),
                "tree_sitter_matlab": e.get("tree_sitter_matlab"),
                "code_rev": e.get("code_rev"),
                "code_dirty": bool(e.get("code_dirty_files")),
                "old_row_getter": e.get("old_row_getter"),
                "returncode": d["returncode"],
                "signal": d["signal"],
                "wall_s": d["wall_s"],
                "harness_wall_s": d["harness"]["harness_wall_s"],
                "parsed_ok": d["harness"]["parsed_ok"],
                "failed": d["harness"]["failed"],
                "profile_loads": (d["profile"] or {}).get("loads"),
            }
        )
    (HERE / "summary.json").write_text(json.dumps(rows, indent=1) + "\n")
    for r in rows:
        print(r)


if __name__ == "__main__":
    if sys.argv[1:] == ["--summarize"]:
        summarize()
    else:
        sep = sys.argv.index("--")
        opts, cmd = sys.argv[1:sep], sys.argv[sep + 1 :]
        probe = opts[opts.index("--probe") + 1] if "--probe" in opts else None
        capture(opts[0], cmd, probe)
