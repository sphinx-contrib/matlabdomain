"""The report of ``scmd quickstart`` (plan.md Section 2.13).

It shows the project facts, the inventory of the index, the help headings,
the copyright blocks that run into help, and the next steps.
"""

from __future__ import annotations

import textwrap

from ..matlab_apidoc._cli import _count as _apidoc_count
from ._detect import SECTION_FILES, inventory
from ._write import py

#: the most items a list of the report shows
LIMIT = 10
WIDTH = 79
_KINDS = {
    "function": "function",
    "class": "class",
    "script": "script",
    "application": "app",
    "model": "model",
    "library": "library",
    "subsystem": "subsystem file",
}


def _count(number, noun):
    if noun == "class":
        return f"{number} class{'' if number == 1 else 'es'}"
    if noun == "library":
        return f"{number} librar{'y' if number == 1 else 'ies'}"
    return _apidoc_count(number, noun)


def _line(text, indent=2):
    """Print ``text`` wrapped at spaces, continued two columns further in."""
    print(
        textwrap.fill(
            text,
            width=WIDTH,
            initial_indent=" " * indent,
            subsequent_indent=" " * (indent + 2),
            break_long_words=False,
            break_on_hyphens=False,
        )
    )


def _items(items, limit=LIMIT):
    shown = ", ".join(items[:limit])
    more = len(items) - limit
    return f"{shown}, and {more} more" if more > 0 else shown


def _rows(rows):
    return _items([f"{name} ({files})" for name, files in rows])


def print_entries(headings):
    """Print the detected ``napoleon_custom_sections``, before asking."""
    print(f"Help headings in {SECTION_FILES} or more files, and their variants:")
    for entry in headings.entries:
        print(f"  {py(entry)}")


def _facts(answers, facts, candidates, suggestions):
    print("Project:")
    versions = facts["versions"]
    for release in sorted(versions, key=lambda r: (-sum(versions[r].values()), r)):
        files = ", ".join(
            f"{name} ({n})" for name, n in sorted(versions[release].items())
        )
        _line(f"{release} is named in {files}")
    if not versions:
        _line("No MATLAB release is named in the CI files, matlab.toml or a README.")
    note = facts["version_note"]
    note = (
        f" ({note})" if note and answers["matlab_version"] == facts["version"] else ""
    )
    _line(f"matlab_version: {answers['matlab_version']}{note}")
    _line(f"uv project: {'yes, ' + facts['uv'] if facts['uv'] else 'no'}")
    install = facts["install"]
    _line(f"matlabdomain is installed as: {install.requirement} ({install.kind})")
    if facts["submodules"]:
        _line(f"Git submodules, left out: {_items(facts['submodules'])}")
    path = facts["path"]
    if path:
        folders = _count(len(path.folders), "folder")
        _line(f"MATLAB project path ({path.source}): {folders}")
        if suggestions:
            _line(f"Not on it, commented out in conf.py: {_items(suggestions)}")
    else:
        _line(
            "MATLAB project path: none read (matlab.toml, resources/project); "
            "no exclusions suggested"
        )
    if answers["markdown"]:
        state = "on" if answers["sidecars"] else "off"
        markdown = _count(len(candidates), "Markdown file")
        _line(f"Sidecar docs {state}: {markdown} next to the code")


def _inventory(source_index):
    found = inventory(source_index)
    kinds = ", ".join(
        _count(found["kinds"][kind], name)
        for kind, name in _KINDS.items()
        if found["kinds"][kind]
    )
    total = _count(len(source_index.index), "file")
    unknown = f", {found['unknown']} unreadable" if found["unknown"] else ""
    print("Inventory:")
    _line(
        f"{total} indexed{f': {kinds}' if kinds else ''}{unknown}; "
        f"{_count(len(found['namespaces']), 'namespace')}"
    )
    if sidecars := source_index.sidecars:
        _line(_count(len(sidecars), "sidecar doc"))
    duplicates = found["duplicates"]
    if duplicates:
        _line(
            f"Duplicate MATLAB names ({len(duplicates)}; exclude a copy, or keep "
            "both, listed by path):"
        )
        for name, files in list(duplicates.items())[:LIMIT]:
            _line(f"{name}: {', '.join(files)}", 4)
        if len(duplicates) > LIMIT:
            _line(f"and {len(duplicates) - LIMIT} more", 4)
    if found["not_callable"]:
        _line(
            f"Not callable ({len(found['not_callable'])}; documented by path): "
            f"{_items(found['not_callable'])}"
        )
    if found["encoding"]:
        _line(
            f"Not UTF-8 ({len(found['encoding'])}; they decode with a warning): "
            f"{_items(found['encoding'])}"
        )


def _headings(headings, found):
    print("Help headings:")
    rows = (
        ("In napoleon_custom_sections", headings.used),
        ("Napoleon's own sections, no entry needed", headings.builtin),
        ("Napoleon cannot match them (rename them in the code)", headings.unmatchable),
        (f"In fewer than {SECTION_FILES} files, not used", headings.unused),
    )
    if not any(row for _, row in rows):
        _line("none")
    for label, row in rows:
        if row:
            _line(f"{label}: {_rows(row)}")
    if found.legal:
        _line(
            f"Copyright blocks that run into help ({len(found.legal)}; a blank "
            "line, not %, before such a block ends the help there):",
            0,
        )
        _line(_items(found.legal))


def _next_steps(answers, docs, dry_run, installed, uv):
    steps = []
    if dry_run:
        steps.append(("Run again without -n to write the files.", []))
    if uv or answers["make"] == "uv":
        after = "" if installed else ", after the commands above"
        steps.append(
            (
                f"Lock and install the docs dependencies{after}:",
                ["uv lock", "uv sync --group docs"],
            )
        )
    else:
        steps.append(("Install the docs dependencies (above).", []))
    steps += [
        (f"Write an introduction in {docs}/index.rst.", []),
        (
            f"Build in {docs}, with a warning for each link that does not "
            "resolve (on Windows: set SPHINXOPTS=-n, then make clean and make "
            "html):",
            ['make clean html SPHINXOPTS="-n"'],
        ),
        (
            "Fix or explain each warning: the Warnings page of the "
            "sphinxcontrib-matlabdomain docs lists the usual fixes. Then the "
            "strict build is the CI build:",
            ['make clean html SPHINXOPTS="-n -W"'],
        ),
    ]
    if answers["api_pages"] == "commit":
        steps.append(
            (
                "Commit the API pages. In CI, this fails when they are out of date:",
                ["make apidoc-check"],
            )
        )
    steps.append(
        (
            "The help-text audit; every rule is a warning at first:",
            ["make matlab-api-check"],
        )
    )
    print("Next steps:")
    for number, (text, commands) in enumerate(steps, 1):
        print(
            textwrap.fill(
                text,
                width=WIDTH,
                initial_indent=f"  {number}. ",
                subsequent_indent="     ",
                break_on_hyphens=False,
            )
        )
        for command in commands:
            print(f"       {command}")


def print_report(answers, facts, run):
    """Print the report; ``run`` holds what the run found and did."""
    _facts(answers, facts, run["candidates"], run["suggestions"])
    _inventory(run["source_index"])
    _headings(run["headings"], run["found"])
    _next_steps(answers, run["docs"], run["dry_run"], run["installed"], facts["uv"])
