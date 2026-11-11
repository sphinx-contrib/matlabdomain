"""Documenting Simulink files and library blocks (S5a): the
``mat:simulink_*`` directives, their auto forms and roles.
"""

import html
import re
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from sphinxcontrib import mat_documenters

SLX = Path(__file__).parent / "simulink" / "fixtures" / "R2026b" / "slx"
LINKER = "web(sphinxcontrib.matlabdomain.simulinkDocumentationLinker({}))"


def _object(lines):
    return "".join(f"          {line}\n" for line in lines)


HID = (
    "Library {\n  System {\n"
    + "".join(
        f'    Block {{\n      BlockType SubSystem\n      Name "{name}"\n'
        '      Object {\n        $ClassName "Simulink.Mask"\n'
        f"        Type {typ}\n        Help {help_}\n"
        '        Array {\n          PropName "Parameters"\n'
        + _object(["Object {", '  Name "a"', '  Prompt "Shown"', '  Value "a`b"', "}"])
        + _object(["Object {", '  Name "b"', '  Visible "off"', "}"])
        + _object(["Object {", '  Prompt "No name"', "}"])
        + "        }\n      }\n    }\n"
        for name, typ, help_ in [
            ("M", '"T"', '"https://example.org/help"'),
            ("Self", '""', '"' + LINKER.format('\\"hid.mdl/Self\\"') + '"'),
            ("Other", '"a`b"', '"' + LINKER.format('\\"probeModel.slx\\"') + '"'),
            (
                "Newline",
                '""',
                '"'
                + LINKER.format('\\"probeLib.slx/Two\\" + newline + \\"Lines\\"')
                + '"',
            ),
        ]
    )
    + "  }\n}\n"
)

# Sublibrary blocks (an empty subsystem whose OpenFcn opens a library), a
# masked block with an OpenFcn callback, and a linked block.
TOP = """\
Library {
  System {
    Block {
      BlockType SubSystem
      Name "Sub"
      OpenFcn "hid"
      MaskType "Folder"
      System {
      }
    }
    Block {
      BlockType SubSystem
      Name "Ext"
      OpenFcn "open_system('dsplib');"
    }
    Block {
      BlockType SubSystem
      Name "Callback"
      OpenFcn "myCallback"
      MaskType "CB"
      MaskDescription "Opens a dialog."
      MaskHelp "Opens   a dialog."
      System {
        Block {
          BlockType Constant
          Name "C"
        }
      }
    }
    Block {
      BlockType Reference
      Name "Lnk"
      SourceBlock "hid/M"
    }
  }
}
"""


def build(make_app, tmp_path, index, conf="", before_build=None):
    """Build HTML of the R2026b fixtures and ``hid.mdl``; return the page and
    the warnings.
    """
    src = tmp_path / "src"
    src.mkdir(parents=True, exist_ok=True)
    for name in ("probeModel", "probeLib", "probeSub", "probeRef"):
        shutil.copyfile(SLX / f"{name}.slx", src / f"{name}.slx")
    (src / "hid.mdl").write_text(HID)
    (src / "top.mdl").write_text(TOP)
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\n'
        f'matlab_src_code_project_root = "src"\n{conf}'
    )
    (tmp_path / "index.rst").write_text(f"Index\n=====\n\n{index}")
    app = make_app(srcdir=tmp_path, freshenv=True)
    if before_build is not None:
        before_build()
    app.build(force_all=True)
    app.cleanup()
    page = (Path(app.outdir) / "index.html").read_text(encoding="utf-8")
    return page, app.warning.getvalue()


def text(page):
    words = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", page)).split())
    return words.replace(" ¶", "").replace(" :", ":")


INDEX = """\
.. mat:autosimulink_model:: probeModel

.. mat:autosimulink_subsystem_reference:: probeSub

.. mat:autosimulink_library:: probeLib

.. mat:autosimulink_library_block:: probeLib.slx/Gain Block

.. mat:autosimulink_library_block:: probeLib.slx/A//B

.. mat:autosimulink_model:: probeRef
   :metadata: creator, release

.. mat:simulink_library_block:: probeLib/Two Lines
   :reference: "probeLib.slx/Two\\nLines"

* :mat:simulink_model:`probeModel`
* :mat:simulink_library_block:`probeLib/Gain Block`
* :mat:simulink_subsystem_reference:`probeSub`
* :mat:simulink_library:`probeLib`
"""


def test_simulink_pages(make_app, tmp_path):
    page, warnings = build(make_app, tmp_path, INDEX)
    assert warnings == ""
    words = text(page)
    assert "Simulink model probeModel" in words
    assert "Simulink subsystem reference probeSub" in words
    assert "Simulink library probeLib" in words
    assert "Simulink library block probeLib/ Gain Block" in words
    assert 'id="mat-probeModel.slx"' in page
    assert 'id="mat-probeLib.slx/Gain~20Block"' in page
    assert 'id="mat-probeLib.slx/Two~0ALines"' in page
    # the description, then the mask, metadata, parameters and ports
    assert "Model description line 1 line 2" in words
    assert "Mask type: ModelMaskType" in words
    assert "Mask description: Model mask description" in words
    assert "Help: Model mask help" in words
    assert "Release: R2026b" in words
    assert "Model version: 1.1" in words
    assert "Created by" not in words.split("Simulink model probeRef")[0]
    assert "Created by: matlabdomain Release: R2026b" in words
    assert "Model version" not in words.split("Simulink model probeRef")[1]
    assert "Mask parameters: k ( edit ) – Factor k. Default: 1 ." in words
    assert (
        "Port Name Data type Dimensions Unit Description input 1 u double 3 m "
        "input u doc input 2 w second input input 3 busPort.sig1 output 1 y "
        "output y doc" in words
    )
    # an empty column is left out
    assert "Port Name Data type Description input 1 in single sub input doc" in words
    assert "Options: fast , slow ." in words
    # the library's own page has no ports
    library = words.split("Simulink library probeLib")[1].split(
        "Simulink library block"
    )[0]
    assert "Ports" not in library
    # roles
    for anchor in (
        "mat-probeModel.slx",
        "mat-probeLib.slx/Gain~20Block",
        "mat-probeSub.slx",
        "mat-probeLib.slx",
    ):
        assert f'href="#{anchor}"' in page


def test_help_links_and_hidden_parameters(make_app, tmp_path):
    index = "".join(
        f".. mat:autosimulink_library_block:: hid.mdl/{name}\n\n"
        for name in ("M", "Self", "Other", "Newline")
    )
    index += ".. mat:autosimulink_model:: probeModel\n\n"
    index += ".. mat:autosimulink_library_block:: probeLib.slx/Two Lines\n"
    page, warnings = build(make_app, tmp_path, index)
    assert warnings == ""
    blocks = text(page).split("Simulink library block")[1:]
    assert 'href="https://example.org/help"' in page
    assert "Help" not in blocks[1]  # its own page
    assert 'href="#mat-probeModel.slx"' in page
    # a line break in the target: a link all the same
    assert "Help: probeLib.slx/Two Lines" in blocks[3]
    assert 'href="#mat-probeLib.slx/Two~0ALines"' in page
    assert "Mask type: a`b" in blocks[2]
    assert "Mask type" not in blocks[1]
    # hidden and unnamed parameters are left out; a value with ` is escaped
    assert "a – Shown. Default: a`b." in blocks[0]
    assert " b " not in blocks[0] + " "
    assert "No name" not in blocks[0]


@pytest.mark.parametrize(
    ("conf", "option", "shown"),
    [
        ("", ":hidden-mask-parameters:", True),
        ("autodoc_default_options = {'hidden-mask-parameters': True}\n", "", True),
        (
            "autodoc_default_options = {'hidden-mask-parameters': True}\n",
            ":no-hidden-mask-parameters:",
            False,
        ),
    ],
)
def test_hidden_mask_parameters_on_request(make_app, tmp_path, conf, option, shown):
    index = f".. mat:autosimulink_library_block:: hid.mdl/M\n   {option}\n"
    page, warnings = build(make_app, tmp_path, index, conf)
    assert warnings == ""
    assert ("<strong>b</strong>" in page) is shown


def test_ports_in_number_order_then_control_ports(make_app, tmp_path):
    from test_mat_simulink import PORTS_OUT_OF_ORDER

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "ports.mdl").write_text(PORTS_OUT_OF_ORDER)
    page, _ = build(make_app, tmp_path, ".. mat:autosimulink_model:: ports\n")
    assert (
        "Ports Port Name input 1 first input 2 second output 1 y "
        "enable Enable trigger Trigger"
    ) in text(page)


def test_metadata_settings(make_app, tmp_path):
    index = (
        ".. mat:autosimulink_model:: probeRef\n\n"
        ".. mat:autosimulink_model:: probeModel\n   :metadata: bogus\n"
    )
    page, warnings = build(
        make_app, tmp_path, index, "matlab_simulink_metadata = ['modified']\n"
    )
    assert "unknown Simulink metadata 'bogus'" in warnings
    assert "[mat.simulink]" in warnings
    assert "Last modified: 2026-11-07T03:40:39Z" in text(page)
    assert "Release" not in text(page)


def test_wrong_kind_and_unreadable_file(make_app, tmp_path):
    import zipfile

    src = tmp_path / "src"
    src.mkdir()
    core = (
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/'
        '2006/metadata/core-properties"><cp:category>model</cp:category>'
        "</cp:coreProperties>"
    )
    with zipfile.ZipFile(src / "broken.slx", "w") as z:
        z.writestr("metadata/coreProperties.xml", core)
    index = (
        ".. mat:autosimulink_model:: probeLib\n\n"
        ".. mat:autosimulink_model:: broken\n\n"
        ".. mat:simulink_model:: probeModel\n\n"
        ".. mat:simulink_model:: nowhere\n"
    )
    page, warnings = build(make_app, tmp_path, index)
    assert "don't know which object to document for 'probeLib'" in warnings
    assert "broken.slx" in warnings  # mat.parse_error
    words = text(page)
    assert "Simulink model broken" in words
    # a description directive finds the file it names
    assert 'id="mat-probeModel.slx"' in page
    assert 'id="mat-nowhere"' in page


LIBRARIES = """\
.. mat:autosimulink_model:: probeModel

.. mat:autosimulink_library:: hid
   :members:
   :undoc-members:

.. mat:autosimulink_library:: top
   :members:

.. mat:autosimulink_library:: probeLib
   :members:
   :undoc-members:
   :exclude-members: Gain Block
"""


def test_library_members_and_links(make_app, tmp_path):
    page, warnings = build(make_app, tmp_path, LIBRARIES, "nitpicky = True\n")
    assert warnings == ""
    words = text(page)
    top = words.split("Simulink library top")[1].split("Simulink library probeLib")[0]
    # a callback OpenFcn on a block with contents: documented
    assert 'id="mat-top.mdl/Callback"' in page
    assert "Simulink library block top/ Callback Opens a dialog." in top
    assert "Help" not in top  # the same as the description
    assert "Links to other blocks Sub: hid Ext: dsplib Lnk: hid/M" in top
    assert 'href="#mat-hid.mdl"' in page
    assert 'href="#mat-hid.mdl/M"' in page
    assert 'id="mat-top.mdl/Sub"' not in page
    lib = words.split("Simulink library probeLib")[1]
    # in the library's order, undocumented blocks too, one excluded
    assert 'id="mat-probeLib.slx/Gain~20Block"' not in page
    assert 'id="mat-probeLib.slx/No~20Description"' in page
    assert 'id="mat-probeLib.slx/Two~0ALines"' in page
    assert "Simulink library block probeLib/ Two Lines" in lib
    # a MathWorks library: text, without a warning
    assert "Lib Doc: simulink/Model-Wide Utilities/DocBlock" in lib


def test_line_break_in_a_block_name_is_a_space(make_app, tmp_path):
    # As in a role's target: "Two Lines" names the block "Two\nLines", and
    # the anchor stays the block's own.
    anchor = 'id="mat-probeLib.slx/Two~0ALines"'
    page, warnings = build(
        make_app,
        tmp_path,
        ".. mat:autosimulink_library:: probeLib\n"
        "   :members: Two Lines, No Such Block\n",
    )
    assert page.count(anchor) == 1
    assert "No Such Block" in warnings and "[mat.not_found]" in warnings

    page, _ = build(
        make_app,
        tmp_path,
        ".. mat:autosimulink_library:: probeLib\n"
        "   :members:\n   :exclude-members: Two Lines\n",
    )
    assert anchor not in page and 'id="mat-probeLib.slx/v1.2"' in page

    page, warnings = build(
        make_app, tmp_path, ".. mat:autosimulink_library_block:: probeLib/Two Lines\n"
    )
    assert 'id="mat-probeLib.slx/Two~0ALines"' in page
    assert "not_found" not in warnings


def test_named_library_members(make_app, tmp_path):
    index = (
        ".. mat:autosimulink_library:: probeLib\n"
        "   :members: Gain Block, Lib Doc\n\n"
        ".. mat:autosimulink_library:: hid\n\n"
        "* :mat:simulink_library_block:`nowhere/x`\n"
        "* :mat:simulink_library_block:`hid/Missing`\n"
        "* :mat:simulink_model:`gone.slx`\n"
    )
    page, warnings = build(make_app, tmp_path, index, "nitpicky = True\n")
    assert 'id="mat-probeLib.slx/Gain~20Block"' in page
    assert 'id="mat-probeLib.slx/A//B"' not in page  # not named in :members:
    assert "Links to other blocks Lib Doc:" in text(page)
    # hid has no members: no list
    assert text(page).count("Links to other blocks") == 1
    # outside the project: text; in it: "not found"
    assert "nowhere/x" not in warnings
    assert "target not found: hid/Missing" in warnings
    assert "target not found: gone.slx" in warnings


def test_reference_option_is_one_line():
    lines = []
    fake = SimpleNamespace(
        objtype="simulink_library_block",
        ref='lib.slx/Two\nLines "x"',
        display="lib/Two\nLines",
        options=SimpleNamespace(no_index=False, noindex=True),
        get_sourcename=lambda: "src",
        add_line=lambda line, _source: lines.append(line),
    )
    documenter = cast(Any, mat_documenters.MatSimulinkDocumenter)
    fake.format_name = lambda: documenter.format_name(fake)
    documenter.add_directive_header(fake, "")
    assert lines == [
        ".. mat:simulink_library_block:: lib/Two Lines",
        "   :noindex:",
        '   :reference: "lib.slx/Two\\nLines \\"x\\""',
    ]


# --- Simulink documentation files (S5c) ---------------------------------------

HID_RST = """\
Hid library
===========

Library intro.

M
-

Block M text.

Details
~~~~~~~

More M.

Nothing
-------

Stray text.
"""

MYST = 'extensions = ["sphinxcontrib.matlab", "myst_parser"]\n'


def write_docs(tmp_path, files):
    src = tmp_path / "src"
    src.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (src / name).write_text(content, encoding="utf-8")


def test_library_documentation_file(make_app, tmp_path):
    write_docs(tmp_path, {"hid.rst": HID_RST})
    index = (
        ".. mat:autosimulink_library:: hid\n   :members:\n\n"
        ".. mat:autosimulink_library_block:: hid.mdl/M\n   :no-index:\n"
    )
    page, warnings = build(make_app, tmp_path, index)
    words = text(page)
    library = words.split("Simulink library hid")[1].split("Simulink library block")[0]
    assert "Hid library" not in words
    assert "Library intro. Nothing Stray text." in library
    blocks = words.split("Simulink library block hid/ M")
    assert len(blocks) == 3, warnings
    for block in blocks[1:]:
        assert block.lstrip().startswith("Block M text. Details More M.")
    assert 'class="rubric" id="details"' in page
    # without a description or a section: not documented
    assert 'id="mat-hid.mdl/Self"' not in page
    hid = str(tmp_path / "src" / "hid.rst")
    assert (
        f"{hid}:17: WARNING: [sphinxcontrib-matlabdomain] hid.rst: the heading "
        "'Nothing' names no masked block of hid.mdl; its text goes with the "
        "library. [mat.simulink]" in warnings
    )
    assert (
        f"{hid}:1: WARNING: [sphinxcontrib-matlabdomain] hid.rst has no section for "
        "the blocks 'Self', 'Other', 'Newline'. [mat.simulink]" in warnings
    )
    # the file is not a page of its own: no toctree warning
    assert warnings.count("WARNING") == 2, warnings


def test_markdown_documentation_file(make_app, tmp_path):
    pytest.importorskip("myst_parser")  # not in the Sphinx dev job
    write_docs(
        tmp_path,
        {
            "probeModel.md": "# Title\n\nModel *extra* text.\n\n## Usage\n\nUse it.\n",
            "probeModel.rst": "Not used\n========\n\nRST text.\n",
            "probeSub.rst": "Only text, no heading.\n",
            "hid.md": "# Hid\n\n## Self ##\n\nSelf text.\n",
        },
    )
    index = (
        ".. mat:autosimulink_model:: probeModel\n\n"
        ".. mat:autosimulink_subsystem_reference:: probeSub\n\n"
        ".. mat:autosimulink_library:: hid\n   :members:\n\n"
        ".. mat:simulink_model:: probeModel\n   :no-index:\n\n"
        ".. mat:simulink_model:: nowhere\n\n"
        "   .. sphinxcontrib-matlabdomain: Simulink documentation file\n"
    )
    page, warnings = build(make_app, tmp_path, index, MYST)
    words = text(page)
    assert (
        "Model description line 1 line 2 Model extra text. Usage Use it. "
        "Mask type: ModelMaskType" in words
    )
    assert "RST text" not in words
    assert "Title" not in words
    assert "Only text, no heading." in words
    assert "Simulink library block hid/ Self Self text." in words
    assert 'id="mat-hid.mdl/M"' not in page
    # a description directive reads no file
    assert words.count("Model extra text.") == 1
    rst = str(tmp_path / "src" / "probeModel.rst")
    assert (
        f"{rst}:1: WARNING: [sphinxcontrib-matlabdomain] probeModel.rst is not used: "
        "probeModel.md documents probeModel.slx (see matlab_simulink_doc_suffixes). "
        "[mat.simulink]" in warnings
    )
    assert "hid.md has no section for the blocks 'M', 'Other', 'Newline'" in warnings
    assert warnings.count("WARNING") == 2, warnings


def test_markdown_documentation_file_needs_myst(make_app, tmp_path):
    from sphinx.errors import ConfigError

    write_docs(tmp_path, {"probeModel.md": "# Title\n"})
    with pytest.raises(ConfigError, match="need myst_parser"):
        build(make_app, tmp_path, "")
    # without .md in the suffixes, it is a plain file (other tests' myst-parser
    # leaves ".md" in the default source_suffix)
    write_docs(tmp_path / "b", {"probeModel.md": "# Title\n"})
    _page, warnings = build(
        make_app,
        tmp_path / "b",
        INDEX,
        "matlab_simulink_doc_suffixes = ['.rst']\nsource_suffix = ['.rst']\n",
    )
    assert warnings == ""


def test_unreadable_documentation_file(make_app, tmp_path):
    # removed after the index stage found it
    write_docs(tmp_path, {"hid.rst": HID_RST})
    index = (
        ".. mat:autosimulink_library:: hid\n   :members:\n\n"
        ".. mat:autosimulink_library:: hid\n   :no-index:\n"
    )
    _page, warnings = build(
        make_app, tmp_path, index, before_build=(tmp_path / "src" / "hid.rst").unlink
    )
    assert warnings.count("hid.rst cannot be read") == 1, warnings


def test_documentation_file_is_not_a_sidecar_doc(make_app, tmp_path):
    from sphinxcontrib import mat_types

    root = tmp_path / "proj"
    docs = root / "docs"
    docs.mkdir(parents=True)
    shutil.copyfile(SLX / "probeModel.slx", root / "probeModel.slx")
    (root / "probeModel.rst").write_text("Doc\n===\n\nModel doc.\n")
    (root / "other.rst").write_text("Other\n=====\n")
    # a Simulink file in the Sphinx source folder, with its documentation
    shutil.copyfile(SLX / "probeSub.slx", docs / "probeSub.slx")
    (docs / "probeSub.rst").write_text("Sub doc.\n")
    (docs / "_skip").mkdir()
    (docs / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\n'
        'matlab_src_code_project_root = ".."\n'
        'matlab_src_sidecar_suffixes = [".rst"]\n'
    )
    (docs / "index.rst").write_text(
        "Index\n=====\n\n.. mat:autosimulink_model:: probeModel\n\n"
        ".. mat:autosimulink_subsystem_reference:: docs/probeSub.slx\n\n"
        ".. mat:autosidecar:: other.rst\n"
    )
    app = make_app(srcdir=docs, freshenv=True)
    app.build(force_all=True)
    page = (Path(app.outdir) / "index.html").read_text(encoding="utf-8")
    assert "Model doc." in page
    assert "Sub doc." in page
    data = app.env.domaindata["mat"]
    assert sorted(r["reference"] for r in data["sidecars"].values()) == ["other.rst"]
    assert sorted(r["reference"] for r in data["simulink_docs"].values()) == [
        "docs/probeSub.rst",
        "probeModel.rst",
    ]
    assert app.warning.getvalue() == ""
    assert "probeSub.rst" in app.config.exclude_patterns
    settings = mat_types.IndexSettings(str(root), simulink_doc_suffixes=(".rst",))
    assert mat_types.sidecar_paths(settings) == []


def test_every_block_has_a_section_and_directive_content(make_app, tmp_path):
    sections = "".join(
        f"{name}\n{'-' * len(name)}\n\n{name} text.\n\n"
        for name in ("M", "Self", "Other", "Newline")
    )
    write_docs(tmp_path, {"hid.rst": f"Hid\n===\n\n{sections}"})
    index = (
        ".. mat:autosimulink_library:: hid\n   :members:\n\n"
        "   Content of the directive.\n"
    )
    page, warnings = build(make_app, tmp_path, index)
    assert warnings == ""
    assert "Content of the directive." in text(page)
    assert "Newline text." in text(page)


def test_suffix_errors_and_another_drive(make_app, tmp_path, monkeypatch):
    from sphinx.errors import ConfigError

    from sphinxcontrib import mat_sidecars, mat_types

    with pytest.raises(ConfigError, match="must be a list"):
        mat_types.simulink_doc_suffix_list(".md")
    with pytest.raises(ConfigError, match=r"'\.txt' is not a documentation suffix"):
        mat_types.simulink_doc_suffix_list([".txt"])
    # Simulink documentation files only: no warning about another drive
    monkeypatch.setattr(mat_sidecars, "same_drive", lambda *_: False)
    _page, warnings = build(make_app, tmp_path, "")
    assert warnings == ""


# --- References (S5d) ---------------------------------------------------------

REFERENCES = (
    "References Doc Text (library link): simulink/Model-Wide Utilities/DocBlock "
    "Linked Gain (library link): probeLib/Gain Block MdlRef (model reference): "
    "probeRef SubRef (subsystem reference): probeSub"
)


@pytest.mark.parametrize(
    ("conf", "option", "shown"),
    [
        ("", "", False),
        ("", ":references:", True),
        ("autodoc_default_options = {'references': True}\n", "", True),
        ("autodoc_default_options = {'references': True}\n", ":no-references:", False),
    ],
)
def test_references_list(make_app, tmp_path, conf, option, shown):
    index = (
        f".. mat:autosimulink_model:: probeModel\n   {option}\n\n"
        ".. mat:autosimulink_model:: probeRef\n   :references:\n\n"
        ".. mat:autosimulink_subsystem_reference:: probeSub\n\n"
        ".. mat:autosimulink_library_block:: probeLib.slx/Gain Block\n"
    )
    page, warnings = build(make_app, tmp_path, index, f"nitpicky = True\n{conf}")
    assert warnings == ""
    assert (REFERENCES in text(page)) is shown
    # links to the project's files; a MathWorks library stays text
    assert ('href="#mat-probeRef.slx"' in page) is shown
    assert ('href="#mat-probeSub.slx"' in page) is shown
    assert ('href="#mat-probeLib.slx/Gain~20Block"' in page) is shown
    # probeRef uses nothing: no list
    assert text(page).count("References") == shown


def test_reference_targets_that_are_not_names():
    from sphinxcontrib.mat_simulink import Reference

    references = (
        Reference("model", "A", "<Enter Model Name>"),
        Reference("model", "B", "probeRef.slx"),
        Reference("subsystem", "C\nD", "sub.mdl"),
    )
    fake = SimpleNamespace(
        object=SimpleNamespace(diagram=SimpleNamespace(references=references)),
        options={"references": True},
    )
    lines = cast(Any, mat_documenters.MatSimulinkDocumenter).reference_lines(fake)
    assert lines[2:5] == [
        "* ``A`` (model reference): ``<Enter Model Name>``",
        "* ``B`` (model reference): :mat:simulink_model:`probeRef`",
        "* ``C D`` (subsystem reference): :mat:simulink_subsystem_reference:`sub`",
    ]


# --- links from MATLAB help to Simulink files (S5e) -----------------------------

USES = """\
function uses
% USES Runs probeSub through probeLib.
%
% See also probeModel, hid
end
"""


@pytest.mark.parametrize("auto_link", ["basic", "all"])
def test_help_links_to_simulink_files(make_app, tmp_path, auto_link):
    write_docs(tmp_path, {"uses.m": USES})
    index = (
        ".. mat:autofunction:: uses\n\n"
        ".. mat:autosimulink_model:: probeModel\n\n"
        ".. mat:autosimulink_library:: probeLib\n\n"
        ".. mat:autosimulink_library:: hid\n\n"
        ".. mat:autosimulink_subsystem_reference:: probeSub\n"
    )
    conf = f"matlab_auto_link = {auto_link!r}\nnitpicky = True\n"
    page, warnings = build(make_app, tmp_path, index, conf)
    assert warnings == ""
    help_ = page.split('id="mat-uses.m"')[1].split("Simulink model")[0]
    assert 'href="#mat-probeModel.slx"' in help_
    assert 'href="#mat-hid.mdl"' in help_
    linked = 'href="#mat-probeSub.slx"' in help_, 'href="#mat-probeLib.slx"' in help_
    assert linked == ((True, True) if auto_link == "all" else (False, False))
