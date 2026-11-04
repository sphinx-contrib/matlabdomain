"""Sidecar docs (plan.md Section 2.11, Phase 12): the index, the
``mat:autosidecar`` directive, links, the ``:mat:sidecar:`` role, the layouts,
incremental and parallel builds, ``sphinx-matlab-apidoc`` and
``matlab-api-check``.
"""

import json
import os
import shutil
import struct
import subprocess
import sys
import time
import zlib
from pathlib import Path

import pytest
import sphinx.builders
from sphinx.errors import ConfigError
from sphinx.util.console import strip_escape_sequences
from test_lazy_index import ForkLikeTasks

from sphinxcontrib import mat_sidecars, mat_types
from sphinxcontrib.mat_types import IndexSettings, build_index
from sphinxcontrib.matlab_apidoc import ApidocOptions, main
from sphinxcontrib.matlab_apidoc._generate import build_pages, stub_reference

pytest.importorskip("myst_parser")

CONF = (
    'extensions = ["sphinxcontrib.matlab", "myst_parser"]\n'
    'matlab_src_code_project_root = "../src"\n'
    'matlab_src_sidecar_suffixes = [".md", ".rst"]\n'
    'exclude_patterns = ["_build"]\n'
    "nitpicky = True\n"
)
GUIDE = """# Getting started

A role: {mat:func}`demo.scale`.

![a plot](img/plot.png)

## Links

- A page: [notes](notes.rst)
- A page without text: [](sub/deep.md)
- An anchor: [links](#links)
- Code: [scale](scale.m) and [](scale.m)
- A download: [data](img/plot.png)
- A page with an anchor: [section](notes.rst#section-two)
- External: <https://example.com>
- Broken: [gone](missing.md)

## Code

```{literalinclude} scale.m
:language: matlab
```

## Foo_bar

A heading whose slug differs from its id.
"""
FIGURE = """.. figure:: img/missing.png

   A missing figure.

"""
NOTES = f"""Notes
=====

A role: :mat:func:`demo.scale`.

.. image:: img/plot.png

{FIGURE}Sidecar docs: :mat:sidecar:`+demo/guide.md` and
:mat:sidecar:`the guide <+demo/guide.md>`;
the introduction: :mat:sidecar:`+demo/README.md`;
a download: :download:`scale.m`.

.. literalinclude:: scale.m
   :language: matlab

.. include:: part.inc

Section two
-----------

Text.
"""
FILES = {
    "src/+demo/scale.m": "function y = scale(x, k)\n%SCALE Multiply X by K.\n"
    "y = x * k;\nend\n",
    "src/+demo/scale.md": "# Scale notes\n\nA page next to scale.m.\n",
    "src/+demo/guide.md": GUIDE,
    "src/+demo/notes.rst": NOTES,
    "src/+demo/part.inc": "Included from part.inc.\n",
    "src/+demo/sub/deep.md": "# Deep page\n\n![up](../img/plot.png)\n\n"
    "![any format](../img/plot.*)\n\nBack to [the guide](../guide.md), "
    "[a section](../guide.md#foo_bar).\n",
    "src/+demo/README.md": "# Demo\n\nThe demo namespace.\n\n## Usage\n\nCall it.\n",
    "src/+demo/plain.md": "Text without a heading.\n",
    "src/README.md": "# The project\n",
}
STUBS = {
    "guide-md": "+demo/guide.md",
    "notes-rst": "+demo/notes.rst",
    "scale-md": "+demo/scale.md",
    "plain-md": "+demo/plain.md",
    "sub/deep-md": "+demo/sub/deep.md",
}
API = """namespace demo
==============

.. mat:autofolder:: +demo/

.. mat:autosidecar:: +demo/README.md
   :no-title:

.. mat:autofunction:: +demo/scale.m

Sidecar docs
------------

.. toctree::

{}
""".format("\n".join(f"   {stub}" for stub in STUBS))


def png():
    raw = b"".join(b"\0" + bytes((200, 30, 30)) * 4 for _ in range(4))

    def chunk(tag, data):
        crc = struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + tag + data + crc

    header = struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def write(root, files):
    for path, content in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8")


def fresh(root):
    """Write a MATLAB root ``src/`` with sidecar docs and a Sphinx project ``docs/``
    with hand-written stubs (the source folder outside the root).
    """
    files = {
        **FILES,
        "src/+demo/img/plot.png": png(),
        "docs/conf.py": CONF,
        "docs/index.rst": "Index\n=====\n\n.. toctree::\n\n   api/+demo/index\n",
        "docs/api/+demo/index.rst": API,
    }
    for stub, ref in STUBS.items():
        files[f"docs/api/+demo/{stub}.rst"] = f".. mat:autosidecar:: {ref}\n"
    write(root, files)
    return root


@pytest.fixture
def project(tmp_path):
    return fresh(tmp_path / "p")


def html(app, docname):
    """Return the body of a page, without the navigation."""
    text = (Path(app.outdir) / f"{docname}.html").read_text(encoding="utf-8")
    return text.split('role="main"', 1)[1].split('class="sphinxsidebar"', 1)[0]


def warnings(app):
    text = strip_escape_sequences(app.warning.getvalue())
    return [line for line in text.splitlines() if "WARNING" in line]


def read_docs(app):
    return sorted(app.env.get_domain("mat").read_docnames)


def build(make_app, srcdir, builder="html", **overrides):
    app = make_app(builder, srcdir=srcdir, confoverrides=overrides)
    app.build()
    return app


# --- settings and the index -------------------------------------------------


def test_sidecar_suffix_list():
    assert mat_types.sidecar_suffix_list([".rst", ".md", ".rst"]) == (".md", ".rst")
    assert mat_types.sidecar_suffix_list(()) == ()
    with pytest.raises(ConfigError, match="must be a list"):
        mat_types.sidecar_suffix_list(".md")
    with pytest.raises(ConfigError, match="'md' is not a sidecar suffix"):
        mat_types.sidecar_suffix_list(["md"])


def test_source_filter_default_exclusions():
    class Config:
        matlab_src_code_project_root = None
        matlab_src_include_patterns = ["**/*"]
        matlab_src_exclusion_patterns = list(mat_types.DEFAULT_EXCLUSION_PATTERNS)

    sources = mat_types.source_filter(Config)
    assert not sources.includes("README.md")
    assert not sources.includes("LICENSE.txt")
    assert sources.includes("readme.md")
    assert sources.includes("+pkg/README.md")
    Config.matlab_src_exclusion_patterns = []
    assert mat_types.source_filter(Config).includes("README.md")
    Config.matlab_src_exclusion_patterns = ["**/tests"]
    with pytest.raises(ConfigError, match="need matlab_src_code_project_root"):
        mat_types.source_filter(Config)


def test_index_records_sidecars_apart_from_code(project):
    src = project / "src"
    settings = IndexSettings(str(src), sidecar_suffixes=(".md", ".rst"))
    source_index = build_index(settings)
    sidecars = {r["reference"]: path for path, r in source_index.sidecars.items()}
    assert sorted(sidecars) == [
        "+demo/README.md",
        "+demo/guide.md",
        "+demo/notes.rst",
        "+demo/plain.md",
        "+demo/scale.md",
        "+demo/sub/deep.md",
    ]
    record = source_index.sidecars[sidecars["+demo/guide.md"]]
    st = os.stat(sidecars["+demo/guide.md"])
    assert record == {
        "reference": "+demo/guide.md",
        "mtime": st.st_mtime_ns,
        "size": st.st_size,
    }
    # No sidecar doc is code, a member of its folder or a MATLAB name.
    refs = {r["reference"] for r in source_index.index.values()}
    assert refs == {"+demo/scale.m"}
    assert source_index.entities["+demo/"].members == [
        (name, ref)
        for name, ref in source_index.entities["+demo/"].members
        if not ref.endswith((".md", ".rst"))
    ]
    assert "demo.scale" in source_index.matlab_names
    assert not any(n.endswith("guide") for n in source_index.matlab_names)
    # Off by default.
    assert build_index(IndexSettings(str(src))).sidecars == {}


def test_sidecar_patterns_and_source_folder_inside_root(tmp_path):
    root = tmp_path / "repo"
    write(
        root,
        {
            "README.md": "# Root readme\n",
            "Readme.rst": "Other case\n==========\n",
            "a/guide.md": "# Guide\n",
            "a/f.m": "function f\nend\n",
            "tests/t.md": "# Test notes\n",
            "docs/index.rst": "Index\n=====\n",
            "docs/sub/page.md": "# Docs page\n",
            "docs/helper.m": "function helper\nend\n",
        },
    )
    settings = IndexSettings(
        str(root),
        exclude=(*mat_types.DEFAULT_EXCLUSION_PATTERNS, "tests"),
        sidecar_suffixes=(".md", ".rst"),
        source_dir=str(root / "docs"),
    )
    source_index = build_index(settings)
    sidecars = sorted(r["reference"] for r in source_index.sidecars.values())
    assert sidecars == ["Readme.rst", "a/guide.md"]
    # Code in the source folder is still indexed.
    refs = sorted(r["reference"] for r in source_index.index.values())
    assert refs == ["a/f.m", "docs/helper.m"]
    assert mat_types.sidecar_paths(settings) == list(source_index.sidecars)
    assert mat_types.sidecar_paths(IndexSettings(str(root / "missing"))) == []


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="no symlinks")
def test_sidecar_linked_outside_the_root_is_skipped(tmp_path, caplog):
    root = tmp_path / "root"
    write(tmp_path, {"outside.md": "# Outside\n", "root/in.md": "# In\n"})
    try:
        os.symlink(tmp_path / "outside.md", root / "link.md")
    except OSError:
        pytest.skip("cannot create symlinks")
    settings = IndexSettings(str(root), sidecar_suffixes=(".md",))
    sidecars = [r["reference"] for r in build_index(settings).sidecars.values()]
    assert sidecars == ["in.md"]
    # The quiet walk finds the same sidecar docs.
    assert [os.path.basename(p) for p in mat_types.sidecar_paths(settings)] == ["in.md"]


def test_sidecar_layout_error():
    mat_types.sidecar_layout_error("/a/src", "/a/docs")
    with pytest.raises(ConfigError, match="to differ from the Sphinx source folder"):
        mat_types.sidecar_layout_error("/a/docs/", "/a/docs")


# --- configuration ---------------------------------------------------------


@pytest.mark.parametrize(
    ("conf", "match"),
    [
        ('matlab_src_sidecar_suffixes = ".md"\n', "must be a list"),
        (
            'matlab_src_sidecar_suffixes = [".txt"]\n',
            "'.txt' is not a sidecar suffix",
        ),
        (
            "matlab_src_code_project_root = None\n"
            'matlab_src_sidecar_suffixes = [".rst"]\n',
            "needs matlab_src_code_project_root",
        ),
        (
            'extensions = ["sphinxcontrib.matlab"]\n',
            "add 'myst_parser' to extensions",
        ),
        ('matlab_src_code_project_root = "."\n', "to differ from the Sphinx source"),
    ],
)
def test_config_errors(make_app, project, conf, match):
    docs = project / "docs"
    (docs / "conf.py").write_text(CONF + conf, encoding="utf-8")
    with pytest.raises(ConfigError, match=match):
        make_app(srcdir=docs)


def test_root_on_another_drive_warns(make_app, project, monkeypatch):
    assert mat_sidecars.same_drive(str(project), str(project / "docs"))
    monkeypatch.setattr(mat_sidecars, "same_drive", lambda *_: False)
    app = make_app(srcdir=project / "docs")
    assert "on another drive than the Sphinx source folder" in app.warning.getvalue()
    assert "[mat.sidecar]" in app.warning.getvalue()


# --- rendering ---------------------------------------------------------------


def test_sidecars_render(make_app, project):
    app = build(make_app, project / "docs")
    found = warnings(app)
    assert len(found) == 3, found
    plain = str(project / "src" / "+demo" / "plain.md")
    assert (
        f"{plain}:1: WARNING: [sphinxcontrib-matlabdomain] +demo/plain.md has no "
        "heading; its file name is its title. [mat.sidecar]" in found
    )
    assert any("missing.md" in w and "[myst.xref_missing]" in w for w in found)
    assert any("missing.png" in w and "image file not readable" in w for w in found)

    titles = app.env.titles
    prefix = "api/+demo/"
    assert titles[f"{prefix}guide-md"].astext() == "Getting started"
    assert titles[f"{prefix}notes-rst"].astext() == "Notes"
    assert titles[f"{prefix}plain-md"].astext() == "plain.md"
    assert titles[f"{prefix}sub/deep-md"].astext() == "Deep page"

    guide = html(app, f"{prefix}guide-md")
    assert 'src="../../_images/plot.png"' in guide
    assert 'href="notes-rst.html"' in guide
    assert '<a class="reference internal" href="sub/deep-md.html">' in guide
    assert ">Deep page</span>" in guide
    assert 'href="#links"' in guide
    assert guide.count('href="index.html#mat-+demo/scale.m"') == 3
    assert ">demo.scale</span>" in guide
    assert 'href="notes-rst.html#section-two"' in guide
    assert "_downloads/" in guide
    assert "highlight-matlab" in guide

    notes = html(app, f"{prefix}notes-rst")
    assert 'src="../../_images/plot.png"' in notes
    assert notes.count('href="guide-md.html"') == 2
    assert ">Getting started</span>" in notes
    # A README's link text is the sidecar doc's title, not its document's.
    assert '<a class="reference internal" href="index.html">' in notes
    assert ">Demo</span>" in notes
    assert "Included from part.inc." in notes
    assert "highlight-matlab" in notes
    assert "_downloads/" in notes

    deep = html(app, f"{prefix}sub/deep-md")
    assert 'src="../../../_images/plot.png"' in deep
    assert 'href="../guide-md.html"' in deep
    # Without myst_heading_anchors the anchor is taken as it is.
    assert 'href="../guide-md.html#foo_bar"' in deep

    folder = html(app, f"{prefix}index")
    assert "The demo namespace." in folder
    assert ">Usage<" in folder
    assert ">Demo<" not in folder
    assert (Path(app.outdir) / "_images" / "plot.png").is_file()

    # scale.md next to scale.m: the name still finds the function.
    dom = app.env.get_domain("mat")
    assert type(dom.entities_table["+demo/"].getter("scale")).__name__ == "MatFunction"
    assert dom.sidecar_doc("+demo/README.md") == f"{prefix}index"
    issues = dom.data["sidecar_issues"]
    assert issues[f"{prefix}guide-md"] == [("+demo/guide.md", "link", "missing.md", 16)]
    assert [i[:3] for i in issues[f"{prefix}notes-rst"]] == [
        ("+demo/notes.rst", "image", "img/missing.png")
    ]


def test_autosidecar_problems(make_app, project, monkeypatch):
    docs = project / "docs"
    write(
        project,
        {
            "src/+demo/latin.md": b"# Caf\xe9\n\nBad byte.\n",
            "src/+demo/bom.rst": b"\xef\xbb\xbfBOM\n===\n\nText.\n",
            "src/+demo/abs.md": "# Absolute\n\n[x](/nowhere.md) and [y]()\n\n"
            "### Skipped a level\n",
            "src/+demo/intro.md": "An introduction without a heading.\n",
            "src/+demo/nest.rst": "Nest\n====\n\n"
            ".. mat:autosidecar:: +demo/scale.md\n\n"
            ".. literalinclude:: part.inc\n   :language: text\n",
            "docs/extra.rst": ":orphan:\n\n.. mat:autosidecar:: +demo/latin.md\n\n"
            ".. mat:autosidecar:: +demo/bom.rst\n\n"
            ".. mat:autosidecar:: +demo/later.md\n\n"
            ".. mat:autosidecar:: +demo/abs.md\n\n"
            ".. mat:autosidecar:: +demo/intro.md\n   :no-title:\n\n"
            ".. mat:autosidecar:: +demo/nest.rst\n\n"
            "See :mat:sidecar:`+demo/nowhere.md`.\n",
        },
    )
    app = build(make_app, docs)
    text = app.warning.getvalue()
    assert "+demo/latin.md is not valid UTF-8" in text
    assert f"{project / 'src' / '+demo' / 'latin.md'}:1:" in text
    assert "+demo/later.md is not a sidecar doc" in text
    assert "mat:sidecar reference target not found: +demo/nowhere.md" in text
    assert "intro.md has no heading" not in text
    # myst-parser's warnings point into the sidecar doc.
    abs_md = project / "src" / "+demo" / "abs.md"
    assert f"{abs_md}:5: WARNING: Non-consecutive header level increase" in text
    body = html(app, "extra")
    assert "Caf\ufffd" in body
    assert ">BOM<" in body
    assert "<p>An introduction without a heading.</p>" in body
    # A sidecar doc that renders another: both resolve relative paths.
    assert ">Scale notes<" in body
    assert "Included from part.inc." in body
    assert "relfn2path" not in vars(app.env)
    assert app.env.get_domain("mat").data["sidecar_issues"]["extra"] == []

    # The missing sidecar doc appears: the document is read again.
    write(project, {"src/+demo/later.md": "# Later\n"})
    app = build(make_app, docs)
    assert "extra" in read_docs(app)
    assert "not a sidecar doc" not in app.warning.getvalue()

    def unreadable(path, ref):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(mat_sidecars, "read_sidecar", unreadable)
    app = make_app(srcdir=docs, freshenv=True)
    app.build()
    assert "+demo/guide.md cannot be read (Permission denied)" in app.warning.getvalue()


def test_paths_on_another_drive_are_left_alone(make_app, project, monkeypatch):
    monkeypatch.setattr(mat_sidecars._Sidecar, "source_path", lambda *_: None)
    app = build(make_app, project / "docs")
    guide = html(app, "api/+demo/guide-md")
    # The image keeps its relative path; the download is myst-parser's.
    assert "plot.png" in guide
    dom = app.env.get_domain("mat")
    assert dom.sidecar_doc("+demo/guide.md") == "api/+demo/guide-md"


@pytest.mark.skipif(os.name != "nt", reason="drives are a Windows thing")
def test_source_path_on_another_drive():
    sidecar = mat_sidecars._Sidecar("a.md", "Z:\\src\\a.md", "C:\\docs", None)
    assert sidecar.source_path("Z:\\src\\img.png") is None
    assert sidecar.source_path("C:\\docs\\img.png") == "/img.png"


def test_autosidecar_without_a_root(make_app, tmp_path):
    write(
        tmp_path,
        {
            "conf.py": 'extensions = ["sphinxcontrib.matlab"]\n',
            "index.rst": "Index\n=====\n\n.. mat:autosidecar:: guide.md\n",
        },
    )
    app = build(make_app, tmp_path)
    assert "guide.md is not a sidecar doc" in app.warning.getvalue()
    assert app.env.dependencies["index"] == set()


def test_autosidecar_in_a_markdown_document(make_app, project):
    # The directive also works in a MyST document.
    write(
        project,
        {
            "docs/md.md": "---\norphan: true\n---\n\n# Host\n\n"
            "```{mat:autosidecar} +demo/sub/deep.md\n```\n"
        },
    )
    app = build(make_app, project / "docs")
    assert 'href="api/%2Bdemo/guide-md.html"' in html(app, "md")
    assert "wordcount" not in app.warning.getvalue()


def test_heading_slugs_name_sections(make_app, project):
    app = build(make_app, project / "docs", myst_heading_anchors=2)
    # GitHub's slug foo_bar; the section's id is foo-bar.
    assert 'href="../guide-md.html#foo-bar"' in html(app, "api/+demo/sub/deep-md")


def test_missing_link_target_is_a_dependency(make_app, project):
    docs = project / "docs"
    app = build(make_app, docs)
    assert "api/+demo/guide-md" in read_docs(build(make_app, docs))
    write(project, {"src/+demo/missing.md": "# Found\n"})
    app = build(make_app, docs)
    assert app.env.get_domain("mat").data["sidecar_issues"]["api/+demo/guide-md"] == []


# --- incremental and parallel builds ----------------------------------------


def _touch(path):
    # After the last build's reads, before the next: read once more.
    now = time.time_ns()
    os.utime(path, ns=(now, now))


def test_incremental_builds(make_app, project):
    docs, demo = project / "docs", project / "src" / "+demo"
    # A missing image or link target is a dependency that makes Sphinx read
    # its page always.
    (demo / "notes.rst").write_text(NOTES.replace(FIGURE, ""), encoding="utf-8")
    (demo / "guide.md").write_text(
        GUIDE.replace("- Broken: [gone](missing.md)\n", ""), encoding="utf-8"
    )
    old = time.time_ns() - 100 * 10**9
    for path in demo.rglob("*"):
        os.utime(path, ns=(old, old))
    build(make_app, docs)
    assert read_docs(build(make_app, docs)) == []
    _touch(demo / "guide.md")
    assert read_docs(build(make_app, docs)) == ["api/+demo/guide-md"]
    _touch(demo / "img" / "plot.png")
    assert read_docs(build(make_app, docs)) == [
        "api/+demo/guide-md",
        "api/+demo/notes-rst",
        "api/+demo/sub/deep-md",
    ]
    _touch(demo / "part.inc")
    assert read_docs(build(make_app, docs)) == ["api/+demo/notes-rst"]
    # scale.m: the folder page documents it, two pages include it.
    _touch(demo / "scale.m")
    assert read_docs(build(make_app, docs)) == [
        "api/+demo/guide-md",
        "api/+demo/index",
        "api/+demo/notes-rst",
    ]
    assert read_docs(build(make_app, docs)) == []


def _outputs(app):
    out = Path(app.outdir)
    pages = {
        p.relative_to(out).as_posix(): p.read_bytes()
        for p in sorted(out.rglob("*.html"))
    }
    data = app.env.domaindata["mat"]
    return pages, data["sidecar_docs"], data["sidecar_issues"]


def test_simulated_parallel_read_matches_serial(make_app, project, monkeypatch):
    docs = project / "docs"
    serial = make_app(srcdir=docs, builddir=project / "serial")
    serial.build()
    monkeypatch.setattr(sphinx.builders, "parallel_available", True)
    monkeypatch.setattr(sphinx.builders, "ParallelTasks", ForkLikeTasks)
    app = make_app(srcdir=docs, builddir=project / "parallel", parallel=4)
    ForkLikeTasks.app = app
    app.build()
    assert _outputs(app) == _outputs(serial)


def test_parallel_build_matches_serial(project, tmp_path):
    # Real -j where Sphinx can fork (POSIX); a serial build elsewhere.
    out = {}
    for name, extra in (("serial", []), ("parallel", ["-j", "2"])):
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "sphinx",
                "-b",
                "html",
                "-q",
                "-n",
                *extra,
                str(project / "docs"),
                str(tmp_path / name),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert proc.returncode == 0, proc.stderr
        out[name] = (
            sorted(proc.stderr.splitlines()),
            {
                p.relative_to(tmp_path / name).as_posix(): p.read_bytes()
                for p in sorted((tmp_path / name).rglob("*.html"))
            },
        )
    assert out["parallel"] == out["serial"]


# --- layouts -----------------------------------------------------------------


def test_root_inside_the_source_folder(make_app, tmp_path):
    docs = tmp_path / "docs"
    stubs = {"guide-md": "+demo/guide.md", "odd-md": "+demo/odd[1].md"}
    write(
        docs,
        {
            "conf.py": CONF.replace('"../src"', '"src"'),
            "index.rst": "Index\n=====\n\n.. toctree::\n\n   guide-md\n   odd-md\n",
            **{f"{s}.rst": f".. mat:autosidecar:: {r}\n" for s, r in stubs.items()},
            "src/+demo/scale.m": FILES["src/+demo/scale.m"],
            "src/+demo/guide.md": "# Guide\n\nSee [odd](odd[1].md).\n",
            "src/+demo/odd[1].md": "# Odd\n",
            "src/+demo/notes.rst": "Notes\n=====\n",
        },
    )
    app = build(make_app, docs)
    assert sorted(app.env.found_docs) == ["guide-md", "index", "odd-md"]
    assert sorted(app.config.exclude_patterns) == [
        "_build",
        "src/+demo/guide.md",
        "src/+demo/notes.rst",
        "src/+demo/odd[][]1].md",
    ]
    # notes.rst is in no toctree, but Sphinx does not read it.
    assert warnings(app) == []
    # The same list next time: the config is unchanged, nothing is read.
    again = build(make_app, docs)
    assert read_docs(again) == []


def test_source_folder_inside_the_root(make_app, tmp_path):
    repo = tmp_path / "repo"
    write(
        repo,
        {
            "docs/conf.py": CONF.replace('"../src"', '".."'),
            "docs/index.rst": "Index\n=====\n\n.. toctree::\n\n   about\n   guide-md\n",
            "docs/about.md": "# About\n\nA Sphinx document, not a sidecar doc.\n",
            "docs/guide-md.rst": ".. mat:autosidecar:: a/guide.md\n\n"
            ".. mat:autofunction:: a/f.m\n",
            "a/guide.md": "# Guide\n\nCalls [f](f.m).\n",
            "a/f.m": "function f\n%F Do nothing.\nend\n",
        },
    )
    app = build(make_app, repo / "docs")
    dom = app.env.get_domain("mat")
    assert sorted(dom.sidecar_paths()) == ["a/guide.md"]
    assert "docs/about.md" not in dom.sidecar_paths()
    assert "about" in app.env.found_docs
    assert warnings(app) == []


# --- sphinx-matlab-apidoc ----------------------------------------------------


def apidoc_pages(root, **options):
    options.setdefault("group", "folder")
    settings = IndexSettings(str(root), sidecar_suffixes=(".md", ".rst"))
    return {
        p.docname: p
        for p in build_pages(build_index(settings), ApidocOptions("o", **options))
    }


def test_stub_reference():
    assert stub_reference("a/guide.md") == "a/guide-md"
    assert stub_reference("guide.md.rst") == "guide.md-rst"


def test_apidoc_sidecar_model(tmp_path):
    root = tmp_path / "root"
    write(
        root,
        {
            "+demo/f.m": "function f\nend\n",
            "+demo/README.md": "# Demo\n",
            "+demo/readme.rst": "Second readme\n=============\n",
            "+demo/Zeta.md": "# Zeta\n",
            "+demo/alpha.rst": "Alpha\n=====\n",
            "+demo/f.md": "# Notes on f\n",
            "+demo/@Cls/Cls.m": "classdef Cls\nend\n",
            "+demo/@Cls/Readme.md": "# Class notes\n",
            "notes/only.md": "# Only pages here\n",
            "my folder/README.rst": "Intro\n=====\n",
        },
    )
    pages = apidoc_pages(root)
    assert sorted(pages) == [
        "+demo/@Cls/Readme-md",
        "+demo/Zeta-md",
        "+demo/alpha-rst",
        "+demo/f-md",
        "+demo/index",
        "+demo/readme-rst",
        "index",
        "my~20folder/index",
        "notes/index",
        "notes/only-md",
    ]
    demo = pages["+demo/index"].context
    assert demo["readme"] == "+demo/README.md"
    # By casefold(name), ref; an @ folder's README is an ordinary sidecar doc.
    assert [(p["ref"], p["docname"]) for p in demo["sidecars"]] == [
        ("+demo/alpha.rst", "alpha-rst"),
        ("+demo/f.md", "f-md"),
        ("+demo/@Cls/Readme.md", "@Cls/Readme-md"),
        ("+demo/readme.rst", "readme-rst"),
        ("+demo/Zeta.md", "Zeta-md"),
    ]
    assert pages["+demo/f-md"].context == {
        "ref": "+demo/f.md",
        "name": "f.md",
        "docname": "+demo/f-md",
    }
    assert pages["my~20folder/index"].context["readme"] == "my folder/README.rst"
    assert pages["my~20folder/index"].context["sidecars"] == []
    assert pages["index"].context["pages"] == [
        "+demo/index",
        "my~20folder/index",
        "notes/index",
    ]
    assert pages["notes/index"].context["sections"] == []


def test_apidoc_from_conf_builds(make_app, project, capsys):
    docs = project / "docs"
    shutil.rmtree(docs / "api")
    (docs / "conf.py").write_text(
        CONF + 'matlab_apidoc_output_dir = "api"\nmatlab_apidoc_group = "folder"\n',
        encoding="utf-8",
    )
    (docs / "index.rst").write_text(
        "Index\n=====\n\n.. toctree::\n\n   api/index\n", encoding="utf-8"
    )
    assert main(["-q", "-c", str(docs)]) == 0
    api = docs / "api" / "+demo"
    assert (
        (api / "guide-md.rst")
        .read_text(encoding="utf-8")
        .endswith(".. mat:autosidecar:: +demo/guide.md\n")
    )
    folder = (api / "index.rst").read_text(encoding="utf-8")
    assert ".. mat:autosidecar:: +demo/README.md\n   :no-title:\n" in folder
    assert folder.index("Functions\n---") < folder.index("Sidecar docs\n---")
    assert "Folders\n---" not in folder
    assert main(["-q", "--check", "-c", str(docs)]) == 0

    app = build(make_app, docs)
    found = warnings(app)
    assert len(found) == 3, found  # plain.md, missing.md, missing.png
    assert app.env.titles["api/+demo/guide-md"].astext() == "Getting started"


def test_apidoc_namespace_pages_render_sidecars(make_app, project):
    docs = project / "docs"
    shutil.rmtree(docs / "api")
    (docs / "conf.py").write_text(
        CONF + 'matlab_apidoc_output_dir = "api"\n', encoding="utf-8"
    )
    (docs / "index.rst").write_text(
        "Index\n=====\n\n.. toctree::\n\n   api/index\n", encoding="utf-8"
    )
    assert main(["-q", "-c", str(docs)]) == 0
    page = (docs / "api" / "demo.rst").read_text(encoding="utf-8")
    assert ".. mat:autosidecar:: +demo/guide.md\n" in page
    assert ".. mat:autosidecar:: +demo/README.md\n" in page
    assert page.index("Functions\n---") < page.index("Sidecar docs\n---")
    app = build(make_app, docs)
    found = warnings(app)
    assert len(found) == 3, found  # plain.md, missing.md, missing.png


def test_apidoc_layout_error(project, capsys):
    docs = project / "docs"
    (docs / "conf.py").write_text(
        CONF.replace('"../src"', '"."') + 'matlab_apidoc_output_dir = "api"\n',
        encoding="utf-8",
    )
    assert main(["-q", "-c", str(docs)]) == 2
    assert "to differ from the Sphinx source folder" in capsys.readouterr().err


# --- matlab-api-check ---------------------------------------------------------


def test_api_check_sidecars(make_app, project):
    docs = project / "docs"
    write(
        project,
        {
            "src/+demo/lost.md": "# Not rendered\n",
            "src/+demo/hidden.md": "# Rendered off the toctree\n",
            "src/+demo/kept.md": "# Rendered in an orphan\n",
            "docs/hidden.rst": ".. mat:autosidecar:: +demo/hidden.md\n",
            "docs/kept.rst": ":orphan:\n\n.. mat:autosidecar:: +demo/kept.md\n",
        },
    )
    app = build(
        make_app,
        docs,
        "matlab-api-check",
        matlab_api_check_ignore_patterns=["+demo/plain.md"],
    )
    assert app.statuscode == 1
    report = json.loads((Path(app.outdir) / "api-check.json").read_text("utf-8"))
    sidecars = [f for f in report["findings"] if f["kind"] == "sidecar"]
    assert [(f["reference"], f["rule"], f["line"], f["message"]) for f in sidecars] == [
        (
            "+demo/guide.md",
            "sidecar-links",
            16,
            "links to a missing file: missing.md",
        ),
        (
            "+demo/hidden.md",
            "sidecar-documented",
            None,
            "is rendered in hidden, which no toctree includes",
        ),
        (
            "+demo/lost.md",
            "sidecar-documented",
            None,
            "is not rendered by a mat:autosidecar directive",
        ),
        (
            "+demo/notes.rst",
            "sidecar-links",
            sidecars[3]["line"],
            "shows a missing image: img/missing.png",
        ),
    ]
    summary = report["summary"]
    assert summary["checked"]["sidecar"] == 8
    assert summary["not_checked"]["ignored"] == 1
    assert summary["findings"]["sidecar-links"] == {"error": 2, "warning": 0}
    text = (Path(app.outdir) / "api-check.txt").read_text(encoding="utf-8")
    guide = project / "src" / "+demo" / "guide.md"
    assert (
        f"{guide}:16: error: +demo/guide.md: links to a missing file: missing.md "
        "[sidecar-links]"
    ) in text
