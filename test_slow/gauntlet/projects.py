"""The gauntlet's project list (projects.toml) and lock file (projects.lock.toml)."""

import json
import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPOS = HERE.parent / "repos"
LIST = HERE / "projects.toml"
_KEYS = {"url", "commit", "root", "submodules", "enabled", "parallel_may_differ"}
# names are folder names and bare TOML keys; refs and URLs must not look like options
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
_REF = re.compile(r"[A-Za-z0-9][\w./-]*")


@dataclass(frozen=True)
class Project:
    name: str
    url: str
    commit: str | None = None
    root: str = ""
    submodules: bool = False
    enabled: bool = True
    parallel_may_differ: bool = False

    @property
    def checkout(self) -> Path:
        return REPOS / self.name

    @property
    def source(self) -> Path:
        return self.checkout / self.root


def load(path=LIST):
    path = Path(path)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if set(data) - {"projects"}:
        raise ValueError(f"{path}: only [projects.<name>] tables are allowed")
    projects = []
    for name, entry in data.get("projects", {}).items():
        where = f"{path}: [projects.{name}]"
        if not _NAME.fullmatch(name):
            raise ValueError(f"{where}: use letters, digits, - and _ in the name")
        if set(entry) - _KEYS:
            raise ValueError(f"{where}: unknown keys {sorted(set(entry) - _KEYS)}")
        if not entry.get("url") or entry["url"].startswith("-"):
            raise ValueError(f"{where}: needs a url")
        entry = {**entry, "commit": entry.get("commit") or None}
        if entry["commit"] and not _REF.fullmatch(entry["commit"]):
            raise ValueError(f"{where}: commit {entry['commit']!r} is not a SHA or tag")
        root = Path(entry.get("root", ""))
        if root.is_absolute() or ".." in root.parts:
            raise ValueError(f"{where}: root must be a folder inside the checkout")
        projects.append(Project(name=name, **entry))
    return projects


def lock_file(path=LIST):
    path = Path(path)
    return path.with_name(f"{path.stem}.lock.toml")


def load_lock(path=LIST):
    file = lock_file(path)
    if not file.exists():
        return {}
    return tomllib.loads(file.read_text(encoding="utf-8")).get("projects", {})


def write_lock(lock, path=LIST):
    lines = [
        "# Written by fetch.py: the commit of each checkout. Commit this file to rerun",
        "# the same commits elsewhere; fetch.py --update moves the unpinned projects.",
        "",
    ]
    # sorted as the pretty-format-toml pre-commit hook sorts: it leaves the file alone
    for name in sorted(lock):
        lines += [
            f"[projects.{name}]",
            f"commit = {json.dumps(lock[name]['commit'])}",
            f"url = {json.dumps(lock[name]['url'])}",
            "",
        ]
    lock_file(path).write_text(
        "\n".join(lines[:-1]) + "\n", encoding="utf-8", newline="\n"
    )


def locked_commit(project, lock):
    """Return the lock file's commit for the project if locked with the same URL."""
    entry = lock.get(project.name)
    return entry["commit"] if entry and entry.get("url") == project.url else None


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    ).stdout.strip()


def resolve(repo, ref):
    """Return the full SHA of a commit, tag or FETCH_HEAD in the checkout, or None."""
    proc = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "rev-parse",
            "--verify",
            "--quiet",
            f"{ref}^{{commit}}",
        ],
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def changed_files(repo):
    return len(git(repo, "status", "--porcelain").splitlines())
