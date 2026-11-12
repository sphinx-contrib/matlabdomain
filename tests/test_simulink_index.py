"""Simulink files in the index: handlers, references with blocks, MATLAB
names, lookups and incremental builds (S4 of the Simulink plan).
"""

import builtins
import io
import json
import logging
import os
import pickle
import shutil
import zipfile
from pathlib import Path

import pytest

from sphinxcontrib import mat_handlers, mat_naming, mat_simulink, mat_types
from sphinxcontrib.mat_naming import (
    folder_of,
    form_model_name,
    is_block_container,
    model_not_callable_reason,
    parse_reference,
)
from sphinxcontrib.mat_types import (
    IndexSettings,
    MatBlock,
    MatLibrary,
    MatModel,
    MatSubsystemFile,
    build_index,
)
from sphinxcontrib.matlab_apidoc import ApidocOptions, generate
from sphinxcontrib.matlab_apidoc._generate import build_pages
from sphinxcontrib.matlab_apidoc._names import docnames

FIXTURES = Path(__file__).parent / "simulink" / "fixtures"
SLX = FIXTURES / "R2026b" / "slx"
CONF = (
    'extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]\n'
    'matlab_src_code_project_root = "src"\n'
    'primary_domain = "mat"\n'
)
LFS = b"version https://git-lfs.github.com/spec/v1\noid sha256:00\nsize 1\n"
# The head of a Simulink library saved with ``ExportToXML``: a file type
# that is not read.
EXPORT_XML = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<ModelInformation Version="1.0">\n'
    '  <Library Name="probeLib">\n'
    '    <P Name="Description">Library description</P>\n'
    '    <System><Block BlockType="SubSystem" Name="Group"/></System>\n'
    "  </Library>\n"
    "</ModelInformation>\n"
)


@pytest.fixture
def warnings():
    """``(subtype, message)`` of the ``mat`` warnings logged meanwhile."""
    records = []

    class Collect(logging.Handler):
        def emit(self, record):
            if getattr(record, "type", None) == "mat":
                records.append((getattr(record, "subtype", None), record.getMessage()))

    logger = logging.getLogger("sphinx")
    saved = logger.handlers[:]
    logger.handlers = [Collect(logging.WARNING)]
    yield records
    logger.handlers = saved


def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def project(root):
    """Write a source tree with Simulink files of every kind and location."""
    copy(SLX / "probeModel.slx", root / "probeModel.slx")
    copy(SLX / "probeLib.slx", root / "probeLib.slx")
    copy(SLX / "probeSub.slx", root / "+pk" / "probeSub.slx")
    copy(SLX / "probeRef.slx", root / "private" / "probeRef.slx")
    copy(SLX / "probeRef.slx", root / "@Cls" / "inClass.slx")
    copy(SLX / "probeRef.slx", root / "@Cls" / "sub" / "inSub.slx")
    copy(FIXTURES / "R2026a" / "mdl" / "probeLib.mdl", root / "mdl" / "probeLib.mdl")
    (root / "export.xml").write_text(EXPORT_XML, encoding="utf-8")
    (root / "@Cls" / "Cls.m").write_text("classdef Cls\nend\n")
    (root / "other.xml").write_text("<root/>\n")
    (root / "lfs.slx").write_bytes(LFS)
    (root / "notes.slx").write_text("not a model\n")
    copy(SLX / "probeRef.slx", root / "same.slx")
    (root / "same.m").write_text("function same\nend\n")
    (root / "data.slx").mkdir()
    (root / "data.slx" / "hidden.m").write_text("function hidden\nend\n")
    return root


def test_block_references():
    assert parse_reference("src/probeLib.slx/Group/Inner Masked") == (
        "src/probeLib.slx",
        ["Group/Inner Masked"],
    )
    assert parse_reference("probeLib.slx/A//B") == ("probeLib.slx", ["A//B"])
    assert parse_reference("a/lib.mdl/Two\nLines") == ("a/lib.mdl", ["Two\nLines"])
    # .xml is no file type: lib.xml is a folder, v1.2 no file
    assert parse_reference("a/lib.xml/f.m") == ("a/lib.xml/f.m", [])
    assert parse_reference("a/lib.xml/v1.2") == (None, [])
    assert not is_block_container("lib.xml")
    assert parse_reference("a/lib.slx") == ("a/lib.slx", [])
    assert parse_reference("a/lib.slx/") == ("a/lib.slx/", [])
    # ".slx" alone is no file name
    assert parse_reference("a/.slx/f.m") == ("a/.slx/f.m", [])
    assert parse_reference("a/Cls.m.meth") == ("a/Cls.m", ["meth"])
    assert parse_reference("a/b.x/c.m", block_extensions=(".x",)) == ("a/b.x", ["c.m"])
    assert folder_of("a/lib.slx/G/B") == "a/"
    assert is_block_container("lib.slx")
    assert not is_block_container(".slx")
    assert not is_block_container("f.m")
    assert mat_naming.make_target_id("lib.slx/A//B") == "mat-lib.slx/A//B"


@pytest.mark.parametrize(
    ("folder", "filename", "version", "name"),
    [
        ("root", "probe.slx", "R2026a", "probe"),
        ("root/+pk", "probe.slx", "R2026b", None),
        ("root/+pk", "probe.slx", "R2024a", None),
        ("root/+pk/sub", "probe.slx", "R2024a", "probe"),
        ("root/private", "probe.slx", "R2026a", None),
        ("root/@Cls", "probe.slx", "R2026a", None),
        # Simulink checks the file's own folder only (R2024a-R2026b).
        ("root/private/deep", "probe.slx", "R2026b", "probe"),
        ("root/@Cls/sub", "probe.slx", "R2024a", "probe"),
        ("root/@Cls/sub", "probe.slx", "R2026b", "probe"),
        ("root/+pk/@Cls/sub", "probe.slx", "R2026b", "probe"),
        ("root/@Cls/private", "probe.slx", "R2024a", None),
        ("root/a*b", "probe.slx", "R2026a", None),
        ("root/+for", "probe.slx", "R2026a", None),
        ("root", "end.slx", "R2026a", None),
        ("root", "bad-name.mdl", "R2026a", None),
        ("root", "L" + "x" * 63 + ".slx", "R2024b", None),
        ("root", "L" + "x" * 63 + ".slx", "R2026a", "L" + "x" * 63),
    ],
)
def test_form_model_name(folder, filename, version, name):
    namelengthmax = mat_naming.default_namelengthmax(version)
    formed = form_model_name(folder, filename, namelengthmax, version)
    assert (formed.pseudo_fullname if formed else None) == name


@pytest.mark.parametrize(
    ("folder", "filename", "version", "reason"),
    [
        ("root/private", "m.slx", "R2026a", "private or class folders"),
        ("root/@C", "m.slx", "R2026a", "private or class folders"),
        ("root/a*b", "m.slx", "R2026a", "with * in their names"),
        ("root", "end.slx", "R2026a", "its name 'end' is a MATLAB keyword"),
        ("root", "L" + "x" * 63 + ".slx", "R2024a", "longer than 63 characters"),
        ("root/+pk", "m.slx", "R2026b", "cannot reference it by name"),
        ("root/+for", "m.slx", "R2026a", "cannot reference it by name"),
    ],
)
def test_model_not_callable_reason(folder, filename, version, reason):
    namelengthmax = mat_naming.default_namelengthmax(version)
    assert reason in model_not_callable_reason(folder, filename, namelengthmax)


def test_handlers(tmp_path):
    project(tmp_path)
    slx = mat_handlers.handler_for(tmp_path / "probeModel.slx")
    assert isinstance(slx, mat_handlers.SlxHandler)
    assert slx.classify(tmp_path / "probeModel.slx") == "model"
    assert slx.read(tmp_path / "probeLib.slx") == ("library", None, [])
    assert slx.classify(tmp_path / "lfs.slx") == "unknown"
    assert slx.classify(tmp_path / "missing.slx") == "unknown"
    assert slx.read(tmp_path / "lfs.slx") == (
        "unknown",
        None,
        [("parse_error", "is a Git LFS pointer, not the model file.", None)],
    )
    assert slx.read(tmp_path / "notes.slx") == (
        "unknown",
        None,
        [
            (
                "parse_error",
                "is not a Simulink model, library or subsystem file.",
                None,
            )
        ],
    )
    with pytest.raises(FileNotFoundError):
        slx.read(tmp_path / "missing.slx")
    mdl = mat_handlers.handler_for(tmp_path / "mdl" / "probeLib.mdl")
    assert isinstance(mdl, mat_handlers.MdlHandler)
    assert mdl is not None
    assert [slx.naming, mdl.naming] == ["model", "model"]
    # no handler owns .xml, not even for a Simulink export
    assert mat_handlers.handler_by_extension("a.xml") is None
    assert mat_handlers.handler_for("a.xml") is None
    assert mat_handlers.handler_for(tmp_path / "export.xml") is None


def test_xml_files_are_not_opened(tmp_path, warnings, monkeypatch):
    """A Simulink export and the XML files of a MATLAB project are neither
    indexed nor opened, and give no warning; a folder ``x.xml/`` is an
    ordinary folder.
    """
    root = tmp_path / "src"
    root.mkdir()
    (root / "f.m").write_text("function f\nend\n", encoding="utf-8")
    (root / "export.xml").write_text(EXPORT_XML, encoding="utf-8")
    project_files = root / "resources" / "project"
    for name in ("Project.xml", "Root.type.Files/f.m.type.File.xml"):
        (project_files / name).parent.mkdir(parents=True, exist_ok=True)
        (project_files / name).write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<Info/>\n', encoding="utf-8"
        )
    (root / "x.xml").mkdir()
    (root / "x.xml" / "g.m").write_text("function g\nend\n", encoding="utf-8")
    opened = []

    def recorder(real):
        def wrapper(file, *args, **kwargs):
            opened.append(os.fspath(file) if not isinstance(file, int) else "")
            return real(file, *args, **kwargs)

        return wrapper

    # Record each file the index stage opens, through the built-in open,
    # io.open (used by pathlib) or os.open.
    monkeypatch.setattr(builtins, "open", recorder(builtins.open))
    monkeypatch.setattr(io, "open", recorder(io.open))
    monkeypatch.setattr(os, "open", recorder(os.open))
    source_index = build_index(IndexSettings(str(root)))
    monkeypatch.undo()
    refs = sorted(r["reference"] for r in source_index.index.values())
    assert refs == ["f.m", "x.xml/g.m"]
    assert any(p.endswith("f.m") for p in opened)  # the wrappers see reads
    assert [p for p in opened if p.lower().endswith(".xml")] == []
    assert warnings == []
    assert "x.xml/" in source_index.entities
    folder = mat_types.MatModule("src", str(root), "./")
    assert ("x.xml", "x.xml/") in folder.member_refs()


def test_index(tmp_path, warnings):
    root = project(tmp_path / "src")
    source_index = build_index(IndexSettings(str(root)))
    records = {r["reference"]: r for r in source_index.index.values()}
    assert {ref: r["type"] for ref, r in records.items()} == {
        "+pk/probeSub.slx": "subsystem",
        "@Cls/Cls.m": "class",
        "@Cls/inClass.slx": "model",
        "@Cls/sub/inSub.slx": "model",
        "lfs.slx": "unknown",
        "mdl/probeLib.mdl": "library",
        "notes.slx": "unknown",
        "private/probeRef.slx": "model",
        "probeLib.slx": "library",
        "probeModel.slx": "model",
        "same.m": "function",
        "same.slx": "model",
    }
    names = {ref: r["matlab_name"] for ref, r in records.items()}
    assert names["probeModel.slx"] == "probeModel"
    assert names["+pk/probeSub.slx"] is None
    assert names["private/probeRef.slx"] is None
    assert names["@Cls/inClass.slx"] is None
    # R2026a: .m files there are not callable, models still load.
    assert names["@Cls/sub/inSub.slx"] == "inSub"
    assert names["lfs.slx"] is None
    assert names["notes.slx"] is None
    assert sorted(source_index.matlab_names["same"]) == ["same.m", "same.slx"]
    assert sorted(source_index.matlab_names["probeLib"]) == [
        "mdl/probeLib.mdl",
        "probeLib.slx",
    ]
    assert "data.slx/" not in source_index.entities
    messages = sorted(warnings)
    assert (
        "folder_name",
        "[sphinxcontrib-matlabdomain] data.slx/: a folder must not be named like "
        "a .slx file; its contents are not documented.",
    ) in messages
    not_callable = [m for s, m in messages if s == "not_callable"]
    assert len(not_callable) == 3
    assert any(
        "+pk/probeSub.slx is not callable" in m and "global namespace" in m
        for m in not_callable
    )
    assert any(
        "private/probeRef.slx is not callable" in m and "private or class" in m
        for m in not_callable
    )
    assert any("@Cls/inClass.slx is not callable" in m for m in not_callable)
    assert any("lfs.slx is a Git LFS pointer" in m for _, m in messages)


@pytest.mark.parametrize("name", ["x.m", "x.MLAPP", "x.mdl", "x.md", "x.rst"])
def test_folders_named_like_files_are_errors(tmp_path, warnings, name):
    root = tmp_path / "src"
    (root / name).mkdir(parents=True)
    (root / name / "f.m").write_text("function f\nend\n")
    (root / "ok.d").mkdir()
    (root / "ok.d" / "g.m").write_text("function g\nend\n")
    source_index = build_index(IndexSettings(str(root)))
    assert [r["reference"] for r in source_index.index.values()] == ["ok.d/g.m"]
    (warning,) = warnings
    assert warning[0] == "folder_name"
    assert f"{name}/: a folder must not be named like a" in warning[1]
    folder = mat_types.MatModule("src", str(root), "./")
    assert folder.member_refs() == [("ok.d", "ok.d/")]


def test_apidoc_lists_simulink_files(tmp_path, warnings):
    root = project(tmp_path / "src")
    core = (
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/'
        '2006/metadata/core-properties"><cp:category>library</cp:category>'
        "</cp:coreProperties>"
    )
    with zipfile.ZipFile(root / "broken.slx", "w") as z:
        z.writestr("metadata/coreProperties.xml", core)
    source_index = build_index(IndexSettings(str(root)))
    warnings.clear()
    pages = build_pages(source_index, ApidocOptions("out", group="namespace"))
    sections = {
        (page.docname, title): [(e["title"], e["argument"]) for e in entries]
        for page in pages
        for title, entries in page.context.get("sections", ())
    }
    assert [title for docname, title in sections if docname == "global"] == [
        "Functions",
        "Classes",
        "Simulink Models",
        "Simulink Libraries",
        "Simulink Library Blocks",
    ]
    assert sections["pk", "Simulink Subsystem References"] == [
        ("+pk/probeSub.slx", "+pk/probeSub.slx")
    ]
    assert sections["global", "Simulink Libraries"] == [
        ("broken", "broken.slx"),
        ("mdl/probeLib.mdl", "mdl/probeLib.mdl"),
        ("probeLib.slx", "probeLib.slx"),
    ]
    blocks = sections["global", "Simulink Library Blocks"]
    assert ("probeLib.slx/Two Lines", "probeLib.slx/Two\n   Lines") in blocks
    assert len(blocks) == 16
    messages = [m for _, m in warnings]
    assert any("broken.slx: its blocks cannot be read" in m for m in messages)
    # one warning for the library, none for its blocks
    assert [m for m in messages if "probeLib" in m] == [
        "[scmd apidoc] probeLib is defined by several files in Global: "
        "mdl/probeLib.mdl, probeLib.slx; they are listed by path."
    ]
    folder = build_pages(source_index, ApidocOptions("out", group="folder"))
    root_page = next(p for p in folder if p.docname == "root")
    titles = [t for t, _ in root_page.context["sections"]]
    assert titles[-3:] == [
        "Simulink Models",
        "Simulink Libraries",
        "Simulink Library Blocks",
    ]


def test_apidoc_pages_build(tmp_path, make_app):
    root = tmp_path / "src"
    copy(SLX / "probeModel.slx", root / "probeModel.slx")
    copy(SLX / "probeLib.slx", root / "probeLib.slx")
    copy(SLX / "probeSub.slx", root / "probeSub.slx")
    copy(SLX / "probeRef.slx", root / "probeRef.slx")
    generate(
        build_index(IndexSettings(str(root))),
        ApidocOptions(str(tmp_path / "api"), separate=True),
    )
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\n'
        'matlab_src_code_project_root = "src"\nnitpicky = True\n'
    )
    (tmp_path / "index.rst").write_text(
        "Index\n=====\n\n.. toctree::\n\n   api/index\n"
    )
    app = make_app(srcdir=tmp_path, freshenv=True)
    app.build(force_all=True)
    assert app.warning.getvalue() == ""
    page = next((Path(app.outdir) / "api").glob("probeLib.slx~2FTwo*.html"))
    assert 'id="mat-probeLib.slx/Two~0ALines"' in page.read_text(encoding="utf-8")


def test_objects(tmp_path):
    project(tmp_path)
    model = mat_types.MatObject.parse_simulink(
        tmp_path / "probeModel.slx", "probeModel", "./"
    )
    assert isinstance(model, MatModel)
    assert model.__doc__ == "Model description line 1\nline 2"
    assert model.__module__ == "./"
    assert model.getter("Gain") is None
    sub = mat_types.MatObject.parse_simulink(
        tmp_path / "+pk" / "probeSub.slx", "probeSub", "+pk/"
    )
    assert isinstance(sub, MatSubsystemFile)
    lib = mat_types.MatObject.parse_simulink(
        tmp_path / "probeLib.slx", "probeLib", "./"
    )
    assert isinstance(lib, MatLibrary)
    block = lib.getter("Group/Inner Masked")
    assert isinstance(block, MatBlock)
    assert block.name == "Group/Inner Masked"
    assert block.library is lib
    assert block.__module__ == "./"
    # no block description: the mask's
    assert block.__doc__ == "Inner masked description."
    assert not hasattr(block, "ref")
    assert lib.getter("missing") is None
    assert lib.getter("__name__") == "probeLib"
    restored = pickle.loads(pickle.dumps(lib))
    assert isinstance(restored, MatLibrary)
    assert restored.diagram == lib.diagram
    empty = mat_types.placeholder("library", "x", "./")
    assert isinstance(empty, MatLibrary)
    assert empty.__doc__ is None
    assert empty.getter("Group/Inner Masked") is None


def test_build_lookups_and_incremental(make_app, tmp_path):
    src = project(tmp_path / "src")
    copy(SLX / "probeModel.slx", src / "models" / "probeModel2.slx")
    (src / "models" / "helper.m").write_text("function helper\n% Helper.\nend\n")
    (tmp_path / "conf.py").write_text(CONF)
    (tmp_path / "index.rst").write_text(
        "Index\n=====\n\n.. mat:autofolder:: models\n   :members:\n"
    )
    app = make_app(srcdir=tmp_path)
    app.build()
    html = (app.outdir / "index.html").read_text(encoding="utf-8")
    assert "Helper." in html

    dom = app.env.get_domain("mat")
    block = mat_types.lookup_reference(dom, "probeLib.slx/Group/Inner Masked")
    assert isinstance(block, MatBlock)
    assert block.ref == "probeLib.slx/Group/Inner Masked"
    assert mat_types.lookup_reference(dom, "probeLib.slx/missing") is None
    found = mat_types.find_source(dom, "probeModel")
    assert [(ref, type(obj)) for ref, obj in found] == [("probeModel.slx", MatModel)]
    assert {ref for ref, _ in mat_types.find_source(dom, "same")} == {
        "same.m",
        "same.slx",
    }
    assert mat_types.display_name(dom, "+pk/probeSub.slx") == "+pk/probeSub.slx"
    assert mat_types.display_name(dom, "probeLib.slx") == "probeLib"
    assert mat_types.resolve(dom, "export.xml") is None
    broken = mat_types.resolve(dom, "notes.slx")
    assert isinstance(broken, mat_types.MatScript)

    # The page listed the folder's files: a changed model makes it outdated.
    model = src / "models" / "probeModel2.slx"
    used = dom.data["doc_sources"]["index"]
    assert str(model) in used
    copy(SLX / "probeRef.slx", model)
    app2 = make_app(srcdir=tmp_path, freshenv=False)
    app2.build()
    assert app2.env.get_domain("mat").read_docnames == ["index"]


def test_linker_addresses_match_stable_addresses():
    """``simulinkDocumentationLinker.m`` gives the addresses of ``mat_urls``
    (``linker.json`` is written by ``make_fixtures("linker", ...)``).
    """
    cases = json.loads((FIXTURES.parent / "linker.json").read_text("utf-8"))["cases"]
    assert len(cases) == 27
    for case in cases:
        ref = case["reference"]
        names, _ = docnames([ref], "html")
        assert f"mat/ref/{names[ref]}.html" == case["address"], ref


def test_block_output_names():
    refs = ["src/lib.slx", "src/lib.slx/Group/Inner Masked", "src/lib.slx/A//B"]
    names, collisions = docnames(refs)
    assert names == {
        "src/lib.slx": "src/lib.slx",
        "src/lib.slx/Group/Inner Masked": "src/lib.slx~2FGroup~2FInner~20Masked",
        "src/lib.slx/A//B": "src/lib.slx~2FA~2F~2FB",
    }
    assert collisions == []


@pytest.mark.parametrize(
    ("text", "target"),
    [
        (
            'web(sphinxcontrib.matlabdomain.simulinkDocumentationLinker("src/m.slx"))',
            ("reference", "src/m.slx"),
        ),
        (
            "web(sphinxcontrib.matlabdomain.simulinkDocumentationLinker("
            '"src/l.slx/Two" + newline + "Lines"));',
            ("reference", "src/l.slx/Two\nLines"),
        ),
        (
            "web( sphinxcontrib.matlabdomain.simulinkDocumentationLinker( "
            '"a/""q"".slx" ) )',
            ("reference", 'a/"q".slx'),
        ),
        ("web('https://example.org/x.html')", ("url", "https://example.org/x.html")),
        ('web("file:///C:/doc/x.html", "-browser")', ("url", "file:///C:/doc/x.html")),
        (
            "  https://example.org/page.html\nmore text",
            ("url", "https://example.org/page.html"),
        ),
        ("mailto:team@example.org", ("url", "mailto:team@example.org")),
        ("Plain help text.", None),
        ("eval('doc gain')", None),
        ("", None),
    ],
)
def test_help_target(text, target):
    assert mat_simulink.help_target(text) == target


def test_simulink_files_share_names_with_code(make_app, tmp_path):
    """A model named like a function is a second object of that name, like a
    second ``.m`` file: "See also" warns, or links with
    ``matlab_link_shadowed_files_to_chooser_pages`` (to the function: models have no
    directive yet). Directives that document code still find the function.
    """
    src = tmp_path / "src"
    copy(SLX / "probeRef.slx", src / "same.slx")
    copy(SLX / "probeRef.slx", src / "other" / "same.slx")
    (src / "same.m").write_text("function same\n% Same help.\nend\n")
    (src / "user.m").write_text(
        "function user\n% Calls same.\n%\n% See also same\nend\n"
    )
    (tmp_path / "index.rst").write_text(
        "Index\n=====\n\n.. mat:autofunction:: same\n\n.. mat:autofunction:: user\n\n"
        ".. mat:function:: same\n   :no-index:\n"
    )
    for shadowed in (False, True):
        (tmp_path / "conf.py").write_text(
            CONF
            + "matlab_auto_link = 'all'\n"
            + f"matlab_link_shadowed_files_to_chooser_pages = {shadowed}\n"
        )
        app = make_app(srcdir=tmp_path, freshenv=True)
        app.build(force_all=True)
        app.cleanup()
        warnings = app.warning.getvalue()
        html = (app.outdir / "index.html").read_text(encoding="utf-8")
        if shadowed:
            assert "ambiguous" not in warnings
            # "Calls same." and "See also same"
            assert html.count('href="#mat-same.m"') == 2
        else:
            assert (
                "'same' in the docstring of user.m matches several objects: same.m, "
                "same.slx" in warnings
            )
            assert 'href="#mat-same.m"' not in html
    dom = app.env.get_domain("mat")
    assert mat_types.find_source(dom, "same.slx", accept=mat_types.is_code_object) == []


def test_unparsable_model_is_a_placeholder(tmp_path):
    import zipfile

    root = tmp_path / "src"
    root.mkdir()
    core = (
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/'
        '2006/metadata/core-properties"><cp:category>model</cp:category>'
        "</cp:coreProperties>"
    )
    with zipfile.ZipFile(root / "broken.slx", "w") as z:
        z.writestr("metadata/coreProperties.xml", core)
    source_index = build_index(IndexSettings(str(root)))
    (record,) = source_index.index.values()
    assert record["type"] == "model"
    handler = mat_handlers.handler_by_extension("broken.slx")
    obj = mat_types._parse(handler, str(root / "broken.slx"), "broken", "./", "model")
    assert isinstance(obj, MatModel)
    assert obj.diagram is None
    (warning,) = obj.source_warnings
    assert warning[0] == "parse_error"
    assert "SimulinkFileError" in warning[1]
