"""The ``matlab-api-check`` builder: audit MATLAB help text (plan.md Section 2.9).

Every indexed object is checked, whether a page documents it or not, unless
``matlab_api_check_files`` selects files.

:copyright: Copyright 2014-2024 by the sphinxcontrib-matlabdomain team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

import functools
import json
import os
import re
from dataclasses import dataclass

from sphinx.builders import Builder
from sphinx.errors import ConfigError
from sphinx.util.logging import getLogger
from sphinx.util.matching import Matcher

from . import mat_types
from .mat_classify import is_hidden

logger = getLogger("matlab-domain")

#: rule names, in report order
RULES = (
    "description",
    "method-description",
    "property-description",
    "inputs",
    "outputs",
    "name-value",
    "example",
    "method-example",
    "sidecar-documented",
    "sidecar-links",
)
SEVERITIES = ("error", "warning", "ignore")
#: the newer rules warn by default, so they do not fail existing checks
DEFAULT_RULES = {
    **dict.fromkeys(RULES, "error"),
    **dict.fromkeys(("property-description", "example", "method-example"), "warning"),
}
#: object kinds, in report order
KINDS = ("function", "class", "method", "property", "script", "application", "sidecar")
_PLURALS = dict(
    zip(
        KINDS,
        (
            "functions",
            "classes",
            "methods",
            "properties",
            "scripts",
            "apps",
            "sidecars",
        ),
        strict=True,
    )
)
REPORT_TXT = "api-check.txt"
REPORT_JSON = "api-check.json"
_IGNORE_OPTION = "matlab_api_check_ignore_patterns"
_FILES_OPTION = "matlab_api_check_files"


def _header(*labels):
    """Regexes for a help line that starts a section with a label (any case):
    ``(colon, alone)``. ``colon``: the label, then ``:`` and anything
    (``Inputs: x - data``, ``Input : x``, ``Options::``), or a short
    qualifier and ``:`` ending the line (``Inputs (all optional):``,
    ``Parameters and their meaning:``). ``alone``: only the label (``Input``).
    """
    alts = "|".join(label.replace(" ", r"\s+") for label in labels)
    start = rf"^[ \t]*(?P<label>{alts})"
    qualifier = r"(?:[ \t]*\([^)\n]*\)|[ \t]+[\w' /-]{1,40}?)[ \t]*::?[ \t]*$"
    return (
        re.compile(rf"{start}(?:[ \t]*::?.*$|{qualifier})", re.IGNORECASE),
        re.compile(rf"{start}[ \t]*$", re.IGNORECASE),
    )


_NV = r"name[-/\s]?value"
_NV_LABELS = (
    rf"(?:optional )?{_NV} (?:arguments?|pairs?|pair arguments?|parameters?|options?)",
    rf"input arguments? \({_NV} arguments?\)",
)
_OPTIONAL = r"optional (?:inputs?|arguments?|parameters?)"
#: the built-in labels of the sections that napoleon_custom_sections can extend
_LABELS = {
    "inputs": (
        r"inputs?(?:\(s\))?",
        r"input (?:arguments?|parameters?)",
        r"arguments?",
        r"param(?:eter)?s?",
        r"required (?:inputs?|arguments?)",
        _OPTIONAL,
        _NV_LABELS[1],
    ),
    "outputs": (
        r"outputs?(?:\(s\))?",
        r"output (?:arguments?|parameters?)",
        r"returns?",
        r"return (?:values?|arguments?)",
    ),
}
SECTIONS = {
    "inputs": _header(*_LABELS["inputs"]),
    "outputs": _header(*_LABELS["outputs"]),
    "name-value": _header(r"options?", _OPTIONAL, *_NV_LABELS),
    "example": _header(
        r"examples?(?:\(s\))?(?:[ \t]+\d+)?",
        r"usage",
        r"example usage",
        r"usage examples?(?:\(s\))?",
    ),
}
_EXAMPLE_RUBRIC = re.compile(
    r"^[ \t]*\.\.[ \t]+rubric::[ \t]*(?:examples?|usage)\b",
    re.IGNORECASE | re.MULTILINE,
)
_UNDERLINE = re.compile(r"^[ \t]*[-=~]{3,}[ \t]*$")
# rule -> (section, example header, what lacks a comment)
_MESSAGES = {
    "inputs": ("inputs", "Inputs:", "inputs"),
    "outputs": ("outputs", "Outputs:", "outputs"),
    "name-value": ("name-value", "Name-Value Arguments:", "name-value arguments"),
}
#: the napoleon_custom_sections styles whose sections are inputs or outputs
_STYLES = {"params_style": "inputs", "returns_style": "outputs"}


def custom_labels(config):
    """Return the ``napoleon_custom_sections`` headings that Napoleon renders
    as input or output sections: ``((rule, heading), ...)``, sorted.

    Read as Napoleon reads them, in order, the last entry for a heading
    winning: ``(heading, "params_style")`` is an input section,
    ``(heading, "returns_style")`` an output section, ``(heading, other)``
    the section ``other`` names if an earlier entry made it one. A plain
    heading is a generic section; an alias of one of Napoleon's own
    sections, or of an unknown one, is not an input or output section.
    A built-in label keeps its meaning (``("Outputs", "params_style")``
    adds no input section). Without ``sphinx.ext.napoleon`` nothing renders
    them: none.
    """
    try:
        entries = config.napoleon_custom_sections
    except AttributeError:
        return ()
    rules = {}
    for entry in entries or ():
        if isinstance(entry, str):
            rules[entry.lower()] = None
            continue
        try:
            heading, style = entry[0], entry[1]
        except (TypeError, LookupError):
            continue
        if isinstance(heading, str) and isinstance(style, str):
            rules[heading.lower()] = _STYLES.get(style) or rules.get(style.lower())
    return tuple(
        sorted(
            (rule, heading)
            for heading, rule in rules.items()
            if rule
            and heading.split()
            and not any(alone.match(heading) for _, alone in SECTIONS.values())
        )
    )


@functools.cache
def sections_for(labels):
    """``SECTIONS`` with the ``custom_labels`` added to their sections."""
    if not labels:
        return SECTIONS
    sections = dict(SECTIONS)
    for rule, builtin in _LABELS.items():
        extra = [
            r"\s+".join(map(re.escape, heading.split()))
            for r, heading in labels
            if r == rule
        ]
        if extra:
            sections[rule] = _header(*builtin, *extra)
    return sections


def check_config(app, config):  # noqa: ARG001
    """``config-inited``: ConfigError for unknown rules or severities and for
    ignore patterns that are not relative globs.
    """
    rules = config.matlab_api_check_rules
    if not isinstance(rules, dict):
        raise ConfigError("matlab_api_check_rules must be a dict of rule -> severity.")
    for rule, severity in rules.items():
        if rule not in RULES:
            raise ConfigError(
                f"matlab_api_check_rules: unknown rule {rule!r}; the rules are "
                f"{', '.join(RULES)}."
            )
        if severity not in SEVERITIES:
            raise ConfigError(
                f"matlab_api_check_rules: the severity of {rule!r} must be "
                f"{', '.join(SEVERITIES)}, not {severity!r}."
            )
    ignore_patterns(config)
    selected_files(config)


def ignore_patterns(config):
    """Return the normalized ``matlab_api_check_ignore_patterns`` (or ConfigError)."""
    patterns = getattr(config, _IGNORE_OPTION)
    if isinstance(patterns, str) or not isinstance(patterns, (list, tuple)):
        raise ConfigError(f"{_IGNORE_OPTION} must be a list of glob patterns.")
    return [mat_types._normalize_pattern(p, _IGNORE_OPTION) for p in patterns]


def selected_files(config):
    """Return the normalized ``matlab_api_check_files`` without duplicates:
    None selects every file, ``[]`` none (or ConfigError). A string, as
    ``-D`` gives it, is a list separated by commas or line breaks.
    """
    entries = getattr(config, _FILES_OPTION)
    if entries is None:
        return None
    if isinstance(entries, str):
        entries = [e.strip() for e in re.split(r"[,\n]", entries)]
        entries = [e for e in entries if e]
    elif not isinstance(entries, (list, tuple)):
        raise ConfigError(
            f"{_FILES_OPTION} must be None, a list of paths or glob patterns, "
            "or a string of them separated by commas."
        )
    return list(
        dict.fromkeys(mat_types._normalize_pattern(e, _FILES_OPTION) for e in entries)
    )


def _why_unmatched(root, entry):
    """Why the ``matlab_api_check_files`` entry ``entry`` selects no file."""
    if root is None:
        return "matlab_src_code_project_root is not set"
    if not mat_types._GLOB_CHARS.isdisjoint(entry) or entry.endswith("/"):
        return "no indexed file matches it"
    path = os.path.join(root, *entry.split("/"))
    if os.path.isdir(path):
        return "it is a folder; end it with '/' to select the files below it"
    if os.path.exists(path):
        return (
            "the project does not index it (excluded, not a MATLAB file or "
            "sidecar doc, or another letter case)"
        )
    return "no such file below the project root"


@dataclass
class Finding:
    reference: str
    name: str | None
    kind: str
    rule: str
    severity: str
    message: str
    line: int | None
    path: str

    def text(self):
        """Return ``<ref> (<MATLAB name>): <message> [<rule>]``."""
        who = self.reference if self.name is None else f"{self.reference} ({self.name})"
        return f"{who}: {self.message} [{self.rule}]"

    def location(self):
        """``path:line``, or None without a line (a bare path is a docname)."""
        return None if self.line is None else f"{self.path}:{self.line}"

    def to_json(self):
        return {
            "reference": self.reference,
            "name": self.name,
            "kind": self.kind,
            "rule": self.rule,
            "severity": self.severity,
            "line": self.line,
            "message": self.message,
        }


def has_description(docstring):
    """Return True if the help's first line (MATLAB's H1 line) is not blank."""
    return bool((docstring or "").split("\n", 1)[0].strip())


def has_section(rule, docstring, names=(), sections=SECTIONS):
    """Return True if the help has a line that starts the rule's section.

    A lowercase label alone after a line of text is a wrapped prose word
    unless it is underlined (``---``). A label with text after its colon
    that is the name of one of the function's arguments (``names``,
    lowercase) is an entry, not a section (``input: the data``).
    ``sections`` holds the labels (``sections_for``).
    """
    colon, alone = sections[rule]
    lines = (docstring or "").split("\n")
    for i, line in enumerate(lines):
        if match := colon.match(line):
            label = " ".join(match["label"].lower().split())
            entry = line[match.end("label") :].partition(":")[2].strip(": \t")
            if not (entry and label in names):
                return True
        elif match := alone.match(line):
            after = lines[i + 1] if i + 1 < len(lines) else ""
            prose = i and lines[i - 1].strip() and match["label"].islower()
            if not prose or _UNDERLINE.match(after):
                return True
    return False


def has_example(docstring):
    """Return True if the help has an example section (or rubric)."""
    return has_section("example", docstring) or bool(
        _EXAMPLE_RUBRIC.search(docstring or "")
    )


def undocumented(rule, docstring, comments, names=(), sections=SECTIONS):
    """Names in ``comments`` (name -> its ``arguments``-block comment) left
    undocumented: [] if the help has the rule's section (``has_section``) or
    every name has a comment, else the names without one.
    """
    if not comments or has_section(rule, docstring, names, sections):
        return []
    return [name for name, comment in comments.items() if not comment]


def is_public(attrs):
    """Return True unless a method or property with the attributes ``attrs``
    is private, protected, access-listed or hidden (a property's
    ``GetAccess`` applies when it has no ``Access``).
    """
    attrs = attrs or {}
    access = attrs.get("Access") or attrs.get("GetAccess")
    if isinstance(access, str):
        access = access.strip("'\"")
    return access in (None, "public") and not attrs.get("Hidden")


class _Checker:
    """Applies the rules to the indexed objects of one build."""

    def __init__(self, dom, rules, ignore, selection=None, sections=SECTIONS):
        self.dom = dom
        self.rules = rules
        self.ignore = Matcher(ignore)
        self.sections = sections
        self.findings = []
        #: source paths of the files resolved (parsed or from the cache)
        self.parsed = []
        self.checked = dict.fromkeys(KINDS, 0)
        self.not_checked: dict[str, int] = dict.fromkeys(
            ("ignored", "hidden", "unreadable", "not_parsed"), 0
        )
        #: the ``selected_files`` entries; None selects every file
        self.selection = selection
        #: the entries that selected a file, and the number of files selected
        self.matched = set()
        self.selected = 0
        if selection is not None:
            self.not_checked["not_selected"] = 0
            self._literal = {
                e for e in selection if mat_types._GLOB_CHARS.isdisjoint(e)
            } - {e for e in selection if e.endswith("/")}
            self._globs = {
                e: Matcher([f"{e}**" if e.endswith("/") else e])
                for e in selection
                if e not in self._literal
            }

    def select(self, ref):
        """Return True if the file or sidecar doc ``ref`` is selected (counted)."""
        if self.selection is None:
            return True
        hits = {e for e, match in self._globs.items() if match(ref)}
        if ref in self._literal:
            hits.add(ref)
        self.matched |= hits
        if hits:
            self.selected += 1
        else:
            self.not_checked["not_selected"] += 1
        return bool(hits)

    def unmatched(self, root):
        """``[(entry, why)]``: the selection entries that selected no file."""
        return [
            (e, _why_unmatched(root, e))
            for e in self.selection or ()
            if e not in self.matched
        ]

    def report(self, rule, where, kind, message):
        severity = self.rules[rule]
        if severity != "ignore":
            self.findings.append(
                Finding(
                    kind=kind, rule=rule, severity=severity, message=message, **where
                )
            )

    def describe(self, rule, where, kind, docstring):
        self.checked[kind] += 1
        if not has_description(docstring):
            self.report(
                rule,
                where,
                kind,
                "has no description: its help is empty or starts with a blank line",
            )

    def example(self, rule, where, kind, docstring):
        if not has_example(docstring):
            self.report(
                rule,
                where,
                kind,
                'has no example section in its help (such as "Example:")',
            )

    def signature(self, where, kind, func, inputs, outputs):
        """Apply the inputs, outputs and name-value rules to a function or method."""
        structs = {name.split(".", 1)[0] for name in func.name_value}
        groups = {
            "inputs": {
                n: (func.args.get(n) or {}).get("docstring")
                for n in inputs
                if n != "~" and n not in structs
            },
            "outputs": {n: (func.retv.get(n) or {}).get("docstring") for n in outputs},
            "name-value": func.name_value,
        }
        names = {n.lower() for n in (*func.args, *func.retv, *structs)}
        for rule, comments in groups.items():
            if missing := undocumented(
                rule, func.docstring, comments, names, self.sections
            ):
                section, example, what = _MESSAGES[rule]
                self.report(
                    rule,
                    where,
                    kind,
                    f'has no {section} section in its help (such as "{example}"), '
                    f"and these {what} have no arguments-block comment: "
                    f"{', '.join(missing)}",
                )

    def method(self, where, func, class_name, static):
        constructor = func.name == class_name
        inputs = list(func.args)
        if not (static or constructor):
            inputs = inputs[1:]  # the object
        # A constructor's output is the object.
        outputs = [] if constructor else list(func.retv)
        self.describe("method-description", where, "method", func.docstring)
        if not constructor:
            self.example("method-example", where, "method", func.docstring)
        self.signature(where, "method", func, inputs, outputs)

    def members(self, cls, where):
        for pname, prop in cls.properties.items():
            if not is_public(prop["attrs"]):
                continue
            ref = f"{where['reference']}.{pname}"
            if self.ignore(ref):
                self.not_checked["ignored"] += 1
                continue
            self.checked["property"] += 1
            if not prop["docstring"]:
                member = {
                    "reference": ref,
                    "name": where["name"] and f"{where['name']}.{pname}",
                    "path": where["path"],
                    "line": prop["line"],
                }
                self.report(
                    "property-description",
                    member,
                    "property",
                    "has no description: no comment above, after or below it",
                )
        for mname, method in cls.methods.items():
            # A class-folder method is checked through its own file; MATLAB's
            # help shows no text for an abstract method.
            if (
                getattr(method, "from_class_folder", False)
                or method.attrs.get("Abstract")
                or not is_public(method.attrs)
            ):
                continue
            ref = f"{where['reference']}.{mname}"
            if self.ignore(ref):
                self.not_checked["ignored"] += 1
                continue
            member = {
                "reference": ref,
                "name": where["name"] and f"{where['name']}.{mname}",
                "path": where["path"],
                "line": method.line,
            }
            self.method(member, method, cls.name, bool(method.attrs.get("Static")))

    def check(self, path, record):
        ref = record["reference"]
        # Before anything is parsed: an unselected file costs no parse.
        if not self.select(ref):
            return
        if record["unreadable"]:
            self.not_checked["unreadable"] += 1
            return
        if is_hidden(ref):
            self.not_checked["hidden"] += 1
            return
        if self.ignore(ref):
            self.not_checked["ignored"] += 1
            return
        obj = mat_types.resolve(self.dom, ref)
        self.parsed.append(path)
        if any(warning[0] == "parse_error" for warning in obj.source_warnings):
            self.not_checked["not_parsed"] += 1
            return
        where = {
            "reference": ref,
            "name": record["matlab_name"],
            "path": path,
            "line": getattr(obj, "line", None),
        }
        if isinstance(obj, mat_types.MatMethod):  # a function file of a class folder
            # Its classdef signature gives Access, Hidden and Static.
            if is_public(obj.attrs) and not obj.cls.attrs.get("Hidden"):
                self.method(where, obj, obj.cls.name, bool(obj.attrs.get("Static")))
        elif isinstance(obj, mat_types.MatFunction):
            self.describe("description", where, "function", obj.docstring)
            self.example("example", where, "function", obj.docstring)
            self.signature(where, "function", obj, list(obj.args), list(obj.retv))
        elif isinstance(obj, mat_types.MatClass):
            if obj.attrs.get("Hidden"):  # MATLAB's mark for "not public API"
                self.not_checked["hidden"] += 1
                return
            self.describe("description", where, "class", obj.docstring)
            self.example("example", where, "class", obj.docstring)
            self.members(obj, where)
        elif isinstance(obj, mat_types.MatScript):
            script = {**where, "line": 1}
            self.describe("description", script, "script", obj.docstring)
            self.example("example", script, "script", obj.docstring)
        else:
            self.describe("description", where, "application", obj.docstring)

    def sidecars(self, env):
        """Check the sidecar docs (plan.md Section 2.11): each is
        rendered by ``mat:autosidecar`` in a document that a toctree includes
        (or an orphan), and its relative links and images exist.
        """
        data = self.dom.data
        included = {env.config.root_doc}
        included.update(d for docs in env.toctree_includes.values() for d in docs)
        docs, issues = {}, {}
        for docname, refs in data["sidecar_docs"].items():
            for ref in refs:
                docs.setdefault(ref, set()).add(docname)
        for found in data["sidecar_issues"].values():
            for ref, *issue in found:
                issues.setdefault(ref, set()).add(tuple(issue))
        for path, record in sorted(
            data["sidecars"].items(), key=lambda i: i[1]["reference"]
        ):
            ref = record["reference"]
            if not self.select(ref):
                continue
            if self.ignore(ref):
                self.not_checked["ignored"] += 1
                continue
            self.checked["sidecar"] += 1
            where = {"reference": ref, "name": None, "path": path, "line": None}
            shown = docs.get(ref, set())
            if not shown:
                self.report(
                    "sidecar-documented",
                    where,
                    "sidecar",
                    "is not rendered by a mat:autosidecar directive",
                )
            elif not any(
                d in included or "orphan" in env.metadata.get(d, {}) for d in shown
            ):
                self.report(
                    "sidecar-documented",
                    where,
                    "sidecar",
                    f"is rendered in {', '.join(sorted(shown))}, which no toctree "
                    "includes",
                )
            for kind, target, line in sorted(
                issues.get(ref, ()), key=lambda i: (i[2] or 0, i[0], i[1])
            ):
                what = (
                    "links to a missing file"
                    if kind == "link"
                    else "shows a missing image"
                )
                self.report(
                    "sidecar-links",
                    {**where, "line": line},
                    "sidecar",
                    f"{what}: {target}",
                )


def _summary(enabled, rules, checker, unmatched=()):
    findings = {rule: {"error": 0, "warning": 0} for rule in RULES}
    for finding in checker.findings if checker else ():
        findings[finding.rule][finding.severity] += 1
    summary = {
        "enabled": enabled,
        "rules": rules,
        "checked": checker.checked if checker else dict.fromkeys(KINDS, 0),
        "not_checked": checker.not_checked if checker else {},
        "findings": findings,
        "errors": sum(n["error"] for n in findings.values()),
        "warnings": sum(n["warning"] for n in findings.values()),
    }
    if checker and checker.selection is not None:
        summary["selection"] = {
            "entries": checker.selection,
            "selected": checker.selected,
            "unmatched": [{"entry": e, "reason": why} for e, why in unmatched],
        }
    return summary


def _text_report(summary, findings):
    selection = summary.get("selection")
    lines = [
        f"{u['entry']}: error: matches no indexed file or sidecar doc: "
        f"{u['reason']} [{_FILES_OPTION}]"
        for u in (selection or {}).get("unmatched", ())
    ]
    lines += [f"{f.location() or f.path}: {f.severity}: {f.text()}" for f in findings]
    if lines:
        lines.append("")
    if not summary["enabled"]:
        lines.append("matlab_api_check_enabled is False: nothing was checked.")
    if selection is not None:
        if not selection["entries"]:
            lines.append(f"{_FILES_OPTION} is empty: no file was selected.")
        total = selection["selected"] + summary["not_checked"]["not_selected"]
        lines.append(
            f"Selected: {selection['selected']} of {total} files by "
            f"{len(selection['entries'])} {_FILES_OPTION} entries, "
            f"{len(selection['unmatched'])} matching no file"
        )
    checked = ", ".join(
        f"{n} {_PLURALS[kind]}" for kind, n in summary["checked"].items()
    )
    lines.append(f"Checked: {checked}")
    if summary["not_checked"]:
        skipped = ", ".join(
            f"{n} {why.replace('_', ' ')}" for why, n in summary["not_checked"].items()
        )
        lines.append(f"Not checked: {skipped}")
    lines.append(
        f"Findings: {summary['errors']} errors, {summary['warnings']} warnings"
    )
    lines.extend(
        f"  {rule} ({summary['rules'][rule]}): {n['error']} errors, "
        f"{n['warning']} warnings"
        for rule, n in summary["findings"].items()
    )
    return "\n".join(lines) + "\n"


class MatlabApiCheckBuilder(Builder):
    """Checks the help text of the MATLAB sources (``-b matlab-api-check``).

    The pages are read as for any builder; the check covers every indexed
    object (or those of the files ``matlab_api_check_files`` selects),
    whether a page documents it or not, and writes no pages.
    """

    name = "matlab-api-check"
    epilog = f"The MATLAB API check passed; see %(outdir)s{os.sep}{REPORT_TXT}."

    def init(self):
        #: number of findings with the severity ``error``
        self.errors = 0
        #: number of matlab_api_check_files entries that selected no file
        self.unmatched = 0

    def get_outdated_docs(self):
        return "the MATLAB sources"

    def get_target_uri(self, docname, typ=None):  # noqa: ARG002
        return ""

    def write_documents(self, docnames):
        """No pages (Sphinx >= 8.1)."""

    def prepare_writing(self, docnames):
        """Nothing to prepare (abstract before Sphinx 8.1)."""

    def write_doc(self, docname, doctree):
        """No pages (Sphinx 8.0 calls this for every page)."""

    def finish(self):
        config = self.config
        dom = self.env.get_domain("mat")
        rules = {**DEFAULT_RULES, **config.matlab_api_check_rules}
        enabled = bool(config.matlab_api_check_enabled)
        checker = None
        unmatched = []
        if enabled:
            checker = _Checker(
                dom,
                rules,
                ignore_patterns(config),
                selected_files(config),
                sections_for(custom_labels(config)),
            )
            records = sorted(dom.data["index"].items(), key=lambda i: i[1]["reference"])
            for path, record in records:
                checker.check(path, record)
            checker.sidecars(self.env)
            unmatched = checker.unmatched(
                mat_types.project_root(config, self.env.srcdir)
            )
        findings = checker.findings if checker else []
        summary = _summary(enabled, rules, checker, unmatched)
        # The report first: -W may stop the build at the first warning.
        os.makedirs(self.outdir, exist_ok=True)
        with open(
            os.path.join(self.outdir, REPORT_TXT), "w", encoding="utf-8", newline="\n"
        ) as f:
            f.write(_text_report(summary, findings))
        with open(
            os.path.join(self.outdir, REPORT_JSON), "w", encoding="utf-8", newline="\n"
        ) as f:
            json.dump(
                {"summary": summary, "findings": [x.to_json() for x in findings]},
                f,
                indent=2,
            )
            f.write("\n")
        self.errors = summary["errors"]
        self.unmatched = len(unmatched)
        if checker:
            _warn_parsed(dom, checker.parsed)
        for entry, why in unmatched:
            logger.error(
                "[sphinxcontrib-matlabdomain] %s: %r matches no indexed file or "
                "sidecar doc: %s",
                _FILES_OPTION,
                entry,
                why,
                type="mat",
                subtype="api_check",
            )
        for finding in findings:
            log = logger.error if finding.severity == "error" else logger.warning
            log(
                "[sphinxcontrib-matlabdomain] %s",
                finding.text(),
                type="mat",
                subtype="api_check",
                location=finding.location(),
            )


def _warn_parsed(dom, paths):
    """Parse-stage warnings of the checked files that no page read in this
    build used (those were warned on ``env-updated``).
    """
    data = dom.data
    used = set()
    for docname in dom.read_docnames:
        used.update(data["doc_sources"].get(docname, ()))
    for path in paths:
        if path not in used:
            record = data["index"][path]
            key = (path, record["mtime"], record["size"])
            for warning in data["parse_warnings"].get(key, ()):
                mat_types._warn(*warning)


def set_status(app, exception):
    """``build-finished``: exit status 1 when an ``error`` rule found something
    or a ``matlab_api_check_files`` entry selected no file.
    """
    builder = app.builder
    if (
        exception is None
        and isinstance(builder, MatlabApiCheckBuilder)
        and (builder.errors or builder.unmatched)
    ):
        app.statuscode = 1
