import importlib.metadata as md
from pathlib import Path
from typing import Any, cast

import tree_sitter_matlab as tsml
from tree_sitter import Language, Parser

FILE = str(
    Path(__file__).resolve().parents[2]
    / "gauntlet/repos/vhlab-toolbox-matlab/+vlt/+plot/hist2d.m"
)
Q = r"""(function_definition
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
    ) @prop_node"""
lang = Language(tsml.language())
tree = Parser(lang).parse(Path(FILE).read_bytes())
print(
    "tree-sitter",
    md.version("tree-sitter"),
    "tree-sitter-matlab",
    md.version("tree-sitter-matlab"),
)
root = tree.root_node
print("root has_error:", root.has_error)
fd = [c for c in root.children if c.type == "function_definition"]
print("top-level children types:", [c.type for c in root.children][:25])
if fd:
    f = fd[0]
    print("function_definition children (first 8):")
    for c in f.children[:8]:
        print(
            "   ",
            c.type,
            repr(cast(bytes, c.text)[:60]),
            "field=",
            f.field_name_for_child(f.children.index(c))
            if hasattr(f, "field_name_for_child")
            else "?",
        )
    nm = f.child_by_field_name("name")
    print(
        "child_by_field_name('name'):", nm.type if nm else None, nm.text if nm else None
    )
if hasattr(lang, "query") and md.version("tree-sitter").startswith("0.22"):
    caps = cast(Any, lang).query(Q).captures(fd[0] if fd else root)
    names = {}
    for n, k in caps:
        names.setdefault(k, []).append(n.text[:40])
else:
    from tree_sitter import Query, QueryCursor

    names = {
        k: [cast(bytes, n.text)[:40] for n in v]
        for k, v in QueryCursor(Query(lang, Q)).captures(fd[0] if fd else root).items()
    }
print(
    "captures:",
    {k: v for k, v in names.items() if k != "prop_node"},
    "prop_node count:",
    len(names.get("prop_node", [])),
)
