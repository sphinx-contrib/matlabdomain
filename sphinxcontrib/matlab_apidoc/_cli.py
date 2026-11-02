"""sphinxcontrib.matlab_apidoc._cli.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Command line of ``sphinx-matlab-apidoc`` (plan.md Section 2.8). With
``-c DIR`` the settings come from ``DIR/conf.py``; flags override them.
"""

from __future__ import annotations

import argparse
import contextlib
import logging
import os
import sys
import time

from sphinx.config import Config
from sphinx.errors import ConfigError
from sphinx.util.tags import Tags

from .. import mat_naming
from ..mat_types import (
    IndexSettings,
    SourceFilter,
    build_index,
    check_pattern_folders,
    check_text_encoding,
    page_layout_error,
    page_suffix_list,
    pattern_list,
    project_root,
)
from ._config import APIDOC_CONFIG, SOURCE_CONFIG, apidoc_value
from ._generate import ApidocOptions, generate

#: exit status when --check finds pages to change
CHECK_FAILED = 1
#: exit status for usage and settings errors (as argparse)
USAGE_ERROR = 2


def _version():
    try:
        from importlib.metadata import version

        return version("sphinxcontrib-matlabdomain")
    except Exception:
        return "0.0.0"


def get_parser():
    parser = argparse.ArgumentParser(
        prog="sphinx-matlab-apidoc",
        usage="%(prog)s [OPTIONS] [-c CONF_DIR] [-o OUTPUT_DIR] [ROOT]",
        description=(
            "Write reST pages with sphinxcontrib-matlabdomain directives for the "
            "MATLAB files below ROOT: one page per folder, mirroring the folder "
            "tree. Pages that start with the marker line are rewritten when "
            "they change and removed when they are no longer pages."
        ),
        epilog=(
            "With -c, ROOT, OUTPUT_DIR and the other settings come from conf.py "
            "(matlab_src_* , matlab_version, matlab_apidoc_*); flags override "
            "them. Without -c, ROOT and -o are required."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_version()}")
    parser.add_argument(
        "root",
        metavar="ROOT",
        nargs="?",
        help="the MATLAB project root (default: matlab_src_code_project_root)",
    )
    parser.add_argument(
        "-c",
        "--conf-dir",
        help="read the settings from conf.py in this folder (the Sphinx source folder)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        help="folder for the generated files (default: matlab_apidoc_output_dir)",
    )
    parser.add_argument(
        "--include",
        action="append",
        metavar="PATTERN",
        help="files to document, a glob relative to ROOT like "
        "matlab_src_include_patterns (repeatable; replaces the conf.py list; "
        "default: **/*)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        metavar="PATTERN",
        help="files to leave out, like matlab_src_exclusion_patterns "
        "(repeatable; replaces the conf.py list)",
    )
    parser.add_argument(
        "--matlab-version",
        help=f"like matlab_version (default: {mat_naming.DEFAULT_MATLAB_VERSION})",
    )
    parser.add_argument(
        "--encoding", help="like matlab_src_encoding (default: UTF-8, as MATLAB)"
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="also overwrite files without the marker line",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="write and remove nothing; list what would change",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="a dry run that exits with 1 if a page would change",
    )
    parser.add_argument(
        "-e",
        "--separate",
        action=argparse.BooleanOptionalAction,
        help="one page per file (default: off)",
    )
    parser.add_argument(
        "-d",
        "--maxdepth",
        type=int,
        help="maximum depth of the toctrees (default: 4)",
    )
    parser.add_argument(
        "--tocfile", help="name of the root folder's page (default: index)"
    )
    parser.add_argument("--suffix", help="file suffix (default: rst)")
    parser.add_argument(
        "-t",
        "--templatedir",
        help="folder with templates (folder.rst.jinja, object.rst.jinja) that "
        "replace the defaults",
    )
    parser.add_argument(
        "--remove-old",
        action=argparse.BooleanOptionalAction,
        help="delete files with the suffix below OUTPUT_DIR (not in folders "
        "starting with '.' or '_') that start with the marker line and are "
        "not pages of this run (default: on)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="no output on stdout, just warnings on stderr",
    )
    return parser


def _name(value, option):
    if not value or any(sep in value for sep in "/\\"):
        raise ConfigError(f"{option} {value!r} must be a file name.")
    return value


def read_conf(confdir):
    """Run ``confdir/conf.py`` like ``sphinx-build`` (no extensions, no tags)
    and return its ``Config`` with the values the CLI reads.
    """
    if not os.path.isfile(os.path.join(confdir, "conf.py")):
        raise ConfigError(f"-c {confdir!r} has no conf.py.")
    config = Config.read(os.path.abspath(confdir), overrides={}, tags=Tags())
    for name, default in SOURCE_CONFIG.items():
        config.add(name, default, "env", ())
    for name, (default, types) in APIDOC_CONFIG.items():
        config.add(name, default, "", types)
    return config


def _pick(flag, flag_name, conf, conf_name, default):
    """``(value, name)``: the flag if given, else the conf.py value, else the
    default; ``name`` is what an error should name.
    """
    if flag is not None:
        return flag, flag_name
    if conf is not None:
        return apidoc_value(conf, conf_name), conf_name
    return default, conf_name


def _path(flag, flag_name, conf, conf_name, srcdir):
    """Return ``(path, name)``: a flag's path (relative to the working
    folder), else conf.py's (relative to the source folder), else None.
    """
    if flag is not None:
        return flag, flag_name
    if conf is not None:
        value = apidoc_value(conf, conf_name)
        if value is not None:
            return os.path.join(srcdir, value), conf_name
    return None, conf_name


def _settings(args):
    """``(IndexSettings, ApidocOptions)`` of conf.py and the flags, or
    ConfigError.
    """
    conf = read_conf(args.conf_dir) if args.conf_dir is not None else None
    srcdir = os.path.abspath(args.conf_dir) if conf is not None else None
    sources = conf if conf is not None else argparse.Namespace(**SOURCE_CONFIG)

    if args.root is not None:
        root, root_name = os.path.abspath(args.root), f"ROOT {args.root!r}"
    elif sources.matlab_src_code_project_root is not None:
        root = project_root(sources, srcdir)
        root_name = f"matlab_src_code_project_root {root!r}"
    else:
        raise ConfigError(
            "ROOT is required (or -c with matlab_src_code_project_root in conf.py)."
        )
    if not os.path.isdir(root):
        raise ConfigError(f"{root_name} is not a folder.")

    if args.include is not None:
        include, include_name = pattern_list(args.include, "--include"), "--include"
    else:
        include_name = "matlab_src_include_patterns"
        include = pattern_list(sources.matlab_src_include_patterns, include_name)
    if args.exclude is not None:
        exclude = pattern_list(args.exclude, "--exclude")
    else:
        exclude = pattern_list(
            sources.matlab_src_exclusion_patterns, "matlab_src_exclusion_patterns"
        )
    check_pattern_folders(SourceFilter(include, exclude), root, include_name)

    encoding = args.encoding
    if encoding is None:
        encoding = sources.matlab_src_encoding
        check_text_encoding(encoding, "matlab_src_encoding")
    else:
        check_text_encoding(encoding, "--encoding")
    if args.matlab_version is not None:
        version, version_name = args.matlab_version, "--matlab-version: "
    else:
        version, version_name = sources.matlab_version, ""
    namelengthmax = sources.matlab_namelengthmax
    try:
        mat_naming.resolve_namelengthmax(version, None)
    except ValueError as err:
        raise ConfigError(f"{version_name}{err}") from err
    try:
        mat_naming.resolve_namelengthmax(version, namelengthmax)
    except ValueError as err:
        raise ConfigError(str(err)) from err

    output_dir, output_name = _path(
        args.output_dir, "-o", conf, "matlab_apidoc_output_dir", srcdir
    )
    if output_dir is None:
        raise ConfigError(
            "-o is required (or -c with matlab_apidoc_output_dir in conf.py)."
        )
    if os.path.exists(output_dir) and not os.path.isdir(output_dir):
        raise ConfigError(f"{output_name} {output_dir!r} is not a folder.")
    templatedir, template_name = _path(
        args.templatedir, "-t", conf, "matlab_apidoc_templatedir", srcdir
    )
    if templatedir is not None and not os.path.isdir(templatedir):
        raise ConfigError(f"{template_name} {templatedir!r} is not a folder.")
    tocfile = _pick(args.tocfile, "--tocfile", conf, "matlab_apidoc_tocfile", "index")
    suffix, suffix_name = _pick(
        args.suffix, "--suffix", conf, "matlab_apidoc_suffix", "rst"
    )
    # Pages next to code come from conf.py only (plan.md Section 2.11).
    page_suffixes = page_suffix_list(sources.matlab_src_page_suffixes)
    if page_suffixes:
        page_layout_error(root, srcdir)
    settings = IndexSettings(
        root=root,
        include=tuple(include),
        exclude=tuple(exclude),
        encoding=encoding,
        matlab_version=version,
        namelengthmax=namelengthmax,
        page_suffixes=page_suffixes,
        source_dir=srcdir,
    )
    options = ApidocOptions(
        output_dir=output_dir,
        force=args.force,
        dry_run=args.dry_run or args.check,
        separate=_pick(
            args.separate, "--separate", conf, "matlab_apidoc_separate", False
        )[0],
        maxdepth=_pick(args.maxdepth, "-d", conf, "matlab_apidoc_maxdepth", 4)[0],
        tocfile=_name(*tocfile),
        suffix=_name(suffix.removeprefix("."), suffix_name),
        templatedir=templatedir,
        remove_old=_pick(
            args.remove_old, "--remove-old", conf, "matlab_apidoc_remove_old", True
        )[0],
    )
    return settings, options


class _WarningHandler(logging.Handler):
    """Print warnings like Sphinx (``location: WARNING: message [type.subtype]``)
    and count them.
    """

    def __init__(self, stream):
        super().__init__(logging.WARNING)
        self.stream = stream
        self.count = 0

    def emit(self, record):
        self.count += 1
        location = getattr(record, "location", None)
        prefix = f"{location}: " if location else ""
        label = "WARNING" if record.levelno == logging.WARNING else "ERROR"
        kind = ".".join(
            str(part)
            for part in (
                getattr(record, "type", None),
                getattr(record, "subtype", None),
            )
            if part
        )
        tail = f" [{kind}]" if kind else ""
        print(f"{prefix}{label}: {record.getMessage()}{tail}", file=self.stream)


@contextlib.contextmanager
def _sphinx_warnings(stream):
    """Route the ``sphinx`` loggers (``sphinx.util.logging``) to one handler
    while the generator runs; in-process callers keep their own handlers.
    """
    logger = logging.getLogger("sphinx")
    saved = logger.handlers[:], logger.propagate, logger.level
    handler = _WarningHandler(stream)
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.WARNING)
    try:
        yield handler
    finally:
        logger.handlers, logger.propagate = saved[0], saved[1]
        logger.setLevel(saved[2])


def main(argv=None):
    """Run ``sphinx-matlab-apidoc``; return the exit status.

    0 on success, also with warnings; 1 if ``--check`` finds a page to
    change; 2 for usage or settings errors (argparse exits with 2 itself for
    usage errors).
    """
    parser = get_parser()
    args = parser.parse_args(argv)
    try:
        settings, options = _settings(args)
    except ConfigError as err:
        print(f"{parser.prog}: error: {err}", file=sys.stderr)
        return USAGE_ERROR

    start = time.perf_counter()
    with _sphinx_warnings(sys.stderr) as warnings:
        source_index = build_index(settings)
        result = generate(source_index, options)
    elapsed = time.perf_counter() - start

    if not args.quiet:
        verbs = (
            "Would create file",
            "Would update file",
            "Would rename",
            "Would remove file",
        )
        if not options.dry_run:
            verbs = ("Creating file", "Updating file", "Renaming", "Removing file")
        changes = (result.created, result.updated, result.renamed, result.removed)
        for verb, paths in zip(verbs, changes, strict=True):
            for path in paths:
                shown = os.path.join(options.output_dir, *path.split("/"))
                print(f"{verb} {shown}.")
        kept = f", {len(result.kept)} kept (-f overwrites)" if result.kept else ""
        renamed = f", {len(result.renamed)} renamed" if result.renamed else ""
        print(
            f"{'Dry run: ' if options.dry_run else ''}{len(result.pages)} pages: "
            f"{len(result.created)} created, {len(result.updated)} updated, "
            f"{len(result.unchanged)} unchanged{kept}{renamed}, "
            f"{len(result.removed)} removed; {len(source_index.index)} files "
            f"indexed, {warnings.count} warnings, {elapsed:.2f} s."
        )
    if args.check and result.changed:
        print(
            f"{parser.prog}: the pages in {options.output_dir} are out of date.",
            file=sys.stderr,
        )
        return CHECK_FAILED
    return 0
