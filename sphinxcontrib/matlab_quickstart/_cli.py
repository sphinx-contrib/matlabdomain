"""Command line of ``scmd quickstart`` (plan.md Section 2.13).

It runs the prompts with detected defaults, the answers file, the dry run,
the writes and the report.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import tomllib
from pathlib import Path

from sphinx.errors import ConfigError

from .. import mat_naming
from ..mat_types import (
    DEFAULT_EXCLUSION_PATTERNS,
    IndexSettings,
    build_index,
    pattern_list,
    sidecar_paths,
)
from ..matlab_apidoc._cli import _count, _sphinx_warnings, _version
from ..matlab_apidoc._generate import GROUPS, ApidocOptions, generate
from . import _detect, _report, _write

#: exit status when ``uv add`` fails or the run is interrupted
FAILED = 1
#: exit status for usage errors and for stops before anything is written
USAGE_ERROR = 2
#: the default name of a saved answers file, in the project root
ANSWERS_FILE = "scmd-quickstart.toml"
#: the keys of an answers file, in prompt order
KEYS = (
    "project",
    "author",
    "matlab_version",
    "group",
    "theme",
    "html_baseurl",
    "exclude",
    "markdown",
    "sidecars",
    "make",
    "guide",
    "api_pages",
    "napoleon_custom_sections",
)
CHOICES = {
    "group": GROUPS,
    "make": ("uv", "plain"),
    "api_pages": ("commit", "generate"),
}
BOOLS = ("markdown", "sidecars", "guide")
API_DIR = "API"
NAPOLEON = "napoleon_custom_sections"


class Stop(Exception):
    """Stop with a message on stderr and an exit status."""

    def __init__(self, message, status=USAGE_ERROR):
        super().__init__(message)
        self.status = status


def get_parser(prog="scmd quickstart"):
    parser = argparse.ArgumentParser(
        prog=prog,
        allow_abbrev=False,
        description=(
            "Set up Sphinx documentation for the MATLAB project in ROOT: a Sphinx "
            "source folder (conf.py, index.rst, make files, a build guide and the "
            "API pages of scmd apidoc), the docs dependencies (uv add "
            "--frozen --group docs) and lines in .gitignore and .gitattributes. It "
            "asks one question per choice, with the detected answer as the "
            "default, and prints a report of the project."
        ),
        epilog=(
            "It stops before writing anything when DOCS/conf.py exists (unless "
            "--force) or when pyproject.toml, .gitignore or .gitattributes have "
            "uncommitted changes. It never touches uv.lock, the project's MATLAB "
            "code or CI, and never commits. For a project with Simulink files it "
            "adds +sphinxcontrib/+matlabdomain/simulinkDocumentationLinker.m and "
            "its settings to ROOT, for Help links to the documentation."
        ),
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {_version()}"
    )
    parser.add_argument(
        "root",
        metavar="ROOT",
        nargs="?",
        default=".",
        help="the MATLAB project root (default: the working folder)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        metavar="DOCS",
        help="the Sphinx source folder, inside ROOT (default: ROOT/docs)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="ask nothing: the answers file, then the detected defaults",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="write nothing; print what would be written and the report",
    )
    parser.add_argument(
        "-a",
        "--answers",
        metavar="FILE",
        help="the answers of a TOML file; ask only for the others",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="rewrite the files it writes when DOCS/conf.py exists",
    )
    return parser


# --- answers -----------------------------------------------------------------


def _section(entry):
    if isinstance(entry, str):
        return entry
    if (
        isinstance(entry, (list, tuple))
        and len(entry) == 2
        and all(isinstance(part, str) for part in entry)
    ):
        return tuple(entry)
    raise ValueError(
        f"{NAPOLEON} must be a list of headings and [heading, style] pairs, "
        f"not {entry!r}."
    )


def check_answer(key, value):
    """Return ``value`` as kept for the answer ``key``, or ValueError."""
    if key in BOOLS:
        if not isinstance(value, bool):
            raise ValueError(f"{key} must be true or false, not {value!r}.")
    elif key in CHOICES:
        if value not in CHOICES[key]:
            raise ValueError(
                f"{key} must be {' or '.join(map(repr, CHOICES[key]))}, not {value!r}."
            )
    elif key == "exclude":
        try:
            pattern_list(value, key)
        except ConfigError as err:
            raise ValueError(str(err)) from err
        value = list(value)
    elif key == NAPOLEON:
        if not isinstance(value, list):
            raise ValueError(f"{key} must be a list, not {value!r}.")
        value = [_section(entry) for entry in value]
    elif key == "html_baseurl":
        if not isinstance(value, str):
            raise ValueError(f"{key} must be a text, not {value!r}.")
        if value and not value.startswith(("https://", "http://")):
            raise ValueError(
                f"{key} must start with https:// or http://, not {value!r}."
            )
    else:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a text, not {value!r}.")
        if key == "matlab_version":
            mat_naming.validate_matlab_version(value)
    return value


def read_answers(path):
    """Return the checked answers of the TOML file ``path``, or Stop."""
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except OSError as err:
        raise Stop(f"--answers {path}: {err.strerror or err}.") from err
    except tomllib.TOMLDecodeError as err:
        raise Stop(f"--answers {path}: {err}.") from err
    unknown = sorted(set(data) - set(KEYS))
    if unknown:
        raise Stop(
            f"--answers {path}: unknown keys {', '.join(unknown)}; the keys are "
            f"{', '.join(KEYS)}."
        )
    answers = {}
    for key, value in data.items():
        try:
            answers[key] = check_answer(key, value)
        except ValueError as err:
            raise Stop(f"--answers {path}: {err}") from err
    return answers


def _toml(value, inline=False):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    items = [_toml(item, inline=True) for item in value]
    if inline or not items:
        return f"[{', '.join(items)}]"
    return "[\n" + "".join(f"    {item},\n" for item in items) + "]"


def dumps(answers):
    """Return the TOML text of ``answers``."""
    lines = ["# Answers of scmd quickstart: --answers FILE reads them back."]
    lines += [f"{key} = {_toml(answers[key])}" for key in KEYS]
    return "\n".join(lines) + "\n"


def yes_no(reply):
    reply = reply.lower()
    if reply in ("y", "yes"):
        return True
    if reply in ("n", "no"):
        return False
    raise ValueError("Answer y or n.")


def patterns(reply):
    return [part.strip() for part in reply.split(",") if part.strip()]


def _shown(value):
    if isinstance(value, bool):
        return "Y/n" if value else "y/N"
    if isinstance(value, list):
        return ", ".join(value) or "none"
    return value


def prompt(text, default, parse, shown=None):
    """Ask until the reply parses; an empty reply is ``default``."""
    while True:
        reply = input(f"> {text} [{shown or _shown(default)}]: ").strip()
        if not reply:
            return default
        try:
            return parse(reply)
        except ValueError as err:
            print(f"* {err}")


class Prompter:
    """Answers from the answers file, else from a prompt (``quiet``: the
    default).
    """

    def __init__(self, given, quiet):
        self.answers = dict(given)
        self.quiet = quiet

    def ask(self, key, text, default, parse=str, shown=None):
        if key not in self.answers:
            self.answers[key] = (
                default
                if self.quiet
                else prompt(text, default, lambda r: check_answer(key, parse(r)), shown)
            )
        return self.answers[key]


# --- the Sphinx source folder ------------------------------------------------


def _inside(path, root):
    """Return True if ``path`` is below ``root`` (not ``root`` itself)."""
    try:
        common = os.path.commonpath([path, root])
    except ValueError:  # another drive
        return False
    folded = os.path.normcase(path)
    return os.path.normcase(common) == os.path.normcase(root) != folded


def _in_use(docs):
    """Return True for a file, or a folder with files but no ``conf.py``."""
    if os.path.isfile(os.path.join(docs, "conf.py")):
        return False
    return os.path.exists(docs) and (not os.path.isdir(docs) or bool(os.listdir(docs)))


def _relative(path, start):
    return Path(os.path.relpath(path, start)).as_posix()


def docs_folder(args, root):
    """Return the Sphinx source folder: ``-o`` or ``ROOT/docs``, or another
    one when it is in use (asked for); or Stop.
    """
    docs = os.path.abspath(args.output_dir or os.path.join(root, "docs"))
    while True:
        if not _inside(docs, root):
            raise Stop(f"-o {docs}: the Sphinx source folder must be inside ROOT.")
        if not _in_use(docs):
            break
        shown = _relative(docs, root)
        if args.quiet:
            raise Stop(
                f"{shown} is in use: it has files but no conf.py. Choose another "
                "folder with -o."
            )
        print(f"{shown} is in use: it has files but no conf.py.")
        reply = ""
        while not reply:
            reply = input("> Sphinx source folder, relative to ROOT: ").strip()
        docs = os.path.abspath(os.path.join(root, reply))
    if os.path.isfile(os.path.join(docs, "conf.py")) and not args.force:
        raise Stop(
            f"{_relative(docs, root)}/conf.py exists, so nothing is written "
            "(--force rewrites the files scmd quickstart writes)."
        )
    return docs


# --- the run -----------------------------------------------------------------


def _git_author(root):
    if shutil.which("git") is None:
        return ""
    status, output = _write.run(["git", "config", "user.name"], root)
    return "" if status else output


def _facts(root):
    versions = _detect.matlab_versions(root)
    version, note = _detect.matlab_version_default(versions)
    uv = _detect.uv_project(root)
    submodules = _detect.submodule_paths(root)
    return {
        "versions": versions,
        "version": version,
        "version_note": note,
        "uv": uv,
        "pyproject": _detect.read_pyproject(root) is not None,
        "submodules": submodules,
        "exclude": [*DEFAULT_EXCLUSION_PATTERNS, *submodules],
        "path": _detect.project_path(root),
        "install": _detect.matlabdomain_install(),
        "myst": _detect.is_importable("myst_parser"),
    }


def _ask(prompter, facts, root, docs):
    """Ask the questions that come before the index; return the sidecar
    doc candidates.
    """
    p = prompter
    project = p.ask("project", "Project name", os.path.basename(root))
    p.ask("author", "Author names", _git_author(root) or f"The {project} authors")
    p.ask("matlab_version", "MATLAB release the code targets", facts["version"])
    p.ask("group", "API pages per namespace or per folder", "namespace")
    p.ask("theme", "HTML theme", "furo")
    p.ask(
        "html_baseurl",
        "URL of the published site (blank: not published yet)",
        "",
        shown="none",
    )
    exclude = p.ask(
        "exclude",
        "Folders and files not to document (patterns relative to ROOT, "
        "comma-separated)",
        [],
        patterns,
    )
    candidates = []
    if p.ask("markdown", "Markdown pages with MyST", facts["myst"], yes_no):
        settings = IndexSettings(
            root=root,
            exclude=tuple(pattern_list([*facts["exclude"], *exclude], "exclude")),
            sidecar_suffixes=(".md",),
            source_dir=docs,
        )
        candidates = _detect.code_next_to(sidecar_paths(settings))
        p.ask(
            "sidecars",
            f"Markdown notes next to the code as API pages ({len(candidates)} found)",
            bool(candidates),
            yes_no,
        )
    elif p.answers.setdefault("sidecars", False):
        raise Stop("sidecars = true needs markdown = true.")
    p.ask("make", "Make files through uv or plain", "uv" if facts["uv"] else "plain")
    p.ask("guide", "A build guide for contributors (BUILDING_DOCS.md)", True, yes_no)
    p.ask("api_pages", "API pages committed, or generated before each build", "commit")
    return candidates


def _ask_napoleon(prompter, headings):
    if not headings.entries:
        prompter.answers.setdefault(NAPOLEON, [])
        return
    if not prompter.quiet and NAPOLEON not in prompter.answers:
        _report.print_entries(headings)
    prompter.ask(
        NAPOLEON,
        "Use these napoleon_custom_sections",
        headings.entries,
        lambda reply: headings.entries if yes_no(reply) else [],
        shown="Y/n",
    )


def _guide_install(facts):
    install = facts["install"]
    if install.kind == "editable":
        return _detect.Install("version", _detect.DISTRIBUTION)
    return install


def _dependencies(answers, facts, args, in_git):
    """Return ``(commands to run, header, lines to print)`` for the docs
    dependencies.
    """
    install = facts["install"]
    commands = _write.uv_commands(answers, install)
    shown = [_write.shell(c) for c in commands]
    if facts["uv"]:
        if args.dry_run:
            return [], "Would run:", shown
        if not in_git:
            return [], "Not in a git repository; run:", shown
        if shutil.which("uv") is None:
            return [], "uv was not found; run:", shown
        return commands, "", []
    header = "Install the docs dependencies:"
    if answers["make"] == "uv":
        return [], header, ([] if facts["pyproject"] else ["uv init --bare"]) + shown
    return [], header, _write.install_lines(answers, install, facts["pyproject"])


def _outside_edits(answers, root, docs_rel):
    """Return ``{file: lines}`` to add to ``.gitignore`` and ``.gitattributes``."""
    gitignore = [f"{docs_rel}/_build/"]
    if answers["api_pages"] == "generate":
        gitignore.append(f"{docs_rel}/{API_DIR}/")
    wanted = {".gitignore": gitignore, ".gitattributes": [_write.GITATTRIBUTES_LINE]}
    edits = {}
    for name, lines in wanted.items():
        if missing := _write.missing_lines(os.path.join(root, name), lines):
            edits[name] = missing
    return edits


def _write_outside(args, root, edits, in_git):
    for name, added in edits.items():
        if args.dry_run:
            verb = "Would add to"
        elif in_git:
            verb = "Adding to"
            _write.append_lines(os.path.join(root, name), added)
        else:
            verb = "Not in a git repository; add to"
        for line in added:
            print(f"{verb} {name}: {line}")


def _git_stop(args, dirty):
    """Stop for uncommitted changes (in a dry run: print it)."""
    stop = (
        f"{', '.join(dirty)} {'has' if len(dirty) == 1 else 'have'} uncommitted "
        "changes: commit or stash them first, so that git restore undoes exactly "
        "the edits of scmd quickstart."
    )
    if not args.dry_run:
        raise Stop(stop)
    print(f"Would stop: {stop}")


def _apply(args, root, docs, answers, facts, files, dirty):
    """Make the edits outside the Sphinx source folder and write its files
    (in a dry run: print them); return the ``uv`` commands run and the
    ``Written``.
    """
    in_git = dirty is not None
    docs_rel = _relative(docs, root)
    commands, header, lines = _dependencies(answers, facts, args, in_git)
    for command in commands:
        print(f"Running {_write.shell(command)}")
        status, output = _write.run(command, root)
        if status:
            raise Stop(f"{_write.shell(command)} failed:\n{output}", FAILED)
    if lines:
        print(header)
        for line in lines:
            print(f"  {line}")
    _write_outside(args, root, _outside_edits(answers, root, docs_rel), in_git)
    written = _write.write_files(docs, files, args.dry_run)
    verbs = (
        ("Would create", "Would update") if args.dry_run else ("Creating", "Updating")
    )
    for verb, names in zip(verbs, (written.created, written.updated), strict=True):
        for name in names:
            print(f"{verb} file {docs_rel}/{name}.")
    return commands, written


def _write_linker(args, root, docs_rel, published):
    """Write the function behind the Help links of the Simulink files."""
    written = _write.write_files(
        root, _write.linker_files(root, docs_rel, published), args.dry_run
    )
    verbs = (
        ("Would create", "Would update") if args.dry_run else ("Creating", "Updating")
    )
    for verb, names in zip(verbs, (written.created, written.updated), strict=True):
        for name in names:
            print(f"{verb} file {name} (Help links of the Simulink files).")


def run(args):
    """Run the command for ``args``; return the exit status, or Stop."""
    start = time.perf_counter()
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        raise Stop(f"ROOT {args.root!r} is not a folder.")
    prompter = Prompter(read_answers(args.answers) if args.answers else {}, args.quiet)
    docs = docs_folder(args, root)
    docs_rel = _relative(docs, root)
    dirty = _write.git_dirty(root)
    if dirty:
        _git_stop(args, dirty)
    facts = _facts(root)
    candidates = _ask(prompter, facts, root, docs)
    answers = prompter.answers
    linker = os.path.join(root, *_write.LINKER_FOLDER.split("/"), f"{_write.LINKER}.m")
    tools = [_write.LINKER_EXCLUDE] if os.path.isfile(linker) else []
    exclude = pattern_list([*facts["exclude"], *answers["exclude"], *tools], "exclude")
    settings = IndexSettings(
        root=root,
        exclude=tuple(exclude),
        matlab_version=answers["matlab_version"],
        sidecar_suffixes=(".md",) if answers["sidecars"] else (),
        source_dir=docs,
    )
    with _sphinx_warnings(sys.stderr) as warnings:
        source_index = build_index(settings)
        found = _detect.survey(source_index)
        simulink = bool(tools) or _detect.has_simulink(source_index)
        headings = _detect.napoleon_headings(found)
        _ask_napoleon(prompter, headings)
        path = facts["path"]
        references = {r["reference"] for r in source_index.index.values()}
        suggestions = _detect.path_suggestions(references, path) if path else []
        rel_root = _relative(root, docs)
        context = {
            "root": rel_root,
            "docs": docs_rel,
            "copyright": f"{time.strftime('%Y')}, {answers['author']}",
            "submodules": bool(facts["submodules"]),
            "gitmodules": f"{rel_root}/.gitmodules",
            "suggestions": suggestions,
            "path_source": path.source if path else "",
            "linker_exclude": _write.LINKER_EXCLUDE if simulink else "",
            # A contributor's guide names no folder of this machine.
            "install": "\n".join(_write.pip_lines(answers, _guide_install(facts))),
        }
        files = _write.render(answers, context)
        commands, written = _apply(args, root, docs, answers, facts, files, dirty)
        if simulink:
            _write_linker(args, root, docs_rel, answers["html_baseurl"])
        result = generate(
            source_index,
            ApidocOptions(
                output_dir=os.path.join(docs, API_DIR),
                force=args.force,
                dry_run=args.dry_run,
                group=answers["group"],
            ),
        )
    pages = len(result.created) + len(result.updated)
    if pages:
        verb = "Would write" if args.dry_run else "Writing"
        print(f"{verb} {_count(pages, 'API page')} in {docs_rel}/{API_DIR}.")
    _report.print_report(
        answers,
        facts,
        {
            "source_index": source_index,
            "found": found,
            "headings": headings,
            "candidates": candidates,
            "suggestions": suggestions,
            "docs": docs_rel,
            "dry_run": args.dry_run,
            "installed": bool(commands),
        },
    )
    mode = "Dry run: " if args.dry_run else ""
    print(
        f"{mode}{_count(len(written.created) + len(written.updated), 'file')} in "
        f"{docs_rel}, {_count(len(result.pages), 'API page')}; "
        f"{_count(len(source_index.index), 'file')} indexed, "
        f"{_count(warnings.count, 'warning')}, {time.perf_counter() - start:.2f} s."
    )
    if not args.quiet:
        save_answers(args, root, answers)
    return 0


def save_answers(args, root, answers):
    """Offer to save the answers (default yes in a dry run)."""
    if not prompt("Save the answers to a file", args.dry_run, yes_no):
        return
    default = args.answers or os.path.join(root, ANSWERS_FILE)
    path = input(f"> File [{default}]: ").strip() or default
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(dumps(answers))
    print(f"Saved the answers: --answers {path} reads them back.")


def main(argv=None, *, prog="scmd quickstart"):
    """Run ``scmd quickstart``; return the exit status.

    0 on success, also with warnings; 1 when ``uv add`` fails or the run is
    interrupted; 2 for usage errors and when it stops before writing
    anything (an occupied DOCS with ``-q``, an existing ``DOCS/conf.py``,
    uncommitted changes, a bad answers file).
    """
    parser = get_parser(prog)
    args = parser.parse_args(argv)
    try:
        return run(args)
    except Stop as err:
        print(f"{parser.prog}: error: {err}", file=sys.stderr)
        return err.status
    except (KeyboardInterrupt, EOFError):
        print("\n[Interrupted.]")
        return FAILED
