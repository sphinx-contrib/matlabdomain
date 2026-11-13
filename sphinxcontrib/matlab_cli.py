"""Unified command line for sphinxcontrib-matlabdomain."""

import argparse
import os
import sys

from .matlab_apidoc import _cli as apidoc
from .matlab_quickstart import _cli as quickstart
from .matlab_skills import _cli as skills

COMMANDS = {
    "apidoc": (apidoc.main, "Generate API pages."),
    "quickstart": (quickstart.main, "Set up documentation."),
    "skills": (skills.main, "List or install the agent skills."),
}


def main(argv=None):
    """Run ``scmd <command> ...`` (``apidoc``, ``quickstart`` or ``skills``) with the
    arguments ``argv`` (default: the command line); return the exit code.
    """
    prog = os.path.basename(sys.argv[0]) if argv is None else "scmd"
    parser = argparse.ArgumentParser(prog=prog, allow_abbrev=False)
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {apidoc._version()}"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name, (_, help_text) in COMMANDS.items():
        commands.add_parser(name, add_help=False, help=help_text)
    args, remaining = parser.parse_known_args(argv)
    return COMMANDS[args.command][0](remaining, prog=f"{prog} {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
