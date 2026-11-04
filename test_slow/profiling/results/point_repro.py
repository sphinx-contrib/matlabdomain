"""Minimal tree-sitter Point.row crash repro: python point_repro.py row|index."""

import sys

import tree_sitter_matlab
from tree_sitter import Language, Parser

mode = sys.argv[1]
p = Parser(Language(tree_sitter_matlab.language()))
tree = p.parse(b"\n" * 300 + b"% comment\nx=1;\n")
for i in range(10000):
    if mode == "row":
        rows = [tree.root_node.end_point.row for _ in range(10)]
    else:
        rows = [tree.root_node.end_point[0] for _ in range(10)]
    assert rows == [302] * 10, (i, rows[:3])
print("ok")
