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
                '"' + LINKER.format('\\"hid.mdl/Two\\" + newline + \\"Lines\\"') + '"',
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


def build(make_app, tmp_path, index, conf=""):
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
    index += ".. mat:autosimulink_model:: probeModel\n"
    page, warnings = build(make_app, tmp_path, index)
    assert warnings == ""
    blocks = text(page).split("Simulink library block")[1:]
    assert 'href="https://example.org/help"' in page
    assert "Help" not in blocks[1]  # its own page
    assert 'href="#mat-probeModel.slx"' in page
    assert "Help" not in blocks[3].split("Simulink model")[0]  # a newline in it
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
    assert 'id="mat-probeLib.slx/A~2F~2FB"' not in page
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
