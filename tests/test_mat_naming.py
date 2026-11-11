"""Tests for centralized MATLAB naming helpers."""

import dataclasses
import json
import os
import random
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sphinx.errors import ConfigError

from sphinxcontrib import matlab
from sphinxcontrib.mat_naming import (
    DEFAULT_MATLAB_VERSION,
    MATLAB_VERSION_FLOOR,
    MATLAB_VERSION_RULES,
    MatlabName,
    canonical_name,
    default_namelengthmax,
    folder_namespace,
    folder_of,
    form_matlab_name,
    has_matlab_behavior,
    is_private_reference,
    is_valid_identifier,
    join_reference,
    make_target_id,
    not_callable_reason,
    parse_reference,
    split_display,
    validate_matlab_version,
)


def _native(name):
    """Return ``name`` with ``parent_folder`` as a native file system path."""
    if name is None:
        return None
    return dataclasses.replace(name, parent_folder=os.path.normpath(name.parent_folder))


def test_form_matlab_name_reference_cases():
    rows = [
        ("/tmp", "demo.m", False, MatlabName("demo", "", "demo", "/tmp")),
        (
            "/tmp/+pkg",
            "demo.m",
            False,
            MatlabName("demo", "pkg", "pkg.demo", "/tmp"),
        ),
        (
            "/tmp/+pkg/+sub",
            "demo.m",
            False,
            MatlabName("demo", "pkg.sub", "pkg.sub.demo", "/tmp"),
        ),
        (
            "/tmp/@Class",
            "Class.m",
            True,
            MatlabName("Class", "Class", "Class", "/tmp/@Class"),
        ),
        (
            "/tmp/+pkg/@Class",
            "helper.m",
            False,
            MatlabName("helper", "pkg.Class", "helper", "/tmp"),
        ),
        ("/tmp/@Class/end", "x.m", False, None),
        (
            "/tmp/@Class",
            "end.m",
            False,
            MatlabName("end", "Class", "end", "/tmp/@Class"),
        ),
        ("/tmp/@Class/sub", "x.m", False, None),
        ("/tmp/+pkg/@Class/sub", "x.m", True, None),
        (
            "/tmp/+pkg/private",
            "pf.m",
            False,
            MatlabName("pf", "", "pf", "/tmp/+pkg/private", True),
        ),
        (
            "/tmp/@C/private",
            "cp.m",
            False,
            MatlabName("cp", "", "cp", "/tmp/@C/private", True),
        ),
        ("/tmp/private", "PrivCls.m", True, None),
        ("/tmp/@C/sub/private", "x.m", False, None),
        ("/tmp/private/private", "x.m", False, None),
        ("/tmp/+1bad/private", "x.m", False, None),
        (
            "/tmp/private/mcode",
            "tut.m",
            False,
            MatlabName("tut", "", "tut", "/tmp/private/mcode"),
        ),
    ]

    for folder, name, is_class, expected in rows:
        out = form_matlab_name(folder, name, is_class, namelengthmax=63)
        assert out == _native(expected)


def test_form_matlab_name_invalid_package_dropped():
    out = form_matlab_name("/tmp/+1bad", "demo.m", False, namelengthmax=63)
    assert out is None


def test_form_matlab_name_class_folder_under_invalid_package_dropped():
    assert form_matlab_name("/tmp/+for/@C", "m.m", False, namelengthmax=63) is None
    assert form_matlab_name("/tmp/+1bad/@C", "C.m", True, namelengthmax=63) is None
    assert (
        form_matlab_name("/tmp/+1bad/@C/private", "p.m", False, namelengthmax=63)
        is None
    )


@pytest.mark.parametrize(
    ("folder", "name", "is_class"),
    [
        ("", "f.m", False),
        ("/tmp/+", "f.m", False),
        ("/tmp/@", "f.m", False),
        ("/tmp/@Outer/@Inner", "Inner.m", True),
        ("/tmp/@C/+pkg/@D", "D.m", True),
        ("/tmp/@C", "bad-name.m", False),
    ],
)
def test_form_matlab_name_not_callable(folder, name, is_class):
    assert form_matlab_name(folder, name, is_class, namelengthmax=2048) is None


@pytest.mark.parametrize(
    ("folder", "name", "is_class", "version", "reason"),
    [
        ("/tmp", "bad-name.m", False, "R2026a", "its name 'bad-name' is not a"),
        ("/tmp", "end.m", False, "R2026a", "its name 'end' is a MATLAB keyword"),
        ("/tmp", "a" * 64 + ".m", False, "R2026a", "is longer than 63 characters"),
        ("/tmp/+for", "f.m", False, "R2026a", "folder name 'for' is a MATLAB"),
        ("/tmp/+1bad/@C", "C.m", True, "R2026a", "folder name '1bad' is not"),
        ("/tmp/@O/@I", "I.m", True, "R2026a", "class folder @I is inside a class"),
        ("/tmp/@C/+p", "f.m", False, "R2026a", "namespace folder +p is inside"),
        ("/tmp/@C/sub", "f.m", False, "R2026a", "not callable since R2026a"),
        ("/tmp/@C/sub", "D.m", True, "R2025b", "classes in subfolders of a class"),
        ("/tmp/@C", "D.m", True, "R2026a", "a class in @C must be named C"),
        ("/tmp/@C/sub", "a-b.m", False, "R2025b", "its name 'a-b' is not"),
        ("", "f.m", False, "R2026a", "MATLAB cannot form a name for it"),
    ],
)
def test_not_callable_reason(folder, name, is_class, version, reason):
    assert form_matlab_name(folder, name, is_class, 63, version) is None
    assert reason in not_callable_reason(folder, name, is_class, 63, version)


def test_form_matlab_name_of_a_relative_package_folder():
    out = form_matlab_name("+pkg", "f.m", False, namelengthmax=2048)
    assert out is not None
    assert (out.pseudo_fullname, out.parent_folder) == ("pkg.f", "")


def test_form_matlab_name_keyword_top_package_invalid():
    out = form_matlab_name("/tmp/+for/+nested", "demo.m", False, namelengthmax=63)
    assert out is None


def test_form_matlab_name_keyword_nested_package_valid():
    out = form_matlab_name("/tmp/+pkg/+for", "demo.m", False, namelengthmax=63)
    assert out == _native(MatlabName("demo", "pkg.for", "pkg.for.demo", "/tmp"))


def test_identifier_validation_respects_namelengthmax():
    name_63 = "a" + ("b" * 62)
    name_64 = "a" + ("b" * 63)

    assert is_valid_identifier(name_63, 63, allow_keywords=False)
    assert not is_valid_identifier(name_64, 63, allow_keywords=False)
    assert is_valid_identifier(name_64, 2048, allow_keywords=False)


def test_ensure_configuration_derives_namelengthmax_from_version():
    env = _config("R2025a")
    matlab.ensure_configuration(_APP, env)
    assert default_namelengthmax(env.matlab_version) == 2048


@pytest.mark.parametrize("value", [True, False, "", "typo", 1, []])
def test_auto_link_rejects_invalid_values(value):
    config = _config()
    config.matlab_auto_link = value
    with pytest.raises(ConfigError, match="matlab_auto_link"):
        matlab.ensure_configuration(_APP, config)


@pytest.mark.parametrize("version", ["R2023b", "2026a", "R2026c", "r2026a", None])
def test_ensure_configuration_rejects_bad_matlab_version(version):
    env = _config(version)
    with pytest.raises(ConfigError, match="matlab_version"):
        matlab.ensure_configuration(_APP, env)


@pytest.mark.parametrize("name", ["matlab_keep_package_prefix", "matlab_short_links"])
@pytest.mark.parametrize("value", [True, False])
def test_ensure_configuration_rejects_removed_options(name, value):
    env = _config()
    setattr(env, name, value)
    with pytest.raises(ConfigError, match=f"{name} was removed"):
        matlab.ensure_configuration(_APP, env)


def test_matlab_version_rules():
    assert validate_matlab_version("R2024a") == "R2024a"
    assert validate_matlab_version("R2025a") == "R2025a"
    assert validate_matlab_version("R2027b") == "R2027b"
    assert default_namelengthmax("R2024a") == 63
    assert default_namelengthmax("R2024b") == 63
    assert default_namelengthmax("R2025a") == 2048
    assert default_namelengthmax("R2026a") == 2048


@pytest.mark.parametrize(
    ("folder", "name", "is_class", "expected"),
    [
        ("/tmp/@C/sub", "x.m", False, MatlabName("x", "", "x", "/tmp/@C/sub")),
        (
            "/tmp/@C/sub/deeper",
            "x.m",
            False,
            MatlabName("x", "", "x", "/tmp/@C/sub/deeper"),
        ),
        (
            "/tmp/+pkg/@C/sub",
            "x.m",
            False,
            MatlabName("x", "", "x", "/tmp/+pkg/@C/sub"),
        ),
        ("/tmp/@C/sub", "K.m", True, None),
        ("/tmp/@C/sub/private", "y.m", False, None),
        ("/tmp/@C/sub/+p", "f.m", False, None),
    ],
)
def test_class_subfolder_callable_before_r2026a(folder, name, is_class, expected):
    for version in ("R2024a", "R2024b", "R2025a", "R2025b"):
        assert form_matlab_name(folder, name, is_class, 2048, version) == _native(
            expected
        )
    assert form_matlab_name(folder, name, is_class, 2048, "R2026a") is None


# --- form_matlab_name reference tests ----------------------------------------
# The reference tests use a table that drops rows without a name;
# form_matlab_name returns None for those rows, so ``_form_matlab_names``
# builds the same table.


def _form_matlab_names(rows, version="R2026a"):
    out = {}
    for folder, name, is_class in rows:
        result = form_matlab_name(folder, name, is_class, 2048, version)
        if result is not None:
            out[(folder, name)] = result
    return out


DERIVE_ROWS = [
    ("/tmp", "demo.m", False),
    ("/tmp/+pkg", "demo.m", False),
    ("/tmp/+pkg/+sub", "demo.m", False),
    ("/tmp/@Class", "Class.m", True),
    ("/tmp/+pkg/@Class", "helper.m", False),
    ("/tmp/@Class/sub", "helper.m", False),
    ("/tmp/+pkg/@Class/sub", "helper.m", False),
]


def _triple(n):
    return n.pseudo_name, n.pseudo_package, n.pseudo_fullname


def test_form_matlab_name_derives_pseudo_names_and_packages():
    # The reference tests predate R2026a: @Class/sub files are callable there.
    out = _form_matlab_names(DERIVE_ROWS, "R2025b")
    assert len(out) == 7
    assert _triple(out["/tmp", "demo.m"]) == ("demo", "", "demo")
    assert _triple(out["/tmp/+pkg", "demo.m"]) == ("demo", "pkg", "pkg.demo")
    assert _triple(out["/tmp/+pkg/+sub", "demo.m"]) == (
        "demo",
        "pkg.sub",
        "pkg.sub.demo",
    )
    assert _triple(out["/tmp/@Class", "Class.m"]) == ("Class", "Class", "Class")
    assert _triple(out["/tmp/+pkg/@Class", "helper.m"]) == (
        "helper",
        "pkg.Class",
        "helper",
    )
    assert _triple(out["/tmp/@Class/sub", "helper.m"]) == ("helper", "", "helper")
    assert _triple(out["/tmp/+pkg/@Class/sub", "helper.m"]) == ("helper", "", "helper")


def test_form_matlab_name_derives_without_class_subfolders_from_r2026a():
    out = _form_matlab_names(DERIVE_ROWS, "R2026a")
    assert set(out) == {(f, n) for f, n, _ in DERIVE_ROWS[:5]}


def test_form_matlab_name_uses_constructor_token_for_class_definitions_in_packages():
    out = _form_matlab_names(
        [("/tmp/+pkg", "Class.m", True), ("/tmp/+pkg/@Class", "Class.m", True)]
    )
    assert len(out) == 2
    for key in out:
        assert out[key].pseudo_package == "pkg.Class"
        assert out[key].pseudo_fullname == "pkg.Class"


def test_form_matlab_name_errors_when_required_columns_missing():
    with pytest.raises(TypeError):
        cast(Any, form_matlab_name)("/tmp", "demo.m")


def test_form_matlab_name_warns_and_drops_files_with_invalid_package_path():
    out = _form_matlab_names(
        [("/tmp", "demo.m", False), ("/tmp/+1bad", "demo.m", False)]
    )
    assert [n.pseudo_fullname for n in out.values()] == ["demo"]


def test_form_matlab_name_warns_and_drops_class_nested_and_keyword_packages():
    rows = [
        ("/tmp", "demo.m", False),
        ("/tmp/@Class/+pkg", "demo.m", False),
        ("/tmp/+for", "demo.m", False),
    ]
    for version in ("R2025a", "R2026a"):
        out = _form_matlab_names(rows, version)
        assert [n.pseudo_fullname for n in out.values()] == ["demo"]


def test_form_matlab_name_allows_keyword_method_names_in_folder_classes():
    out = _form_matlab_names(
        [("/tmp/@Class", "end.m", False), ("/tmp/+pkg/@Class", "end.m", False)]
    )
    assert _triple(out["/tmp/@Class", "end.m"]) == ("end", "Class", "end")
    assert _triple(out["/tmp/+pkg/@Class", "end.m"]) == ("end", "pkg.Class", "end")


# --- R2026a oracle (reference/matlab_names_reference.json) -------------------

_ORACLE_EDGE_CASES = json.loads(
    (Path(__file__).parent / "naming_oracle_edge_cases.json").read_text()
)
# form_matlab_name, like the reference, names an old-style constructor in a
# package class folder; R2026a does not call it. Kept on purpose.
_KNOWN_DIVERGENCES = {("/oracle/+pkg/@Old2", "Old2.m")}


def _oracle_check(row):
    out = form_matlab_name(row["folder"], row["name"], row["is_class"], 2048, "R2026a")
    got = (
        (out.pseudo_name, out.pseudo_package, out.pseudo_fullname, out.is_private)
        if out
        else ("", "", "", False)
    )
    expected = (
        row["exp_pseudo_name"],
        row["exp_pseudo_package"],
        row["exp_pseudo_full_name"],
        row["is_private"],
    )
    return got, expected


@pytest.mark.parametrize(
    "row",
    [
        pytest.param(
            row,
            id=f"{row['folder']}/{row['name']}",
            marks=[pytest.mark.xfail(strict=True)]
            if (row["folder"], row["name"]) in _KNOWN_DIVERGENCES
            else [],
        )
        for row in _ORACLE_EDGE_CASES
        if not row["ignore"]
    ],
)
def test_oracle_edge_cases(row):
    got, expected = _oracle_check(row)
    assert got == expected


# --- Spaces, invalid identifiers, keywords and both length limits ------------


@pytest.mark.parametrize(
    ("folder", "name", "is_class", "expected"),
    [
        ("/tmp/my folder", "demo.m", False, "demo"),
        ("/tmp/my folder/+pkg", "demo.m", False, "pkg.demo"),
        ("/tmp/+my pkg", "demo.m", False, None),
        ("/tmp", "my file.m", False, None),
        ("/tmp/@My Class", "My Class.m", True, None),
        ("/tmp/+pkg", "bad-name.m", False, None),
        ("/tmp/+pkg", "_x.m", False, None),
        ("/tmp/+pkg", "for.m", False, None),
        ("/tmp/+pkg/@C", "for.m", False, "for"),
        ("/tmp/class", "C.m", True, "C"),
        # Python keywords are ordinary MATLAB identifiers.
        ("/tmp/+lambda/+import", "def.m", False, "lambda.import.def"),
        ("/tmp/+None/@pass", "pass.m", True, "None.pass"),
        ("/tmp/import/from", "yield.m", False, "yield"),
    ],
)
def test_form_matlab_name_spaces_and_invalid_identifiers(
    folder, name, is_class, expected
):
    out = form_matlab_name(folder, name, is_class, 2048)
    assert (out.pseudo_fullname if out else None) == expected


@pytest.mark.parametrize("length", [63, 64, 2048, 2049])
def test_form_matlab_name_both_length_limits(length):
    ident = "a" * length
    for folder, name, is_class, expected in [
        (f"/tmp/+{ident}", "f.m", False, f"{ident}.f"),
        ("/tmp/+pkg", f"{ident}.m", False, f"pkg.{ident}"),
        (f"/tmp/@{ident}", f"{ident}.m", True, ident),
    ]:
        for limit in (63, 2048):
            out = form_matlab_name(folder, name, is_class, limit)
            want = expected if length <= limit else None
            assert (out.pseudo_fullname if out else None) == want


# --- matlab_version / namelengthmax ------------------------------------------


_APP = SimpleNamespace(srcdir=".")


def _config(version="R2026a"):
    return SimpleNamespace(
        matlab_short_links=None,
        matlab_keep_package_prefix=None,
        matlab_src_dir=None,
        matlab_src_code_project_root=None,
        matlab_src_include_patterns=["**/*"],
        matlab_src_exclude_patterns=[],
        matlab_src_sidecar_suffixes=[],
        matlab_src_encoding=None,
        matlab_version=version,
        matlab_auto_link=None,
    )


@pytest.mark.parametrize(
    ("version", "expected"),
    [("R2024a", 63), ("R2024b", 63), ("R2025a", 2048), ("R2026a", 2048)],
)
def test_namelengthmax_follows_version(version, expected):
    assert default_namelengthmax(version) == expected


def test_version_rules_table_drives_defaults(monkeypatch):
    # Thresholds live only in MATLAB_VERSION_RULES.
    monkeypatch.setitem(MATLAB_VERSION_RULES, "namelengthmax_2048", "R2026a")
    assert default_namelengthmax("R2025b") == 63
    assert has_matlab_behavior("class_subfolder_not_callable", "R2026a")
    assert not has_matlab_behavior("class_subfolder_not_callable", "R2025b")
    assert MATLAB_VERSION_FLOOR == "R2024a"
    assert DEFAULT_MATLAB_VERSION == "R2026a"


# --- Path references and anchors ----------------------------------------------


def _decode_target_id(anchor):
    assert anchor.startswith("mat-")
    body, out, i = anchor[4:], bytearray(), 0
    while i < len(body):
        if body[i] == "~":
            out.append(int(body[i + 1 : i + 3], 16))
            i += 3
        else:
            out.extend(body[i].encode("utf-8"))
            i += 1
    return out.decode("utf-8")


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        ("target/+package/ClassBar.m", ("target/+package/ClassBar.m", [])),
        (
            "target/+package/ClassBar.m.myMethod",
            ("target/+package/ClassBar.m", ["myMethod"]),
        ),
        ("Cls.m.Inner.prop", ("Cls.m", ["Inner", "prop"])),
        ("apps/My App.mlapp", ("apps/My App.mlapp", [])),
        ("a.m/b/F.m.x", ("a.m/b/F.m", ["x"])),  # folder named like a file
        ("target/+package/", ("target/+package/", [])),
        ("./", ("./", [])),
        ("target/x.mat", (None, [])),
        ("package.ClassBar", (None, [])),
        ("target/+package", (None, [])),
        ("Cls.m.", (None, [])),
        (".m", (None, [])),
    ],
)
def test_parse_reference(reference, expected):
    assert parse_reference(reference) == expected


def test_parse_reference_with_given_extensions():
    assert parse_reference("a/M.slx.x", extensions=(".slx",)) == ("a/M.slx", ["x"])
    assert parse_reference("a/F.m", extensions=(".slx",)) == (None, [])


@pytest.mark.parametrize(
    ("reference", "anchor"),
    [
        ("target/+package/ClassBar.m", "mat-target/+package/ClassBar.m"),
        ("target/+package/", "mat-target/+package/"),
        ("src/@Cls/Cls.m.myMethod", "mat-src/@Cls/Cls.m.myMethod"),
        ("my folder/f.m", "mat-my~20folder/f.m"),
        ("a#b%c~d/f.m", "mat-a~23b~25c~7Ed/f.m"),
        ('q"<>\\^`{|}/f.m', "mat-q~22~3C~3E~5C~5E~60~7B~7C~7D/f.m"),
        ("tab\there\x7f/f.m", "mat-tab~09here~7F/f.m"),
        ("café/漢字.m", "mat-café/漢字.m"),
        ("ok-._!$&'()*+,;=:@/f.m", "mat-ok-._!$&'()*+,;=:@/f.m"),
    ],
)
def test_make_target_id_escapes(reference, anchor):
    assert make_target_id(reference) == anchor
    assert _decode_target_id(anchor) == reference


def test_target_ids_are_unique():
    # The escape is reversible, so distinct references never share an anchor.
    tricky = [
        "x/Cls.m",
        "x/Cls.m/",  # a folder next to a file with the same name
        "x/Cls.m.meth",
        "x/Cls.m.meth/",
        "my folder/f.m",
        "my~20folder/f.m",
        "my-folder/f.m",
        "a~7E/f.m",
        "a~/f.m",
        "./",
        "f.m",
    ]
    rng = random.Random(0)
    alphabet = [chr(c) for c in range(0x00, 0x80)] + list("é 漢😀")
    refs = set(tricky)
    for _ in range(5000):
        refs.add("".join(rng.choice(alphabet) for _ in range(rng.randint(1, 6))))
    anchors = {make_target_id(ref) for ref in refs}
    assert len(anchors) == len(refs)
    assert all(_decode_target_id(make_target_id(ref)) == ref for ref in refs)
    for anchor in anchors:
        assert not any(c.isspace() and ord(c) < 0x80 for c in anchor)


def test_folder_next_to_same_named_file():
    # A folder named like a file: its reference ends with "/".
    folder, nested = "x/Cls.m/", "x/Cls.m/f.m"
    assert parse_reference(folder) == ("x/Cls.m/", [])
    assert parse_reference(nested) == ("x/Cls.m/f.m", [])
    assert make_target_id(folder) != make_target_id("x/Cls.m")


def test_canonical_name_qualifies_class_folder_methods():
    assert canonical_name(MatlabName("helper", "pkg.C", "helper", "/t")) == (
        "pkg.C.helper"
    )
    assert canonical_name(MatlabName("C", "pkg.C", "pkg.C", "/t")) == "pkg.C"
    assert canonical_name(MatlabName("f", "pkg", "pkg.f", "/t")) == "pkg.f"
    assert canonical_name(MatlabName("Old", "Old", "Old", "/t")) == "Old"
    assert canonical_name(MatlabName("f", "", "f", "/t", True)) == "f"


@pytest.mark.parametrize(
    ("reference", "folder", "private"),
    [
        ("f.m", "./", False),
        ("./", "./", False),
        ("target/+package/ClassBar.m.myMethod", "target/+package/", False),
        ("target/+package/", "target/+package/", False),
        ("src/private/helper.m", "src/private/", True),
        ("src/private/", "src/private/", True),
        ("a.m/f.m", "a.m/", False),
        ("privateer/f.m", "privateer/", False),
    ],
)
def test_folder_of_and_private(reference, folder, private):
    assert folder_of(reference) == folder
    assert is_private_reference(reference) is private


def test_join_reference_and_split_display():
    assert join_reference("./", "f.m") == "f.m"
    assert join_reference("src/", "f.m") == "src/f.m"
    assert split_display("package.ClassBar") == ("package.", "ClassBar")
    assert split_display("ClassBar") == ("", "ClassBar")
    assert split_display("+for/nm_kw.m") == ("+for/", "nm_kw.m")
    assert split_display("target/+package/") == ("target/", "+package/")
    assert split_display("./") == ("", "./")


@pytest.mark.parametrize(
    ("folder", "expected"),
    [
        ("/r/+pkg", "pkg"),
        ("/r/+pkg/+sub", "pkg.sub"),
        ("/r/src", None),
        ("/r/+for", None),  # keyword
        ("/r/+pkg/+for", "pkg.for"),  # keywords only fail the first level
        ("/r/@Cls/+pkg", None),  # below a class folder
    ],
)
def test_folder_namespace(folder, expected):
    assert folder_namespace(folder, 2048) == expected
