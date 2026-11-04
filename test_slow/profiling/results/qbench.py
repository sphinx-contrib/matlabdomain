"""Version-agnostic tree-sitter microbenchmark (same files, same query text)."""

import importlib.metadata as md
import json
import platform
import sysconfig
import time
from pathlib import Path
from typing import Any, cast

import tree_sitter as ts
import tree_sitter_matlab as tsml

SRC = (
    Path(__file__).resolve().parents[2] / "gauntlet" / "repos" / "vhlab-toolbox-matlab"
)
Q_IS_FUNCTION = r"""(source_file [(comment) "\n"]* (function_definition))"""
Q_IS_CLASS = "(class_definition)"
Q_FUN = r"""(function_definition
    _*
        (function_output
            [(identifier) @outputs
             (multioutput_variable [[(identifier) (ignored_argument)] @outputs _]+)])?
    _*
    name: (identifier) @name
    _*
    (function_arguments [(identifier) @params (ignored_argument) @params _]*)?
    _*
    [(arguments_statement) @argblocks _]*
    .
    (comment)? @docstring
    )"""
lang = ts.Language(tsml.language())
new_api = hasattr(ts, "QueryCursor")


def compile_q(text):
    return ts.Query(lang, text) if new_api else cast(Any, lang).query(text)


def matches(q, node):
    return list(ts.QueryCursor(q).matches(node)) if new_api else q.matches(node)


def bench_compile(text, n):
    t = time.perf_counter()
    for _ in range(n):
        compile_q(text)
    return (time.perf_counter() - t) / n * 1e3


files = sorted(SRC.rglob("*.m"))
codes = [f.read_bytes() for f in files]
parser = ts.Parser(lang)
t = time.perf_counter()
trees = [parser.parse(c) for c in codes]
parse_s = time.perf_counter() - t
qf, qc = compile_q(Q_IS_FUNCTION), compile_q(Q_IS_CLASS)
t = time.perf_counter()
nf = sum(bool(matches(qf, tr.root_node)) for tr in trees)
nc = sum(bool(matches(qc, tr.root_node)) for tr in trees)
match_s = time.perf_counter() - t
t = time.perf_counter()
for _ in range(len(files)):
    md.version("tree_sitter")
meta_s = time.perf_counter() - t
print(
    json.dumps(
        {
            "python": platform.python_version(),
            "gil_disabled": bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
            "tree_sitter": md.version("tree-sitter"),
            "tree_sitter_matlab": md.version("tree-sitter-matlab"),
            "lang_abi": getattr(lang, "abi_version", getattr(lang, "version", None)),
            "compile_ms": {
                "is_function": round(bench_compile(Q_IS_FUNCTION, 100), 3),
                "is_class": round(bench_compile(Q_IS_CLASS, 100), 3),
                "q_fun": round(bench_compile(Q_FUN, 50), 3),
                "function_definition_at_f": round(
                    bench_compile("(function_definition) @f", 100), 3
                ),
            },
            "parse_all_s": round(parse_s, 3),
            "match_isfunc_isclass_all_s": round(match_s, 3),
            "n_function": nf,
            "n_class": nc,
            "metadata_version_x1726_s": round(meta_s, 3),
            "n_files": len(files),
        }
    )
)
