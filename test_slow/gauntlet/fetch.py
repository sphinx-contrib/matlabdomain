"""Fetch or update the gauntlet's checkouts (../repos/<name>) and write the lock.

Usage, from anywhere:
  python test_slow/gauntlet/fetch.py [NAME ...] [--update] [--reset] [--projects FILE]

For each enabled project in the list (NAME arguments keep the projects whose
name contains one of them), the target commit is the list's ``commit``, else
the lock file's, else the checkout's HEAD, else (a new checkout) the default
branch HEAD. ``--update`` moves the projects without a ``commit`` to the
newest default branch HEAD.

- A missing checkout is fetched at the target (depth 1, no history).
- An existing checkout with a clean tree is moved to the target. With local
  changes it is left alone and reported; ``--reset`` discards the changes
  (``git reset --hard`` and ``git clean -fd``).
- With ``submodules = true`` the submodules are fetched too (depth 1).

Writes the checked-out commit of each project to the lock file
(projects.lock.toml). Exit 1 when a project failed or was skipped.
"""

import argparse
import subprocess
import sys

import projects as P


class Skip(Exception):
    pass


def is_shallow(repo):
    return P.git(repo, "rev-parse", "--is-shallow-repository") == "true"


def fetch(repo, ref, shallow):
    """Fetch a SHA, tag or the remote HEAD and return its commit."""
    try:
        P.git(
            repo, "fetch", "-q", *(["--depth", "1"] if shallow else []), "origin", ref
        )
        return P.resolve(repo, "FETCH_HEAD")
    except subprocess.CalledProcessError:
        # a short SHA cannot be fetched by itself: fetch the history and look it up
        unshallow = ["--unshallow"] if is_shallow(repo) else []
        P.git(repo, "fetch", "-q", *unshallow, "--tags", "origin")
        commit = P.resolve(repo, ref)
        if commit is None:
            url = P.git(repo, "remote", "get-url", "origin")
            raise Skip(f"{ref} is not in {url}") from None
        return commit


def init(project):
    repo = project.checkout
    repo.mkdir(parents=True, exist_ok=True)
    P.git(repo, "init", "-q")
    P.git(repo, "config", "core.longpaths", "true")
    # else Git for Windows writes symlinks as text files (matpower has 807)
    P.git(repo, "config", "core.symlinks", "true")
    P.git(repo, "remote", "add", "origin", project.url)


def sync(project, target, args):
    repo = project.checkout
    if not (repo / ".git").exists():
        init(project)
    url = P.git(repo, "remote", "get-url", "origin")
    if url != project.url:
        raise Skip(f"its origin is {url}, not {project.url}")
    head = P.resolve(repo, "HEAD")
    if head is None:  # a new checkout, or an earlier fetch failed
        commit = fetch(repo, target or "HEAD", shallow=True)
        P.git(repo, "checkout", "-q", "--detach", commit)
        return commit, "fetched"
    if args.update and not project.commit:
        commit = fetch(repo, "HEAD", is_shallow(repo))
    elif target:
        commit = P.resolve(repo, target) or fetch(repo, target, is_shallow(repo))
    else:
        commit = head
    changed = P.changed_files(repo)
    notes = []
    if changed and args.reset:
        P.git(repo, "reset", "-q", "--hard")
        P.git(repo, "clean", "-q", "-fd")
        notes.append(f"discarded {changed} changed files")
        changed = 0
    if commit != head:
        if changed:
            raise Skip(
                f"at {head[:12]}, not {(commit or '')[:12]}: {changed} changed files "
                "(--reset discards them)"
            )
        P.git(repo, "checkout", "-q", "--detach", commit)
        notes.append(f"moved from {head[:12]}")
    elif changed:
        notes.append(f"WARNING: {changed} changed files (--reset discards them)")
    return commit, "; ".join(notes) or "unchanged"


def main():
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument(
        "names", nargs="*", help="keep projects whose name contains one"
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="move unpinned projects to the newest commit",
    )
    parser.add_argument(
        "--reset", action="store_true", help="discard local changes in the checkouts"
    )
    parser.add_argument(
        "--projects", default=P.LIST, help="the project list (default: %(default)s)"
    )
    args = parser.parse_args()

    listed = P.load(args.projects)
    lock = P.load_lock(args.projects)
    failed = 0
    for project in listed:
        if not project.enabled or (
            args.names and not any(n in project.name for n in args.names)
        ):
            continue
        try:
            commit, note = sync(
                project, project.commit or P.locked_commit(project, lock), args
            )
            if project.submodules:
                P.git(
                    project.checkout,
                    "submodule",
                    "update",
                    "-q",
                    "--init",
                    "--recursive",
                    "--depth",
                    "1",
                )
            lock[project.name] = {"commit": commit, "url": project.url}
            print(f"{project.name}: {(commit or '')[:12]} {note}", flush=True)
        except Skip as err:
            failed += 1
            print(f"{project.name}: SKIPPED: {err}", flush=True)
        except subprocess.CalledProcessError as err:
            failed += 1
            print(f"{project.name}: FAILED: {err.stderr.strip()}", flush=True)
    names = {p.name for p in listed}
    P.write_lock({n: e for n, e in lock.items() if n in names}, args.projects)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
