"""Unified command line for sphinxcontrib-matlabdomain."""

import argparse
import os
import sys

from .matlab_apidoc import _cli as apidoc
from .matlab_quickstart import _cli as quickstart


def main(argv=None):
    prog = os.path.basename(sys.argv[0]) if argv is None else "scmd"
    parser = argparse.ArgumentParser(prog=prog, allow_abbrev=False)
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {apidoc._version()}"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("apidoc", add_help=False, help="Generate API pages.")
    commands.add_parser("quickstart", add_help=False, help="Set up documentation.")
    args, remaining = parser.parse_known_args(argv)
    return {"apidoc": apidoc.main, "quickstart": quickstart.main}[args.command](
        remaining, prog=f"{prog} {args.command}"
    )
