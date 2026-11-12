"""Names, anchors and the inventory as properties (G4-T4).

(a) ``objects.inv`` read back with Sphinx's loader holds the objects of the
domain; (b) seeded random checks of the naming functions; (c) which added
sibling changes an existing output name.
"""

import random
import shutil
import unicodedata
from pathlib import Path
from urllib.parse import quote, unquote

import pytest
from test_intersphinx import inventory

from sphinxcontrib import mat_urls
from sphinxcontrib.mat_naming import make_target_id, parse_reference
from sphinxcontrib.matlab_apidoc._names import docnames

SLX = Path(__file__).parent / "simulink" / "fixtures" / "R2026b" / "slx"

# --- (a) the inventory ----------------------------------------------------

AWKWARD = [
    "with space",
    "hash#tag",
    "cost$",
    "café",
    "tab\\tstop",
    "100%",
    "über$",
]


def _mdl(names):
    blocks = "".join(
        "    Block {\n      BlockType SubSystem\n"
        f'      MaskType "T"\n      MaskDescription "d"\n      Name "{n}"\n    }}\n'
        for n in names
    )
    return f"Library {{\n  System {{\n{blocks}  }}\n}}\n"


def _build(make_app, tmp_path, names, conf="", with_probe_lib=False):
    """Build a library ``odd.mdl`` whose blocks are ``names`` (as an MDL
    string body); return ``(outdir, mat objects, warnings)``.
    """
    src = tmp_path / "src"
    src.mkdir(parents=True)
    (src / "odd.mdl").write_bytes(_mdl(names).encode("utf-8"))
    index = ".. mat:autosimulink_library:: odd\n   :members:\n"
    if with_probe_lib:
        shutil.copyfile(SLX / "probeLib.slx", src / "probeLib.slx")
        index += "\n.. mat:autosimulink_library:: probeLib\n   :members:\n"
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\n'
        f'matlab_src_code_project_root = "src"\n{conf}'
    )
    (tmp_path / "index.rst").write_text(f"Index\n=====\n\n{index}")
    app = make_app(srcdir=tmp_path, freshenv=True)
    app.build(force_all=True)
    domain = app.env.get_domain("mat")
    objects = list(domain.get_objects())
    stable = mat_urls.addresses(domain)[0]
    app.cleanup()
    return Path(app.outdir), objects, stable, app.warning.getvalue()


def _control(name):
    return [c for c in name if unicodedata.category(c).startswith("C")]


@pytest.mark.parametrize("stable", [True, False])
def test_inventory_holds_the_objects_of_awkward_names(make_app, tmp_path, stable):
    outdir, objects, by_ref, warnings = _build(
        make_app, tmp_path, AWKWARD, f"matlab_stable_urls = {stable}\n"
    )
    assert warnings == ""
    inv = inventory(outdir)
    assert set(inv) == {o[0] for o in objects}
    assert len(inv) == len(AWKWARD) + 1
    for name, display, _type, _doc, anchor, _prio in objects:
        uri, shown = inv[name]
        assert shown == display
        if stable:
            assert uri == quote(by_ref[name])
            assert (outdir / unquote(uri)).is_file()
        else:
            assert uri == f"index.html#{anchor}"


# Sphinx's loader ends a line at every str.splitlines() break. An .mdl file
# with any other such character in a name does not parse at all, so only
# these two (written as MDL escapes) reach the inventory.
BREAKS = ["\\n", "\\r"]


@pytest.mark.parametrize(
    "sep",
    BREAKS,
    ids=[repr(s.encode().decode("unicode_escape")) for s in BREAKS],
)
def test_inventory_names_survive_a_line_break(make_app, tmp_path, sep):
    outdir, objects, _, _ = _build(make_app, tmp_path, [f"Two{sep}Lines", "Plain"])
    names = {o[0] for o in objects}
    assert names == {"odd.mdl", "odd.mdl/Two Lines", "odd.mdl/Plain"}
    inv = inventory(outdir)
    assert set(inv) == names
    uri, shown = inv["odd.mdl/Two Lines"]
    assert uri.startswith("mat/ref/")
    assert (outdir / unquote(uri)).is_file()
    assert "\n" not in shown and "\r" not in shown
    assert not [n for n in inv if _control(n)]


@pytest.mark.parametrize("names", [["A\\nB", "A B"], ["A B", "A\\nB"]])
def test_blocks_that_collapse_to_one_name_keep_the_plain_one(make_app, tmp_path, names):
    # "A\nB" and "A B" are both written "odd.mdl/A B" by a role: the block
    # that has that name keeps the entry, the other has none (whatever the
    # order); every reference keeps its anchor.
    outdir, objects, _, _ = _build(make_app, tmp_path, names)
    assert sorted(o[0] for o in objects) == ["odd.mdl", "odd.mdl/A B"]
    uri, _ = inventory(outdir)["odd.mdl/A B"]
    assert uri == "mat/ref/odd.mdl~2FA~20B.html"  # not the other block's


def test_inventory_of_the_fixture_library_with_a_line_break(make_app, tmp_path):
    # probeLib.slx has the block "Two\nLines" (as in test_simulink_docs.py).
    outdir, objects, _, _ = _build(make_app, tmp_path, ["Plain"], with_probe_lib=True)
    assert set(inventory(outdir)) == {o[0] for o in objects}


# --- (b) names as properties ----------------------------------------------

LETTERS = list("aZ_-9")
ODD = [*"~%#+@./ \n", "//", "\u00e9", "\u2028", "\x00", "\U0001f600", "e\u0301"]
SEGMENTS = [*"aB+p@C", "x y", "~", "%", "#", "a.b", "é", "é", "a\nb", "1"]
EXTENSIONS = [".m", ".mlapp", ".slx", ".mdl"]
MEMBERS = ["m", "get", "x1", "a b", "é", "~", "#", "a\nb"]


def _decode(anchor):
    """Inverse of ``make_target_id``."""
    assert anchor.startswith("mat-")
    out, raw, i = [], bytearray(), 4
    while i < len(anchor):
        if anchor[i] == "~":
            raw.append(int(anchor[i + 1 : i + 3], 16))
            i += 3
            continue
        if raw:
            out.append(raw.decode("utf-8"))
            raw.clear()
        out.append(anchor[i])
        i += 1
    if raw:
        out.append(raw.decode("utf-8"))
    return "".join(out)


def test_target_id_is_injective_and_decodable():
    rng = random.Random(4001)
    alphabet = LETTERS + ODD
    seen = {}
    for _ in range(20000):
        ref = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 12)))
        anchor = make_target_id(ref)
        assert seen.setdefault(anchor, ref) == ref
        assert _decode(anchor) == ref
    assert len(seen) > 15000


def test_parse_reference_round_trips():
    rng = random.Random(4002)
    for _ in range(20000):
        folders = [rng.choice(SEGMENTS) for _ in range(rng.randint(0, 3))]
        ext = rng.choice(EXTENSIONS)
        file = "/".join([*folders, rng.choice(SEGMENTS) + ext])
        if ext in (".slx", ".mdl") and rng.random() < 0.7:
            parts = [rng.choice(SEGMENTS) for _ in range(rng.randint(1, 3))]
            block = "/".join(p.replace("/", "//") for p in parts)
            ref, expected = f"{file}/{block}", (file, [block])
        else:
            members = [rng.choice(MEMBERS) for _ in range(rng.randint(0, 3))]
            ref, expected = ".".join([file, *members]), (file, members)
        assert parse_reference(ref) == expected, ref


def _random_reference(rng, pool):
    folders = [rng.choice(pool) for _ in range(rng.randint(0, 3))]
    base = "/".join(folders) + "/" if folders else ""
    kind = rng.random()
    if kind < 0.3:
        return base or "./"
    file = base + rng.choice(pool) + rng.choice([".m", ".slx", ".mlapp"])
    if kind < 0.6:
        return file
    if file.endswith(".slx"):
        return file + "/" + rng.choice(["G", "g", "a b", "x//y"])
    return file + "." + rng.choice(["meth", "Meth", "a b"])


def test_docnames_are_injective_and_do_not_clash_by_case():
    rng = random.Random(4003)
    pool = ["a", "A", "+p", "+P", "_u", "~u", "b.m", "B.M", "x.rst", "x.m", "x.m.html"]
    pool += ["CON", "con", "a b", "é", "é", "a~b", "a.", "index", "Index"]
    pool += ["%", "#", "a\nb", "@C", "1"]
    checked = 0
    for _ in range(400):
        refs = sorted({_random_reference(rng, pool) for _ in range(50)})
        for suffix in ("rst", "html"):
            names, _ = docnames(refs, suffix)
            assert set(names) == set(refs)
            values = list(names.values())
            assert len(set(values)) == len(values)
            files = [f"{v}.{suffix}".lower() for v in values]
            folders = {
                "/".join(v.split("/")[:i]).lower()
                for v in values
                for i in range(1, v.count("/") + 1)
            }
            assert len(set(files)) == len(files)
            assert not folders & set(files)
            checked += len(refs)
    assert checked > 15000


# --- (c) a sibling that moves an existing address ---------------------------


def _moved(base, extra, suffix="html"):
    before, _ = docnames(base, suffix)
    after, _ = docnames([*base, *extra], suffix)
    return {ref: (before[ref], after[ref]) for ref in base if before[ref] != after[ref]}


@pytest.mark.parametrize(
    ("base", "extra", "moved"),
    [
        (["util/Foo.m"], ["util/foo.m"], {"util/Foo.m": "util/~46oo.m"}),
        (["Util/f.m"], ["util/g.m"], {"Util/f.m": "~55til/f.m"}),
        (["lib.slx/Gain"], ["lib.slx/gain"], {"lib.slx/Gain": "lib.slx~2~46~47ain"}),
        (["a/C.m.get"], ["a/C.m.Get"], {"a/C.m.get": "a/~43.m.get"}),
        (["Foo", "x"], ["foo"], {"Foo": "~46oo"}),
        (
            ["d/x.m.html/y.m"],
            ["d/x.m"],
            {"d/x.m.html/y.m": "d/x.m~2Ehtml/y.m"},
        ),
        (["d/x.m"], ["d/x.m.html/y.m"], {}),
        (["a/f.m"], ["a/g.m", "b/f.m", "a/f.m.meth"], {}),
    ],
)
def test_which_sibling_moves_an_address(base, extra, moved):
    assert {r: new for r, (_, new) in _moved(base, extra).items()} == moved
