"""sphinxcontrib.matlab_skills._cli.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Command line of ``scmd skills``: ``list`` prints the agent skills that ship
with the package, ``install`` copies them into a project's skill folder.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import textwrap
from importlib import resources
from pathlib import Path

from ..matlab_apidoc._cli import _version

#: the folder GitHub Copilot reads a project's skills from
DEFAULT_DEST = ".github/skills"
#: the package that holds the skill folders
PACKAGE = __name__.rpartition(".")[0]
#: exit status when a skill folder exists and --force is not given
EXISTS = 1
#: exit status for usage errors (as argparse)
USAGE_ERROR = 2


def _front_matter(text):
    """Return the ``key: value`` lines of a ``SKILL.md`` header."""
    lines = text.splitlines()
    fields = {}
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            key, sep, value = line.partition(":")
            if sep:
                fields[key.strip()] = value.strip()
    return fields


def skills():
    """Return ``{name: description}`` of the skills in the package, by name."""
    found = {}
    for entry in resources.files(PACKAGE).iterdir():
        skill = entry / "SKILL.md"
        if entry.is_dir() and skill.is_file():
            header = _front_matter(skill.read_text(encoding="utf-8"))
            found[entry.name] = header.get("description", "")
    return dict(sorted(found.items()))


def get_parser(prog="scmd skills"):
    parser = argparse.ArgumentParser(
        prog=prog,
        allow_abbrev=False,
        description=(
            "List the agent skills that ship with sphinxcontrib-matlabdomain, "
            "or copy them into a project."
        ),
        epilog=(
            "Agent tools read a project's skills from their own folder: GitHub "
            "Copilot from .github/skills, Claude from .claude/skills, Codex "
            "from .agents/skills."
        ),
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {_version()}"
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    commands.add_parser(
        "list",
        allow_abbrev=False,
        help="print the name and description of each skill",
        description="Print the name and description of each skill.",
    )
    install = commands.add_parser(
        "install",
        allow_abbrev=False,
        help="copy skills into a project",
        description=(
            "Copy skill folders into DIR, each to DIR/NAME. It copies nothing "
            "when one of these folders exists, unless --force."
        ),
    )
    install.add_argument(
        "names", nargs="*", metavar="NAME", help="the skills to copy (default: all)"
    )
    install.add_argument(
        "-d",
        "--dest",
        default=DEFAULT_DEST,
        metavar="DIR",
        help=f"the project's skill folder (default: {DEFAULT_DEST})",
    )
    install.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="replace skill folders that exist",
    )
    return parser


def _list(available):
    for name, description in available.items():
        print(name)
        print(
            textwrap.fill(
                description, width=79, initial_indent="    ", subsequent_indent="    "
            )
        )


def _install(parser, available, args):
    unknown = [name for name in args.names if name not in available]
    if unknown:
        print(
            f"{parser.prog} install: error: unknown skill {', '.join(unknown)} "
            f"(the skills: {', '.join(available)})",
            file=sys.stderr,
        )
        return USAGE_ERROR
    dest = Path(args.dest)
    names = list(dict.fromkeys(args.names)) or list(available)
    existing = [dest / name for name in names if (dest / name).exists()]
    if existing and not args.force:
        for path in existing:
            print(f"{parser.prog} install: error: {path} exists", file=sys.stderr)
        print("Nothing copied; --force replaces these folders.", file=sys.stderr)
        return EXISTS
    with resources.as_file(resources.files(PACKAGE)) as root:
        for name in names:
            target = dest / name
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            elif target.exists() or target.is_symlink():
                target.unlink()
            shutil.copytree(
                root / name, target, ignore=shutil.ignore_patterns("__pycache__")
            )
            print(f"Installed {name} in {target}.")
    return 0


def main(argv=None, *, prog="scmd skills"):
    """Run ``scmd skills``; return the exit status.

    0 on success; 1 if a skill folder exists and ``--force`` is not given;
    2 for an unknown skill name (argparse exits with 2 itself for usage
    errors).
    """
    parser = get_parser(prog)
    args = parser.parse_args(argv)
    available = skills()
    if args.command == "list":
        _list(available)
        return 0
    return _install(parser, available, args)
