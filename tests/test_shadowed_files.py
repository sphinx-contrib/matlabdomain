"""Several objects of one MATLAB name: ``mat.ambiguous`` and no link, or,
with ``matlab_link_shadowed_files_to_chooser_pages``, a link to the page that lists them
(``mat/name/``), locally and through intersphinx.
"""

import zlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from docutils import nodes
from test_apidoc import FUNCTION, write
from test_intersphinx import BASE, build_consumer, build_library, write_inventory

from sphinxcontrib import mat_urls

USER = """\
function user
% USER Calls helper.
%
% See also helper
end
"""


def build(make_app, tmp_path, shadowed, builder="html", conf=""):
    """Build two global ``helper`` functions and a page that names them;
    return ``(page text, warnings, output folder)``.
    """
    write(
        tmp_path / "src",
        {
            "a/helper.m": FUNCTION.format(name="helper"),
            "b/helper.m": FUNCTION.format(name="helper"),
            "c/user.m": USER,
        },
    )
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\n'
        'matlab_src_code_project_root = "src"\n'
        'matlab_auto_link = "all"\n'
        f"matlab_link_shadowed_files_to_chooser_pages = {shadowed}\n{conf}"
    )
    (tmp_path / "index.rst").write_text(
        "Index\n=====\n\n.. mat:autofunction:: a/helper.m\n\n"
        ".. mat:autofunction:: b/helper.m\n\n.. mat:autofunction:: c/user.m\n\n"
        "* role: :mat:func:`helper`\n* any: :any:`helper`\n"
    )
    app = make_app(builder, srcdir=tmp_path, freshenv=True)
    app.build(force_all=True)
    app.cleanup()
    outdir = Path(app.outdir)
    page = next(outdir.glob("index.*")).read_text(encoding="utf-8")
    return page, app.warning.getvalue(), outdir


def test_ambiguous_names_stay_text(make_app, tmp_path):
    page, warnings, _ = build(make_app, tmp_path, False)
    assert 'href="mat/name/helper.html"' not in page
    # role, :any:, "See also" and the auto-link in the summary line
    assert warnings.count("matches several objects: a/helper.m, b/helper.m") == 4


def test_shadowed_names_link_to_their_list(make_app, tmp_path):
    page, warnings, outdir = build(make_app, tmp_path, True)
    assert warnings == ""
    assert page.count('href="mat/name/helper.html"') == 4
    chooser = (outdir / "mat" / "name" / "helper.html").read_text(encoding="utf-8")
    assert "a/helper.m" in chooser
    assert "b/helper.m" in chooser


@pytest.mark.parametrize(
    ("builder", "conf"), [("text", ""), ("html", "matlab_stable_urls = False\n")]
)
def test_shadowed_names_without_a_list_are_text(make_app, tmp_path, builder, conf):
    page, warnings, _ = build(make_app, tmp_path, True, builder, conf)
    assert warnings == ""
    assert "mat/name/" not in page


def test_inventory_lists_the_pages_of_shadowed_names(make_app, tmp_path):
    outdir = build_library(make_app, tmp_path / "lib")
    path = outdir / "objects.inv"
    with open(path, "rb") as f:
        body = f.read().split(b"\n", 4)[4]
    lines = zlib.decompress(body).decode("utf-8").splitlines()
    assert "helper mat:function -1 mat/name/helper.html -" in lines
    # A second rewrite replaces the entries.
    mat_urls.rewrite_inventory(path, {}, [("helper", "function", "mat/name/x.html")])
    with open(path, "rb") as f:
        body = f.read().split(b"\n", 4)[4]
    lines = zlib.decompress(body).decode("utf-8").splitlines()
    assert [line for line in lines if " -1 mat/name/" in line] == [
        "helper mat:function -1 mat/name/x.html -"
    ]


REFERENCES = {
    "name": ":mat:func:`helper`",
    "named": ":external+lib:mat:func:`helper`",
    "prefixed": ":mat:func:`lib:helper`",
    "other_type": ":mat:class:`helper`",
}


@pytest.mark.parametrize("shadowed", [False, True])
def test_other_sites_shadowed_names(make_app, tmp_path, shadowed):
    outdir = build_library(make_app, tmp_path / "lib")
    mapping = {"lib": (BASE, str(outdir / "objects.inv"))}
    links, warnings = build_consumer(
        make_app,
        tmp_path / "app",
        mapping,
        REFERENCES,
        f"matlab_link_shadowed_files_to_chooser_pages = {shadowed}\n",
    )
    chooser = f"{BASE}mat/name/helper.html"
    # Only functions have the name.
    assert links["other_type"] == (None, "helper")
    assert "mat:class reference target not found: helper" in warnings
    if shadowed:
        assert {k: links[k][0] for k in ("name", "named", "prefixed")} == dict.fromkeys(
            ("name", "named", "prefixed"), chooser
        )
        assert "ambiguous" not in warnings
    else:
        assert all(links[k][0] is None for k in ("name", "named", "prefixed"))
        assert (
            warnings.count(
                "'helper' matches several objects: examples/helper.m, "
                "toolbox/helper.m; use a path reference"
            )
            == 3
        )


@pytest.mark.parametrize("shadowed", [False, True])
def test_old_inventories_without_lists(make_app, tmp_path, shadowed):
    write_inventory(
        tmp_path / "old" / "objects.inv",
        "old",
        [
            ("a/f.m", "function", "api.html#mat-a/f.m", "f"),
            ("b/f.m", "function", "api.html#mat-b/f.m", "f"),
        ],
    )
    mapping = {
        "old": ("https://old.example.invalid/", str(tmp_path / "old/objects.inv"))
    }
    links, warnings = build_consumer(
        make_app,
        tmp_path / "app",
        mapping,
        {"name": ":mat:func:`f`"},
        f"matlab_link_shadowed_files_to_chooser_pages = {shadowed}\n",
    )
    assert links["name"] == (None, "f()")
    ambiguous = "'f' matches several objects: a/f.m, b/f.m" in warnings
    assert ambiguous is not shadowed
    assert "target not found" not in warnings


def test_chooser_uri():
    assert mat_urls.is_chooser_uri("https://x.invalid/docs/mat/name/f.html")
    assert mat_urls.is_chooser_uri("mat/name/f.html")
    assert not mat_urls.is_chooser_uri("https://x.invalid/mat/ref/f.m.html")
    assert not mat_urls.is_chooser_uri("https://x.invalid/format/name/f.html")


def test_no_chooser_page_lists_the_matches():
    # A private file of the same name is not on the page, nor is a name of
    # one public object.
    objects = {
        "a/f.m": ("api", "function", "f"),
        "b/f.m": ("api", "function", "f"),
        "a/private/f.m": ("api", "function", "f"),
        "a/g.m": ("api", "function", "g"),
        "a/private/g.m": ("api", "function", "g"),
    }
    names = {"f": ["a/f.m", "b/f.m"], "g": ["a/g.m"]}
    by_name = {"f": "mat/name/f.html", "g": "mat/name/g.html"}
    dom = SimpleNamespace(
        data={"objects": objects}, _stable_urls=({}, by_name, names, {})
    )
    builder = SimpleNamespace(
        config=SimpleNamespace(matlab_stable_urls=True),
        format="html",
        out_suffix=".html",
        name="html",
        get_target_uri=lambda docname: f"{docname}.html",
    )
    text = nodes.Text("f")
    link = mat_urls.chooser_link(dom, builder, "api", ["a/f.m", "b/f.m"], text)
    assert isinstance(link, nodes.reference)
    assert link["refuri"] == "mat/name/f.html"
    for refs in (["a/f.m", "a/private/f.m"], ["a/g.m", "a/private/g.m"]):
        assert mat_urls.chooser_link(dom, builder, "api", refs, text) is text
