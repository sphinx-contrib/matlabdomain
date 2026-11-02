"""sphinxcontrib.matlab_apidoc._cli.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Command line of ``sphinx-matlab-apidoc`` (plan.md Section 2.8). The
settings come from ``conf.py`` in ``-c DIR`` (default: the working folder)
only; the flags are run-time options.
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
    check_config_names,
    check_pattern_folders,
    check_text_encoding,
    pattern_list,
    project_root,
    sidecar_layout_error,
    sidecar_suffix_list,
)
from ._config import (
    APIDOC_CONFIG,
    BUILD_ONLY_CONFIG,
    SOURCE_CONFIG,
    apidoc_value,
)
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
        allow_abbrev=False,
        description=(
            "Write reST pages with sphinxcontrib-matlabdomain directives for the "
            "MATLAB files of the project that CONF_DIR/conf.py documents: one "
            "page per folder, mirroring the folder tree. Pages that start with "
            "the marker line are rewritten when they change and removed when "
            "they are no longer pages."
        ),
        epilog=(
            "The settings come from conf.py only: matlab_src_code_project_root "
            "and matlab_apidoc_output_dir (both required), the other "
            "matlab_src_* values, matlab_version, matlab_namelengthmax, "
            "matlab_apidoc_templatedir and matlab_apidoc_separate. For anything "
            "else, write a script on the Python API "
            "(sphinxcontrib.matlab_apidoc.generate)."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_version()}")
    parser.add_argument(
        "-c",
        "--conf-dir",
        default=".",
        help="the folder of conf.py, the Sphinx source folder (default: the "
        "working folder)",
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
        "-q",
        "--quiet",
        action="store_true",
        help="no output on stdout, just warnings on stderr",
    )
    return parser


def read_conf(confdir):
    """Run ``confdir/conf.py`` like ``sphinx-build`` (no extensions, no tags)
    and return its ``Config`` with the values the CLI reads.
    """
    if not os.path.isfile(os.path.join(confdir, "conf.py")):
        raise ConfigError(f"-c {confdir!r} has no conf.py.")
    config = Config.read(os.path.abspath(confdir), overrides={}, tags=Tags())
    known = {*SOURCE_CONFIG, *APIDOC_CONFIG, *BUILD_ONLY_CONFIG}
    check_config_names(config._raw_config, known)
    for name, default in SOURCE_CONFIG.items():
        config.add(name, default, "env", ())
    for name, (default, types) in APIDOC_CONFIG.items():
        config.add(name, default, "", types)
    return config


def _folder(conf, name, srcdir):
    """Return a path value of conf.py (relative to the source folder) or None."""
    value = apidoc_value(conf, name)
    return None if value is None else os.path.join(srcdir, value)


def _settings(args):
    """``(IndexSettings, ApidocOptions)`` of conf.py and the flags, or
    ConfigError.
    """
    conf = read_conf(args.conf_dir)
    srcdir = os.path.abspath(args.conf_dir)

    root = project_root(conf, srcdir)
    if root is None:
        raise ConfigError("matlab_src_code_project_root is required in conf.py.")
    if not os.path.isdir(root):
        raise ConfigError(f"matlab_src_code_project_root {root!r} is not a folder.")

    include_name = "matlab_src_include_patterns"
    include = pattern_list(conf.matlab_src_include_patterns, include_name)
    exclude = pattern_list(
        conf.matlab_src_exclusion_patterns, "matlab_src_exclusion_patterns"
    )
    check_pattern_folders(SourceFilter(include, exclude), root, include_name)

    encoding = conf.matlab_src_encoding
    check_text_encoding(encoding, "matlab_src_encoding")
    version, namelengthmax = conf.matlab_version, conf.matlab_namelengthmax
    try:
        mat_naming.resolve_namelengthmax(version, namelengthmax)
    except ValueError as err:
        raise ConfigError(str(err)) from err

    output_dir = _folder(conf, "matlab_apidoc_output_dir", srcdir)
    if output_dir is None:
        raise ConfigError("matlab_apidoc_output_dir is required in conf.py.")
    if os.path.exists(output_dir) and not os.path.isdir(output_dir):
        raise ConfigError(f"matlab_apidoc_output_dir {output_dir!r} is not a folder.")
    templatedir = _folder(conf, "matlab_apidoc_templatedir", srcdir)
    if templatedir is not None and not os.path.isdir(templatedir):
        raise ConfigError(f"matlab_apidoc_templatedir {templatedir!r} is not a folder.")
    sidecar_suffixes = sidecar_suffix_list(conf.matlab_src_sidecar_suffixes)
    if sidecar_suffixes:
        sidecar_layout_error(root, srcdir)
    settings = IndexSettings(
        root=root,
        include=tuple(include),
        exclude=tuple(exclude),
        encoding=encoding,
        matlab_version=version,
        namelengthmax=namelengthmax,
        sidecar_suffixes=sidecar_suffixes,
        source_dir=srcdir,
    )
    options = ApidocOptions(
        output_dir=output_dir,
        force=args.force,
        dry_run=args.dry_run or args.check,
        separate=apidoc_value(conf, "matlab_apidoc_separate"),
        templatedir=templatedir,
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
