"""Tests for tree-sitter helpers in ``mat_tree_sitter_parser``."""

from tree_sitter import Parser

from sphinxcontrib.mat_tree_sitter_parser import ML_LANG


def test_point_row_is_stable_beyond_small_int_cache():
    # Rows above 256 are not cached small ints. tree-sitter 0.26.0's
    # ``Point.row`` returned a borrowed reference for them; repeated reads
    # corrupted the heap and crashed (SIGSEGV) on standard CPython builds.
    # Fixed in 0.26.1 (py-tree-sitter afb3836), the minimum pinned version.
    tree = Parser(ML_LANG).parse(b"\n" * 300 + b"x = 1;\n")
    for _ in range(10000):
        rows = [tree.root_node.end_point.row for _ in range(10)]
        assert rows == [301] * 10
