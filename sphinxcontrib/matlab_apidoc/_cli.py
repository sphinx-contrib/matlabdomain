"""sphinxcontrib.matlab_apidoc._cli.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Command line of ``scmd apidoc`` (plan.md Section 2.8). The
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
from sphinx.util.logging import is_suppressed_warning
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
    simulink_doc_suffix_list,
)
from ._config import (
    APIDOC_CONFIG,
    BUILD_ONLY_CONFIG,
    SOURCE_CONFIG,
    apidoc_value,
)
from ._generate import GROUPS, ApidocOptions, generate

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


def get_parser(prog="scmd apidoc"):
    parser = argparse.ArgumentParser(
        prog=prog,
        allow_abbrev=False,
        description=(
            "Write reST pages with sphinxcontrib-matlabdomain directives for the "
            "MATLAB files of the project that CONF_DIR/conf.py documents: one "
            "page per namespace (matlab_apidoc_group = 'namespace', the default) "
            "or per folder ('folder'). Pages that start with "
            "the marker line are rewritten when they change and removed when "
            "they are no longer pages (matlab_apidoc_remove_old)."
        ),
        epilog=(
            "The settings come from conf.py only: matlab_src_code_project_root "
            "and matlab_apidoc_output_dir (both required), the other "
            "matlab_src_* values, matlab_version and the "
            "other matlab_apidoc_* values. For full control, write a script on "
            "the Python API (sphinxcontrib.matlab_apidoc.generate)."
        ),
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {_version()}"
    )
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
        "-k",
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


def _file_name(conf, name):
    """Return a file-name value of conf.py, or ConfigError."""
    value = apidoc_value(conf, name)
    if not value or any(sep in value for sep in "/\\"):
        raise ConfigError(f"{name} {value!r} must be a file name.")
    return value


def _settings(args):
    """``(IndexSettings, ApidocOptions, suppress_warnings)`` of conf.py and
    the flags, or ConfigError.
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
        conf.matlab_src_exclude_patterns, "matlab_src_exclude_patterns"
    )
    check_pattern_folders(SourceFilter(include, exclude), root, include_name)

    encoding = conf.matlab_src_encoding
    check_text_encoding(encoding, "matlab_src_encoding")
    version = conf.matlab_version
    try:
        mat_naming.validate_matlab_version(version)
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
        sidecar_suffixes=sidecar_suffixes,
        source_dir=srcdir,
        simulink_doc_suffixes=simulink_doc_suffix_list(
            conf.matlab_simulink_doc_suffixes
        ),
    )
    group = apidoc_value(conf, "matlab_apidoc_group")
    if group not in GROUPS:
        raise ConfigError(
            f"matlab_apidoc_group must be {' or '.join(map(repr, GROUPS))}, "
            f"not {group!r}."
        )
    page_size = apidoc_value(conf, "matlab_apidoc_page_size")
    if page_size < 1:
        raise ConfigError(
            f"matlab_apidoc_page_size must be 1 or more, not {page_size}."
        )
    options = ApidocOptions(
        output_dir=output_dir,
        force=args.force,
        dry_run=args.dry_run or args.check,
        separate=apidoc_value(conf, "matlab_apidoc_separate"),
        maxdepth=apidoc_value(conf, "matlab_apidoc_maxdepth"),
        tocfile=_file_name(conf, "matlab_apidoc_tocfile"),
        templatedir=templatedir,
        remove_old=apidoc_value(conf, "matlab_apidoc_remove_old"),
        group=group,
        page_size=page_size,
        private=apidoc_value(conf, "matlab_apidoc_private"),
    )
    suppress = conf.suppress_warnings
    if isinstance(suppress, str) or not isinstance(suppress, (list, tuple, set)):
        raise ConfigError(f"suppress_warnings must be a list, not {suppress!r}.")
    return settings, options, list(suppress)


class _WarningHandler(logging.Handler):
    """Print warnings like Sphinx (``location: WARNING: message [type.subtype]``)
    and count them; skip those that ``suppress_warnings`` names.
    """

    def __init__(self, stream, suppress=()):
        super().__init__(logging.WARNING)
        self.stream = stream
        self.suppress = suppress
        self.count = 0

    def emit(self, record):
        warning_type = getattr(record, "type", None) or ""
        subtype = getattr(record, "subtype", None) or ""
        if is_suppressed_warning(warning_type, subtype, self.suppress):
            return
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
def _sphinx_warnings(stream, suppress=()):
    """Route the ``sphinx`` loggers (``sphinx.util.logging``) to one handler
    while the generator runs; in-process callers keep their own handlers.
    """
    logger = logging.getLogger("sphinx")
    saved = logger.handlers[:], logger.propagate, logger.level
    handler = _WarningHandler(stream, suppress)
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.WARNING)
    try:
        yield handler
    finally:
        logger.handlers, logger.propagate = saved[0], saved[1]
        logger.setLevel(saved[2])


def _count(number, noun):
    """``1 page``, ``2 pages``."""
    return f"{number} {noun}{'' if number == 1 else 's'}"


def main(argv=None, *, prog="scmd apidoc"):
    """Run ``scmd apidoc``; return the exit status.

    0 on success, also with warnings; 1 if ``--check`` finds a page to
    change; 2 for usage or settings errors (argparse exits with 2 itself for
    usage errors).
    """
    parser = get_parser(prog)
    args = parser.parse_args(argv)
    try:
        settings, options, suppress = _settings(args)
    except ConfigError as err:
        print(f"{parser.prog}: error: {err}", file=sys.stderr)
        return USAGE_ERROR

    start = time.perf_counter()
    with _sphinx_warnings(sys.stderr, suppress) as warnings:
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
        mode = "Check: " if args.check else "Dry run: " if options.dry_run else ""
        print(
            f"{mode}{_count(len(result.pages), 'page')}: "
            f"{len(result.created)} created, {len(result.updated)} updated, "
            f"{len(result.unchanged)} unchanged{kept}{renamed}, "
            f"{len(result.removed)} removed; "
            f"{_count(len(source_index.index), 'file')} indexed, "
            f"{_count(warnings.count, 'warning')}, {elapsed:.2f} s."
        )
    if args.check and result.changed:
        print(
            f"{parser.prog}: the pages in {options.output_dir} are out of date.",
            file=sys.stderr,
        )
        return CHECK_FAILED
    return 0
