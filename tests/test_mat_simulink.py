"""Reading Simulink files without MATLAB (``sphinxcontrib.mat_simulink``).

The fixtures in ``tests/simulink/fixtures`` were written by
``tests/simulink/make_fixtures.m``: one set per release where the file
format changes. ``tests/simulink/oracle.json`` holds what
the Simulink API reports for each fixture; the reader must agree.
"""

import codecs
import json
import pickle
import zipfile
from pathlib import Path

import pytest

from sphinxcontrib import mat_simulink
from sphinxcontrib.mat_simulink import (
    SimulinkFileError,
    _model,
    _nodes,
    _parts,
    classify,
    read_diagram,
    simulink_release,
)

HERE = Path(__file__).parent / "simulink"
FIXTURES = HERE / "fixtures"
ORACLE = json.loads((HERE / "oracle.json").read_text(encoding="utf-8"))["fixtures"]


def _as_list(value):
    # jsonencode writes a one-element struct array as an object.
    if isinstance(value, list):
        return value
    return [] if not value else [value]


def _mask(mask):
    if mask is None:
        return None
    return {
        "type": mask.type,
        "description": mask.description,
        "help": mask.help,
        "parameters": [
            {"name": p.name, "prompt": p.prompt, "type": p.type, "value": p.value}
            for p in mask.parameters
        ],
    }


def _oracle_mask(mask):
    return {**mask, "parameters": _as_list(mask["parameters"])} if mask else None


def _sorted(items):
    return sorted(items, key=lambda item: json.dumps(item, sort_keys=True))


@pytest.mark.parametrize("entry", ORACLE, ids=[e["file"] for e in ORACLE])
def test_reader_matches_simulink(entry):
    path = FIXTURES / entry["file"]
    facts = entry["facts"]
    diagram = read_diagram(path)

    assert classify(path) == facts["kind"]
    assert diagram.kind == facts["kind"]
    assert diagram.name == path.stem
    assert diagram.description == facts["description"]
    assert diagram.release == facts["release"]
    assert _mask(diagram.system_mask) == _oracle_mask(facts["systemMask"])
    ports = [
        {
            "blockType": p.block_type,
            "name": p.name,
            "port": p.number,
            "dataType": p.data_type,
            "dimensions": p.dimensions,
            "unit": p.unit,
            "description": p.description,
            "portName": p.port_name,
            "element": p.element,
        }
        for p in diagram.ports
    ]
    assert _sorted(ports) == _sorted(_as_list(facts["ports"]))
    references = [
        {"kind": r.kind, "block": r.block, "target": r.target}
        for r in diagram.references
    ]
    assert _sorted(references) == _sorted(_as_list(facts["references"]))
    blocks = [
        {
            "path": b.path,
            "link": b.link,
            "mask": _mask(b.mask),
            "description": b.description,
        }
        for b in diagram.library_blocks
    ]
    expected = [
        {**b, "mask": _oracle_mask(b["mask"])} for b in _as_list(facts["libraryBlocks"])
    ]
    assert _sorted(blocks) == _sorted(expected)


def test_oracle_covers_every_layout():
    layouts = {read_diagram(FIXTURES / e["file"]).layout for e in ORACLE}
    assert layouts == {"slx", "mdl-opc", "mdl-classic"}


def test_library_blocks_and_metadata():
    lib = read_diagram(FIXTURES / "R2026b" / "slx" / "probeLib.slx")
    by_path = {b.path: b for b in lib.library_blocks}
    gain = by_path["Gain Block"]
    assert gain.mask is not None
    assert [p.options for p in gain.mask.parameters] == [(), ("fast", "slow"), ()]
    assert [(p.block_type, p.name) for p in gain.ports] == [
        ("Inport", "In1"),
        ("Outport", "Out1"),
    ]
    assert by_path["Lib Doc"].mask is None
    assert by_path["Lib Doc"].link == "simulink/Model-Wide\nUtilities/DocBlock"
    assert "Two\nLines" in by_path
    assert "Group" not in by_path
    metadata = dict(lib.metadata)
    assert metadata["creator"] == "matlabdomain"
    assert metadata["last_modified_by"] == "matlabdomain"
    assert metadata["release"] == "R2026b"
    classic = dict(read_diagram(FIXTURES / "R2015b" / "mdl" / "probeLib.mdl").metadata)
    assert classic["creator"] == "matlabdomain"
    assert classic["release"] == "R2015b"
    assert classic["model_version"]
    assert "%<" not in classic["model_version"]


def test_diagram_pickles():
    diagram = read_diagram(FIXTURES / "R2026b" / "slx" / "probeModel.slx")
    assert pickle.loads(pickle.dumps(diagram)) == diagram


@pytest.mark.parametrize(
    ("version", "release"),
    [
        ("6.4", "R2006a"),
        ("6.5", "R2006b"),
        ("7.0", "R2007b"),
        ("7.9", "R2012a"),
        ("8.0", "R2012b"),
        ("8.6", "R2015b"),
        ("9.0", "R2017b"),
        ("10.0", "R2019b"),
        ("10.7", "R2023a"),
        ("23.2", "R2023b"),
        ("26.1", "R2026a"),
        ("5.0", ""),
        ("26.3", ""),
        ("", ""),
    ],
)
def test_simulink_release(version, release):
    assert simulink_release(version) == release


def test_public_names():
    assert set(mat_simulink.__all__) <= set(dir(mat_simulink))


# --- error handling and limits -------------------------------------------


def _write_zip(path, parts):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)
    return path


CORE = (
    '<cp:coreProperties xmlns:cp="urn:cp"><cp:category>{}</cp:category>'
    "</cp:coreProperties>"
)


def test_lfs_pointer(tmp_path):
    path = tmp_path / "m.slx"
    path.write_bytes(_parts.LFS_POINTER + b"\noid sha256:00\nsize 1\n")
    with pytest.raises(SimulinkFileError, match="Git LFS pointer"):
        classify(path)
    with pytest.raises(SimulinkFileError, match="Git LFS pointer"):
        read_diagram(path)


def test_not_simulink(tmp_path):
    other = tmp_path / "data.mdl"
    other.write_text('<?xml version="1.0"?>\n<config/>\n', encoding="utf-8")
    text = tmp_path / "notes.mdl"
    text.write_text("hello\n")
    for path in (other, text):
        assert classify(path) == "unknown"
        with pytest.raises(SimulinkFileError, match="is not a Simulink"):
            read_diagram(path)


def test_bad_zip(tmp_path):
    path = tmp_path / "m.slx"
    path.write_bytes(b"PK\x03\x04" + b"\0" * 64)
    with pytest.raises(SimulinkFileError, match="not a readable zip"):
        read_diagram(path)


def test_zip_without_kind(tmp_path):
    path = _write_zip(
        tmp_path / "m.slx", {"metadata/coreProperties.xml": CORE.format("x")}
    )
    assert classify(path) == "unknown"
    with pytest.raises(SimulinkFileError, match="is not a Simulink model"):
        read_diagram(path)
    bare = _write_zip(tmp_path / "bare.slx", {"other.txt": "x"})
    assert classify(bare) == "unknown"


def test_zip_kind_from_block_diagram(tmp_path):
    info = (
        '<ModelInformation Version="1.0"><Library>'
        '<P Name="Description">From the diagram</P>'
        '<System><Block BlockType="Reference" Name="L">'
        '<P Name="SourceBlock">lib/x</P></Block></System>'
        "</Library></ModelInformation>"
    )
    path = _write_zip(tmp_path / "lib.slx", {"simulink/blockdiagram.xml": info})
    assert classify(path) == "library"
    diagram = read_diagram(path)
    assert diagram.kind == "library"
    assert diagram.description == "From the diagram"
    assert diagram.library_blocks == (
        mat_simulink.LibraryBlock("L", "", None, "lib/x"),
    )
    empty = _write_zip(
        tmp_path / "empty.slx",
        {"simulink/blockdiagram.xml": "<ModelInformation/>"},
    )
    assert classify(empty) == "unknown"
    unknown_root = _write_zip(
        tmp_path / "chart.slx",
        {"simulink/blockdiagram.xml": "<ModelInformation><Chart/></ModelInformation>"},
    )
    assert classify(unknown_root) == "unknown"


def test_json_diagram_without_system_part(tmp_path):
    path = _write_zip(
        tmp_path / "m.slx",
        {
            "metadata/coreProperties.xml": CORE.format("model"),
            "simulink/blockDiagram.json": "{}",
        },
    )
    with pytest.raises(SimulinkFileError, match="has no part simulink/systems/"):
        read_diagram(path)


def test_dtd_refused(tmp_path):
    core = '<!DOCTYPE x [<!ENTITY a "aaaa">]>' + CORE.format("&a;")
    path = _write_zip(tmp_path / "m.slx", {"metadata/coreProperties.xml": core})
    with pytest.raises(SimulinkFileError, match="DTD or entity"):
        classify(path)


def test_invalid_xml(tmp_path):
    path = _write_zip(tmp_path / "m.slx", {"metadata/coreProperties.xml": "<a>"})
    with pytest.raises(SimulinkFileError, match="invalid XML"):
        read_diagram(path)


def test_zip_limits(tmp_path, monkeypatch):
    path = _write_zip(
        tmp_path / "m.slx",
        {
            "metadata/coreProperties.xml": CORE.format("model"),
            "dir/": "",
            "metadata/b.xml": "x" * 50,
            "simulink/modelWorkspace.mxarray": "y" * 500,
        },
    )
    monkeypatch.setattr(_parts, "MAX_ENTRIES", 3)
    with pytest.raises(SimulinkFileError, match="more than 3 entries"):
        read_diagram(path)
    monkeypatch.setattr(_parts, "MAX_ENTRIES", 100)
    monkeypatch.setattr(_parts, "MAX_TOTAL_BYTES", 60)
    with pytest.raises(SimulinkFileError, match="more than 60 bytes of parts"):
        read_diagram(path)
    monkeypatch.setattr(_parts, "MAX_PART_BYTES", 10)
    with pytest.raises(SimulinkFileError, match="part larger than 10 bytes"):
        read_diagram(path)
    monkeypatch.setattr(_parts, "MAX_FILE_BYTES", 10)
    with pytest.raises(SimulinkFileError, match="larger than 10 bytes"):
        read_diagram(path)


def test_unused_parts_are_not_read(tmp_path, monkeypatch):
    path = _write_zip(
        tmp_path / "m.slx",
        {
            "metadata/coreProperties.xml": CORE.format("model"),
            "simulink/systems/system_root.xml": "<System/>",
            "simulink/modelWorkspace.mxarray": "y" * 500,
        },
    )
    monkeypatch.setattr(_parts, "MAX_PART_BYTES", 100)
    assert read_diagram(path).kind == "model"


def test_corrupt_zip_io_error(tmp_path, monkeypatch):
    path = _write_zip(tmp_path / "m.slx", {"metadata/coreProperties.xml": "x"})

    def broken(f, wanted):
        raise OSError(22, "Invalid argument")

    monkeypatch.setattr(_parts, "_zip_parts", broken)
    with pytest.raises(SimulinkFileError, match="not a readable zip"):
        read_diagram(path)
    with pytest.raises(FileNotFoundError):
        _parts.zip_parts(tmp_path / "missing.slx", lambda _: True)


def test_zip_lying_size_is_a_crc_error(tmp_path, monkeypatch):
    path = _write_zip(tmp_path / "m.slx", {"metadata/coreProperties.xml": "x" * 50})
    original = _parts._read_entry

    def lying(z, info):
        info.file_size = 1
        return original(z, info)

    monkeypatch.setattr(_parts, "_read_entry", lying)
    with pytest.raises(SimulinkFileError, match="not a readable zip"):
        read_diagram(path)


def _opc(*parts):
    lines = [
        "# MathWorks OPC Text Package",
        "Model {",
        "}",
        "__MWOPC_PACKAGE_BEGIN__ R2026b",
    ]
    for name, body in parts:
        lines += [f"__MWOPC_PART_BEGIN__ {name}", body]
    return "\n".join([*lines, "__MWOPC_PACKAGE_END__", ""])


def test_opc_text_errors(tmp_path, monkeypatch):
    path = tmp_path / "m.mdl"
    path.write_text(_opc(("/metadata/x.xml BASE64", "!!!!")))
    with pytest.raises(SimulinkFileError, match="bad base64 part"):
        read_diagram(path)
    path.write_text(_opc())
    with pytest.raises(SimulinkFileError, match="no parts"):
        read_diagram(path)
    path.write_text(_opc(("/metadata/a.xml", "<a/>" * 10)))
    monkeypatch.setattr(_parts, "MAX_PART_BYTES", 10)
    with pytest.raises(SimulinkFileError, match="part larger than 10"):
        read_diagram(path)
    monkeypatch.setattr(_parts, "MAX_PART_BYTES", 100)
    monkeypatch.setattr(_parts, "MAX_TOTAL_BYTES", 5)
    with pytest.raises(SimulinkFileError, match="too many or too large"):
        read_diagram(path)


def test_opc_text_kind_from_block_diagram(tmp_path):
    path = tmp_path / "m.mdl"
    path.write_text(
        _opc(
            (
                "/simulink/blockdiagram.xml",
                "<ModelInformation><Subsystem/></ModelInformation>",
            ),
            ("/simulink/bdmxdata/x.mxarray BASE64", "!!!!"),
            ("/simulink/systems/system_root.xml", "<System/>"),
        )
    )
    assert classify(path) == "subsystem"
    assert read_diagram(path).kind == "subsystem"


CLASSIC = """\
# comment
Library {
  Name "old"
  Version 7.2
  Description "first "
  "second"
  $Weird "x"
  Created "today"
  ModelVersionFormat "1.%<AutoIncrement:5>"
  System {
    Name "old"
    Block {
      BlockType SubSystem
      Name "Masked"
      MaskType "OldType"
      MaskDescription "Old description"
      MaskHelp "Old help"
      MaskPromptString "Gain|Mode|Extra"
      MaskStyleString "edit,popup(a|b)"
      MaskVariables "k=@1;mode=&2;extra=@3;"
      MaskValueString "2|a"
      MaskVisibilityString "on,off"
    }
  }
}
"""


def test_classic_old_mask_parameters(tmp_path):
    path = tmp_path / "old.mdl"
    path.write_text(CLASSIC)
    assert classify(path) == "library"
    diagram = read_diagram(path)
    assert diagram.description == "first second"
    assert diagram.release == "R2008b"
    assert dict(diagram.metadata)["model_version"] == "1.5"
    (block,) = diagram.library_blocks
    assert block.mask == mat_simulink.Mask(
        "OldType",
        "Old description",
        "Old help",
        "",
        (
            mat_simulink.MaskParameter("k", "Gain", "edit", "2"),
            mat_simulink.MaskParameter(
                "mode", "Mode", "popup", "a", ("a", "b"), visible=False
            ),
            mat_simulink.MaskParameter("extra", "Extra", "edit", ""),
        ),
    )


def test_hidden_mask_parameters(tmp_path):
    element = _nodes.parse_xml(
        b'<Mask><Type>T</Type><MaskParameter Name="a" Type="edit"/>'
        b'<MaskParameter Name="b" Type="edit" Visible="off"/></Mask>',
        "test",
    )
    mask = _model.block_mask(_nodes.Node("Block", children=[element]))
    assert mask is not None
    assert [(p.name, p.visible) for p in mask.parameters] == [("a", True), ("b", False)]
    path = tmp_path / "lib.mdl"
    path.write_text(
        "Library {\n  System {\n    Block {\n      BlockType SubSystem\n"
        '      Name "M"\n      Object {\n        $ClassName "Simulink.Mask"\n'
        '        Type "T"\n        Array {\n          PropName "Parameters"\n'
        '          Object {\n            Name "a"\n          }\n'
        '          Object {\n            Name "b"\n            Visible "off"\n'
        "          }\n        }\n      }\n    }\n  }\n}\n"
    )
    (block,) = read_diagram(path).library_blocks
    assert block.mask is not None
    assert [(p.name, p.visible) for p in block.mask.parameters] == [
        ("a", True),
        ("b", False),
    ]


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("Model {\n}\n}\n", "unmatched"),
        ("Model {\n  = bad\n}\n", "unreadable line 2"),
        ('Model {\n  Name "x"\n', "ends inside"),
    ],
)
def test_classic_errors(tmp_path, text, message):
    path = tmp_path / "x.mdl"
    path.write_text(text)
    with pytest.raises(SimulinkFileError, match=message):
        read_diagram(path)


def test_sublibrary_blocks(tmp_path):
    blocks = "".join(
        f'    Block {{\n      BlockType SubSystem\n      Name "{name}"\n'
        f"      OpenFcn {opens}\n{inner}    }}\n"
        for name, opens, inner in [
            ("Plain", '"libA"', ""),
            ("Call", "\"open_system('libB');\"", "      System {\n      }\n"),
            ("Quoted", '"open_system(libC)"', ""),
            (
                "Busy",
                '"libD"',
                '      System {\n        Block {\n          Name "x"\n'
                "        }\n      }\n",
            ),
            ("Code", '"disp(1)"', ""),
        ]
    )
    path = tmp_path / "lib.mdl"
    path.write_text(f"Library {{\n  System {{\n{blocks}  }}\n}}\n")
    found = {b.path: b.opens for b in read_diagram(path).library_blocks}
    # a subsystem with contents is entered; "disp(1)" opens nothing
    assert found == {"Plain": "libA", "Call": "libB", "Quoted": "libC"}


def test_classic_object_mask_skips_other_objects(tmp_path):
    path = tmp_path / "lib.mdl"
    path.write_text(
        "Library {\n  System {\n    Block {\n      BlockType SubSystem\n"
        '      Name "M"\n      Object {\n        $ClassName "Simulink.Other"\n'
        '      }\n      Object {\n        $ClassName "Simulink.Mask"\n'
        '        Type "T"\n        Array {\n          PropName "Other"\n'
        "        }\n      }\n    }\n  }\n}\n"
    )
    (block,) = read_diagram(path).library_blocks
    assert block.mask == mat_simulink.Mask("T", "", "")


def test_classic_without_root_section(tmp_path, monkeypatch):
    path = tmp_path / "x.mdl"
    path.write_text("Model {\n}\n")
    monkeypatch.setattr(_model, "parse_mdl", lambda _: [_nodes.Node("MatData")])
    with pytest.raises(SimulinkFileError, match="no Model, Library or Subsystem"):
        read_diagram(path)


def test_classic_depth_limit(monkeypatch):
    monkeypatch.setattr(_nodes, "MAX_DEPTH", 2)
    with pytest.raises(SimulinkFileError, match="nested deeper than 2"):
        _nodes.parse_mdl("A {\nB {\nC {\n}\n}\n}\n")
    with pytest.raises(SimulinkFileError, match="nested deeper than 2"):
        _nodes.parse_xml(b"<a><b><c><d/></c></b></a>", "x")


@pytest.mark.parametrize(
    "data",
    [
        b'<?xml version="1.0" encoding="utf-O"?><a/>',  # unknown codec (fuzzing)
        b'<?xml version="1.0" encoding="rot13"?><a/>',  # not a text codec
        b'<?xml version="1.0" encoding="utf-7"?><a/>',  # a multi-byte codec
        b'<?xml version="1.0" encoding="idna"?><a/>',  # a codec without "replace"
    ],
)
def test_xml_with_a_bad_encoding_declaration(data):
    with pytest.raises(SimulinkFileError, match="invalid XML in x"):
        _nodes.parse_xml(data, "x")


# Every encoding the XML parser accepts: ASCII-compatible ones (including a
# byte-order mark) and UTF-16. UTF-32 and EBCDIC are invalid XML for it.
_XML_ENCODINGS = [
    ("utf-8", "utf-8", b""),
    ("utf-8", None, b""),
    ("utf-8", "utf-8", codecs.BOM_UTF8),
    ("windows-1252", "windows-1252", b""),
    ("latin-1", "iso-8859-1", b""),
    ("shift_jis", None, b""),
    ("utf-16-le", "utf-16", codecs.BOM_UTF16_LE),
    ("utf-16-be", "utf-16", codecs.BOM_UTF16_BE),
    ("utf-16-le", None, codecs.BOM_UTF16_LE),
    ("utf-16-be", None, codecs.BOM_UTF16_BE),
    ("utf-16-le", "utf-16", b""),
    ("utf-16-be", "utf-16", b""),
    ("utf-16-le", None, b""),
    ("utf-16-be", None, b""),
]


def _xml_document(encoding, declared, bom, body):
    declaration = f'<?xml version="1.0" encoding="{declared}"?>' if declared else ""
    return bom + (declaration + body).encode(encoding)


@pytest.mark.parametrize(("encoding", "declared", "bom"), _XML_ENCODINGS)
@pytest.mark.parametrize(
    "dtd",
    [
        '<!DOCTYPE a [<!ENTITY b "c">]><a>&b;</a>',
        "<!DOCTYPE a><a/>",
        '<a><!ENTITY b "c"></a>',
    ],
)
def test_a_dtd_is_refused_in_every_encoding(encoding, declared, bom, dtd):
    data = _xml_document(encoding, declared, bom, dtd)
    with pytest.raises(SimulinkFileError, match="DTD or entity declaration"):
        _nodes.parse_xml(data, "x")


@pytest.mark.parametrize(("encoding", "declared", "bom"), _XML_ENCODINGS)
def test_the_same_document_without_a_dtd_parses_in_every_encoding(
    encoding, declared, bom
):
    body = '<a k="v"><!-- c --><P Name="n">t</P><b/></a>'
    node = _nodes.parse_xml(_xml_document(encoding, declared, bom, body), "x")
    assert node.tag == "a"
    assert node.attrs == {"k": "v"}
    assert node.params == {"n": ["t"]}
    assert [c.tag for c in node.children] == ["b"]


def test_classic_without_system(tmp_path):
    path = tmp_path / "x.mdl"
    path.write_text('Model {\n  Name "x"\n}\n')
    diagram = read_diagram(path)
    assert diagram.ports == ()
    assert diagram.release == ""


PORTS_OUT_OF_ORDER = """\
Model {
  Name "ports"
  System {
    Block {
      BlockType Outport
      Name "y"
    }
    Block {
      BlockType EnablePort
      Name "Enable"
    }
    Block {
      BlockType Inport
      Name "second"
      Port "2"
    }
    Block {
      BlockType TriggerPort
      Name "Trigger"
    }
    Block {
      BlockType Inport
      Name "first"
    }
  }
}
"""


def test_ports_sorted_by_number_with_control_ports(tmp_path):
    # Spec 4.4: sorted by port number; Enable/Trigger/Action ports listed by
    # type, without a data type.
    path = tmp_path / "ports.mdl"
    path.write_text(PORTS_OUT_OF_ORDER)
    ports = read_diagram(path).ports
    assert [(p.block_type, p.number, p.name) for p in ports] == [
        ("Inport", "1", "first"),
        ("Inport", "2", "second"),
        ("Outport", "1", "y"),
        ("EnablePort", "", "Enable"),
        ("TriggerPort", "", "Trigger"),
    ]
    assert ports[3].data_type == ports[3].dimensions == ""


def test_decode_mdl():
    assert _nodes.decode_mdl(
        'A {\n  SavedCharacterEncoding "utf-8"\n  N "Gr\u00f6\u00dfe"\n}'.encode()
    ).endswith('e"\n}')
    cp1252 = 'SavedCharacterEncoding "windows-1252"\nN "Gr\u00f6\u00dfe"'.encode(
        "cp1252"
    )
    assert "Gr\u00f6\u00dfe" in _nodes.decode_mdl(cp1252)
    unknown = b'SavedCharacterEncoding "no-such-codec"\nN "x"'
    assert _nodes.decode_mdl(unknown).endswith('"x"')
    invalid = 'SavedCharacterEncoding "utf-8"\nN "\xe9"'.encode("latin-1")
    assert _nodes.decode_mdl(invalid).endswith('"\xe9"')


def test_decode_mdl_limit(monkeypatch):
    monkeypatch.setattr(_nodes, "MAX_PART_BYTES", 1)
    with pytest.raises(SimulinkFileError, match="larger than 4 bytes"):
        _nodes.decode_mdl(b"12345")


def test_unescape():
    assert _nodes.unescape(r"a\nb\t\"c\\d\q") == 'a\nb\t"c\\d\\q'


def test_classic_unknown_head(tmp_path, monkeypatch):
    path = tmp_path / "x.mdl"
    path.write_text("Model {\n}\n")
    monkeypatch.setattr(_model, "read_head", lambda _: b"Model {")
    monkeypatch.setattr(_model, "sniff", lambda *_: "classic")
    assert classify(path) == "model"
    monkeypatch.setattr(_model, "read_head", lambda _: b"nothing")
    assert classify(path) == "unknown"


def test_nodes():
    node = _nodes.Node("Block", {"Name": "a"}, {"Port": ["1", "2"]})
    assert node.param("Name") == "a"
    assert node.param("Port") == "2"
    assert node.param("Missing", "d") == "d"
    assert node.find("System") is None
    assert node.child_text("Type") == ""
    assert node.has("Port")
    assert not node.has("Unit")
    parsed = _nodes.parse_xml(
        b'<m:a xmlns:m="urn:x"><Array><Cell>c</Cell></Array></m:a>', "x"
    )
    assert parsed.tag == "a"
    assert parsed.children[0].cells() == ["c"]
