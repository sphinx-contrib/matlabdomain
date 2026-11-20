"""Link targets of relative links in sidecar docs, in files they include and
in help text, on the page that renders them and across pages: each link
keeps its target, and the ids of the page stay as they are.
"""

import re
from pathlib import Path

import pytest
from test_sidecars import build, html, warnings, write

pytest.importorskip("myst_parser")

CONF = (
    'extensions = ["sphinxcontrib.matlab", "myst_parser"]\n'
    'matlab_src_code_project_root = "../src"\n'
    'matlab_src_sidecar_suffixes = [".md", ".rst"]\n'
    'matlab_src_exclude_patterns = ["**/minc.md"]\n'
)
NOTES = """\
Notes
=====

Usage
-----

`RLNK1 <bar.m>`_, `RLNK2 <guide.md>`_, `RLNK3 <guide.md#guide-part>`_,
`RLNK4 <../other/far.md>`_, `RLNK5 <https://example.com>`_,
`RLNK6 <#usage>`_, `RLNK7 <data.csv>`_, `RLNK8 <gone.rst>`_.

.. include:: inc.txt

.. include:: inc/deep.txt
"""
GUIDE = """\
# Guide

[MLNK1](bar.m), [MLNK2](notes.rst), [MLNK3](notes.rst#usage),
[MLNK4](../other/far.md), [MLNK5](https://example.com),
[MLNK6](#guide-part), [MLNK7](data.csv), [MLNK8](gone.md),
[MLNK9](README.md).

## Guide part

```{include} minc.md
```
"""
FILES = {
    "src/sub/bar.m": "function bar\n% BAR The target.\nend\n",
    "src/sub/withInc.m": "function withInc\n% WITHINC Help.\n%\n"
    "% `HLNK1 <bar.m>`_ and `HLNK2 <notes.rst>`_.\n%\n"
    "% .. include:: helpinc.txt\nend\n",
    "src/sub/helpinc.txt": "Help include: `HLNK3 <bar.m>`_, `HLNK4 <notes.rst>`_.\n",
    "src/sub/data.csv": "a,b\n",
    "src/sub/notes.rst": NOTES,
    "src/sub/inc.txt": "Included: `ILNK1 <bar.m>`_, `ILNK2 <guide.md>`_,\n"
    "`ILNK3 <../other/far.md>`_, `ILNK4 <https://example.com>`_.\n",
    "src/sub/inc/deep.txt": "Deep: `ILNK5 <bar.m>`_, `ILNK6 <../bar.m>`_.\n",
    "src/sub/inc/bar.m": "function bar\nend\n",
    "src/sub/guide.md": GUIDE,
    "src/sub/README.md": "# Sub\n\nThe introduction.\n",
    "src/sub/minc.md": "Markdown include: [MILNK1](bar.m), [MILNK2](notes.rst).\n",
    "src/other/far.md": "# Far\n\n[FLNK1](../sub/notes.rst), "
    "[FLNK2](../sub/guide.md#guide-part), [FLNK3](../sub/bar.m).\n\n"
    "## Far part\n\nText.\n",
    "docs/conf.py": CONF,
    "docs/index.rst": "Index\n=====\n\n.. toctree::\n\n   page\n   far\n",
    "docs/page.rst": "Page\n====\n\n"
    ".. mat:autosidecar:: sub/README.md\n   :no-title:\n\n"
    ".. mat:autofunction:: sub/withInc.m\n\n"
    ".. mat:autofunction:: sub/bar.m\n\n"
    ".. mat:autosidecar:: sub/notes.rst\n\n"
    ".. mat:autosidecar:: sub/guide.md\n",
    "docs/far.rst": ".. mat:autosidecar:: other/far.md\n",
}
API = "#mat-sub/bar.m"


def hrefs(body):
    """Link marker (``RLNK1``) -> href of the links on a page."""
    out = {}
    link = re.compile(r'<a [^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL)
    for href, text in link.findall(body):
        if marker := re.search(r"[A-Z]*LNK\d+", text):
            out[marker.group()] = href
    return out


def ids(body):
    return re.findall(r' id="([^"]*)"', body)


@pytest.fixture
def app(make_app, tmp_path):
    write(tmp_path, FILES)
    return build(make_app, tmp_path / "docs")


def test_link_targets(app):
    page = html(app, "page")
    assert hrefs(page) == {
        # help text, and a file it includes
        "HLNK1": API,
        "HLNK2": "#notes",
        "HLNK3": API,
        "HLNK4": "#notes",
        # a reST sidecar doc
        "RLNK1": API,
        "RLNK2": "#guide",
        "RLNK3": "#guide-part",
        "RLNK4": "far.html",
        "RLNK5": "https://example.com",
        "RLNK6": "#usage",
        "RLNK7": "_downloads/7d3627df50ff4323d8ce4018d6d3e8b1/data.csv",
        "RLNK8": "gone.rst",
        # files it includes: relative to the sidecar doc's folder
        "ILNK1": API,
        "ILNK2": "#guide",
        "ILNK3": "far.html",
        "ILNK4": "https://example.com",
        "ILNK5": API,
        "ILNK6": "../bar.m",
        # a Markdown sidecar doc, and a file it includes
        "MLNK1": API,
        "MLNK2": "#notes",
        "MLNK3": "#usage",
        "MLNK4": "far.html",
        "MLNK5": "https://example.com",
        "MLNK6": "#guide-part",
        "MLNK7": "_downloads/7d3627df50ff4323d8ce4018d6d3e8b1/data.csv",
        "MLNK8": "#gone.md",
        # a sidecar doc without its title (a README): the page
        "MLNK9": "#",
        "MILNK1": API,
        "MILNK2": "#notes",
    }
    assert hrefs(html(app, "far")) == {
        "FLNK1": "page.html",
        "FLNK2": "page.html#guide-part",
        "FLNK3": "page.html" + API,
    }


def test_ids_of_the_pages(app):
    assert ids(html(app, "page")) == [
        "page",
        "mat-sub/withInc.m",
        "mat-sub/bar.m",
        "notes",
        "usage",
        "guide",
        "guide-part",
    ]
    assert ids(html(app, "far")) == ["far", "far-part"]


def test_broken_links_are_reported(app):
    issues = app.env.get_domain("mat").data["sidecar_issues"]["page"]
    assert issues == [
        ("sub/notes.rst", "link", "gone.rst", 7),
        ("sub/notes.rst", "link", "../bar.m", 1),
        ("sub/guide.md", "link", "gone.md", 3),
    ]
    assert len(warnings(app)) == 1  # myst: gone.md
    assert Path(app.outdir, "_downloads").is_dir()
