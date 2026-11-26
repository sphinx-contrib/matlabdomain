"""Names, anchors and the inventory as properties.

(a) ``objects.inv`` read back with Sphinx's loader holds the objects of the
domain; (b) seeded random checks of the naming functions; (c) which added
sibling changes an existing output name.
"""

import random
from pathlib import Path
from urllib.parse import quote, unquote

import pytest
from test_apidoc import FUNCTION
from test_intersphinx import inventory

from sphinxcontrib import mat_urls
from sphinxcontrib.mat_naming import make_target_id, parse_reference
from sphinxcontrib.matlab_apidoc._names import docnames

# --- (a) the inventory ----------------------------------------------------

# File names every system accepts; none is a MATLAB identifier, so each
# function is documented by its path reference.
AWKWARD = [
    "with space",
    "hash#tag",
    "cost$",
    "café",
    "100%",
    "über$",
]


def _build(make_app, tmp_path, names, conf=""):
    """Build a project whose functions are the files ``names``; return
    ``(outdir, mat objects, stable addresses, warnings)``.
    """
    src = tmp_path / "src"
    src.mkdir(parents=True)
    for name in names:
        (src / f"{name}.m").write_text(FUNCTION.format(name="f"), encoding="utf-8")
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\n'
        'matlab_src_code_project_root = "src"\n'
        f'suppress_warnings = ["mat.not_callable"]\n{conf}',
        encoding="utf-8",
    )
    (tmp_path / "index.rst").write_text(
        "Index\n=====\n\n.. mat:autofolder:: ./\n   :members:\n", encoding="utf-8"
    )
    app = make_app(srcdir=tmp_path, freshenv=True)
    app.build(force_all=True)
    domain = app.env.get_domain("mat")
    objects = list(domain.get_objects())
    stable = mat_urls.addresses(domain)[0]
    app.cleanup()
    return Path(app.outdir), objects, stable, app.warning.getvalue()


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
        # an entry whose display name is its name has "-" for it
        assert shown == ("-" if display == name else display)
        if stable:
            assert uri == quote(by_ref[name])
            assert (outdir / unquote(uri)).is_file()
        else:
            assert uri == f"index.html#{anchor}"


# --- (b) names as properties ----------------------------------------------

LETTERS = list("aZ_-9")
ODD = [*"~%#+@./ \n", "//", "\u00e9", "\u2028", "\x00", "\U0001f600", "e\u0301"]
SEGMENTS = [*"aB+p@C", "x y", "~", "%", "#", "a.b", "é", "é", "a\nb", "1"]
EXTENSIONS = [".m", ".mlapp"]
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
        members = [rng.choice(MEMBERS) for _ in range(rng.randint(0, 3))]
        ref, expected = ".".join([file, *members]), (file, members)
        assert parse_reference(ref) == expected, ref


def _random_reference(rng, pool):
    folders = [rng.choice(pool) for _ in range(rng.randint(0, 3))]
    base = "/".join(folders) + "/" if folders else ""
    kind = rng.random()
    if kind < 0.3:
        return base or "./"
    file = base + rng.choice(pool) + rng.choice([".m", ".mlapp"])
    if kind < 0.6:
        return file
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
