"""A corrupt or huge ``.mlapp`` file is one ``mat.parse_error``, not a stall.

The ``.mlapp`` reader has the guards of ``mat_container``: size limits, no
DTD or entity declaration, a nesting limit. The limits are lowered here
instead of writing large files.
"""

import zipfile

import pytest

from sphinxcontrib import mat_container, mat_types
from sphinxcontrib.mat_handlers import handler_by_extension

CORE = (
    '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/'
    'metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">'
    "<dc:description>Summary of app</dc:description></cp:coreProperties>"
)
META = (
    '<metadata xmlns="http://schemas.mathworks.com/appDesigner/app/2017/'
    'appMetadata"><description>Description of app</description></metadata>'
)


def make_app(tmp_path, core=CORE, meta=META, extra=()):
    path = tmp_path / "App.mlapp"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("metadata/appMetadata.xml", meta)
        z.writestr("metadata/coreProperties.xml", core)
        for name in extra:
            z.writestr(name, "x")
    return path


def parse(path):
    """Parse as a ``mat:autoapplication`` page does: a failure is a placeholder."""
    handler = handler_by_extension(str(path))
    return mat_types._parse(handler, str(path), "App", "", "application")


def warnings_of(obj):
    return [(kind, text) for kind, text, _ in obj.source_warnings]


def test_a_valid_app_is_read(tmp_path):
    obj = parse(make_app(tmp_path))
    assert not obj.source_warnings
    assert obj.docstring == "Summary of app\n\nDescription of app"


def test_a_member_over_the_limit_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(mat_container, "MAX_MEMBER_BYTES", len(META) + 10)
    obj = parse(make_app(tmp_path, core=CORE + " " * 100))
    assert warnings_of(obj) == [
        (
            "parse_error",
            "cannot be parsed (ContainerFileError: has a member larger than "
            f"{len(META) + 10} bytes: metadata/coreProperties.xml.); it is documented "
            "without content.",
        )
    ]
    assert obj.docstring == ""


def test_a_file_over_the_limit_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(mat_container, "MAX_FILE_BYTES", 100)
    obj = parse(make_app(tmp_path))
    assert warnings_of(obj)[0][1].startswith(
        "cannot be parsed (ContainerFileError: is larger than 100 bytes.)"
    )


def test_too_many_entries_are_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(mat_container, "MAX_ENTRIES", 2)
    obj = parse(make_app(tmp_path, extra=("a.txt",)))
    assert warnings_of(obj)[0][1].startswith(
        "cannot be parsed (ContainerFileError: has more than 2 entries.)"
    )


@pytest.mark.parametrize(
    "declaration", ["<!DOCTYPE x>", '<!DOCTYPE x [<!ENTITY a "b">]>']
)
def test_a_dtd_is_refused(tmp_path, declaration):
    obj = parse(make_app(tmp_path, core=declaration + CORE))
    assert warnings_of(obj) == [
        (
            "parse_error",
            "cannot be parsed (ContainerFileError: has a DTD or entity declaration in "
            "metadata/coreProperties.xml.); it is documented without content.",
        )
    ]


@pytest.mark.parametrize(
    ("meta", "reason"),
    [
        ("<a>", "no element found"),
        # an encoding the XML parser does not know, and one that is no text encoding
        ('<?xml version="1.0" encoding="no-such"?><a/>', "unknown encoding"),
        ('<?xml version="1.0" encoding="utf-7"?><a/>', ""),
    ],
    ids=["not well-formed", "unknown encoding", "multi-byte encoding"],
)
def test_invalid_xml_is_refused(tmp_path, meta, reason):
    obj = parse(make_app(tmp_path, meta=meta))
    ((kind, text),) = warnings_of(obj)
    assert kind == "parse_error"
    assert text.startswith(
        "cannot be parsed (ContainerFileError: has invalid XML in "
        "metadata/appMetadata.xml ("
    )
    assert reason in text


def test_deep_nesting_is_refused(tmp_path):
    depth = mat_container.MAX_DEPTH + 2
    obj = parse(make_app(tmp_path, meta="<a>" * depth + "</a>" * depth))
    assert warnings_of(obj)[0][1].startswith(
        "cannot be parsed (ContainerFileError: is nested deeper than "
        f"{mat_container.MAX_DEPTH} in metadata/appMetadata.xml.)"
    )
