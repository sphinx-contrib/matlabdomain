"""The ``matlab-api-check`` builder: audit MATLAB help text (plan.md Section 2.9).

Every indexed object is checked, whether a page documents it or not.

:copyright: Copyright 2014-2024 by the sphinxcontrib-matlabdomain team, see AUTHORS.
:license: BSD, see LICENSE for details.
"""

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
    "inputs",
    "outputs",
    "name-value",
    "page-documented",
    "page-links",
)
SEVERITIES = ("error", "warning", "ignore")
DEFAULT_RULES = dict.fromkeys(RULES, "error")
#: object kinds, in report order
KINDS = ("function", "class", "method", "script", "application", "page")
_PLURALS = dict(
    zip(
        KINDS,
        ("functions", "classes", "methods", "scripts", "apps", "pages"),
        strict=True,
    )
)
REPORT_TXT = "api-check.txt"
REPORT_JSON = "api-check.json"
_IGNORE_OPTION = "matlab_api_check_ignore_patterns"


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
SECTIONS = {
    "inputs": _header(
        r"inputs?(?:\(s\))?",
        r"input (?:arguments?|parameters?)",
        r"arguments?",
        r"param(?:eter)?s?",
        r"required (?:inputs?|arguments?)",
        _OPTIONAL,
        _NV_LABELS[1],
    ),
    "outputs": _header(
        r"outputs?(?:\(s\))?",
        r"output (?:arguments?|parameters?)",
        r"returns?",
        r"return (?:values?|arguments?)",
    ),
    "name-value": _header(r"options?", _OPTIONAL, *_NV_LABELS),
}
_UNDERLINE = re.compile(r"^[ \t]*[-=~]{3,}[ \t]*$")
# rule -> (section, example header, what lacks a comment)
_MESSAGES = {
    "inputs": ("inputs", "Inputs:", "inputs"),
    "outputs": ("outputs", "Outputs:", "outputs"),
    "name-value": ("name-value", "Name-Value Arguments:", "name-value arguments"),
}


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


def ignore_patterns(config):
    """Return the normalized ``matlab_api_check_ignore_patterns`` (or ConfigError)."""
    patterns = getattr(config, _IGNORE_OPTION)
    if isinstance(patterns, str) or not isinstance(patterns, (list, tuple)):
        raise ConfigError(f"{_IGNORE_OPTION} must be a list of glob patterns.")
    return [mat_types._normalize_pattern(p, _IGNORE_OPTION) for p in patterns]


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


def has_section(rule, docstring, names=()):
    """Return True if the help has a line that starts the rule's section.

    A lowercase label alone after a line of text is a wrapped prose word
    unless it is underlined (``---``). A label with text after its colon
    that is the name of one of the function's arguments (``names``,
    lowercase) is an entry, not a section (``input: the data``).
    """
    colon, alone = SECTIONS[rule]
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


def undocumented(rule, docstring, comments, names=()):
    """Names in ``comments`` (name -> its ``arguments``-block comment) left
    undocumented: [] if the help has the rule's section (``has_section``) or
    every name has a comment, else the names without one.
    """
    if not comments or has_section(rule, docstring, names):
        return []
    return [name for name, comment in comments.items() if not comment]


def is_public(method):
    """Return True unless the method is private, protected, access-listed or hidden."""
    attrs = method.attrs or {}
    access = attrs.get("Access")
    if isinstance(access, str):
        access = access.strip("'\"")
    return access in (None, "public") and not attrs.get("Hidden")


class _Checker:
    """Applies the rules to the indexed objects of one build."""

    def __init__(self, dom, rules, ignore):
        self.dom = dom
        self.rules = rules
        self.ignore = Matcher(ignore)
        self.findings = []
        #: source paths of the files resolved (parsed or from the cache)
        self.parsed = []
        self.checked = dict.fromkeys(KINDS, 0)
        self.not_checked = dict.fromkeys(
            ("ignored", "hidden", "unreadable", "not_parsed"), 0
        )

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
            if missing := undocumented(rule, func.docstring, comments, names):
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
        self.signature(where, "method", func, inputs, outputs)

    def members(self, cls, where):
        for mname, method in cls.methods.items():
            # A class-folder method is checked through its own file.
            if getattr(method, "from_class_folder", False) or not is_public(method):
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
            self.method(where, obj, obj.cls.name, static=False)
        elif isinstance(obj, mat_types.MatFunction):
            self.describe("description", where, "function", obj.docstring)
            self.signature(where, "function", obj, list(obj.args), list(obj.retv))
        elif isinstance(obj, mat_types.MatClass):
            self.describe("description", where, "class", obj.docstring)
            self.members(obj, where)
        elif isinstance(obj, mat_types.MatScript):
            self.describe("description", {**where, "line": 1}, "script", obj.docstring)
        else:
            self.describe("description", where, "application", obj.docstring)

    def pages(self, env):
        """Check the pages next to code (plan.md Section 2.11): each is
        rendered by ``mat:autopage`` in a document that a toctree includes
        (or an orphan), and its relative links and images exist.
        """
        data = self.dom.data
        included = {env.config.root_doc}
        included.update(d for docs in env.toctree_includes.values() for d in docs)
        docs, issues = {}, {}
        for docname, refs in data["page_docs"].items():
            for ref in refs:
                docs.setdefault(ref, set()).add(docname)
        for found in data["page_issues"].values():
            for ref, *issue in found:
                issues.setdefault(ref, set()).add(tuple(issue))
        for path, record in sorted(
            data["pages"].items(), key=lambda i: i[1]["reference"]
        ):
            ref = record["reference"]
            if self.ignore(ref):
                self.not_checked["ignored"] += 1
                continue
            self.checked["page"] += 1
            where = {"reference": ref, "name": None, "path": path, "line": None}
            shown = docs.get(ref, set())
            if not shown:
                self.report(
                    "page-documented",
                    where,
                    "page",
                    "is not rendered by a mat:autopage directive",
                )
            elif not any(
                d in included or "orphan" in env.metadata.get(d, {}) for d in shown
            ):
                self.report(
                    "page-documented",
                    where,
                    "page",
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
                    "page-links", {**where, "line": line}, "page", f"{what}: {target}"
                )


def _summary(enabled, rules, checker):
    findings = {rule: {"error": 0, "warning": 0} for rule in RULES}
    for finding in checker.findings if checker else ():
        findings[finding.rule][finding.severity] += 1
    return {
        "enabled": enabled,
        "rules": rules,
        "checked": checker.checked if checker else dict.fromkeys(KINDS, 0),
        "not_checked": checker.not_checked if checker else {},
        "findings": findings,
        "errors": sum(n["error"] for n in findings.values()),
        "warnings": sum(n["warning"] for n in findings.values()),
    }


def _text_report(summary, findings):
    lines = [f"{f.location() or f.path}: {f.severity}: {f.text()}" for f in findings]
    if lines:
        lines.append("")
    if not summary["enabled"]:
        lines.append("matlab_api_check_enabled is False: nothing was checked.")
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
    object, whether a page documents it or not, and writes no pages.
    """

    name = "matlab-api-check"
    epilog = "The MATLAB API check passed; see %(outdir)s/api-check.txt."

    def init(self):
        #: number of findings with the severity ``error``
        self.errors = 0

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
        if enabled:
            checker = _Checker(dom, rules, ignore_patterns(config))
            records = sorted(dom.data["index"].items(), key=lambda i: i[1]["reference"])
            for path, record in records:
                checker.check(path, record)
            checker.pages(self.env)
        findings = checker.findings if checker else []
        summary = _summary(enabled, rules, checker)
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
        if checker:
            _warn_parsed(dom, checker.parsed)
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
    """``build-finished``: exit status 1 when an ``error`` rule found something."""
    builder = app.builder
    if (
        exception is None
        and isinstance(builder, MatlabApiCheckBuilder)
        and builder.errors
    ):
        app.statuscode = 1
