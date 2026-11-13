"""Where the lines the documenters generate around help text are: the
directive header and its options, ``Bases:``, the member headings. They are
at the code file of the object and the line of its declaration (line 1 of a
file without one); an object without a file is at its auto directive. Help
text keeps ``<file>:docstring of <reference>``.
"""

import os
import re
import shutil
from pathlib import Path
from typing import Any, cast

import pytest
from docutils import nodes
from sphinx import addnodes
from sphinx.util import console

strip_escape_sequences = cast(Any, console).strip_escape_sequences

SLX = Path(__file__).parent / "simulink" / "fixtures" / "R2026b" / "slx"
CONF = (
    'extensions = ["sphinxcontrib.matlab"]\n'
    'matlab_src_code_project_root = "src"\n'
    'matlab_src_sidecar_suffixes = [".rst"]\n'
    'exclude_patterns = ["inc.txt", "_build"]\n'
    "nitpicky = True\n"
)
# the classdef on line 3; Base is not documented, Missing does not exist
SUB = """\
% a comment

classdef Sub < Base & Missing
% SUB help
properties
    % P help
    p = 1
end
methods
    function m(obj)
    % M help
    end
end
events
    Ev % EV help
end
end
"""
# a class folder: the classdef on line 4, a method in its own file
CF = (
    "% lead\n%\n\nclassdef Cf < Missing\n% CF help\nmethods\n"
    "    r = meth(obj)\nend\nend\n"
)
METH = "\nfunction r = meth(obj)\n% METH help\nr = 1;\nend\n"
COLOR = "classdef Color\n% COLOR help\nenumeration\n    % RED help\n    Red\nend\nend\n"
FUNCTION = "function y = {0}(x)\n% {0} help\ny = x;\nend\n"
SOURCES = {
    "conf.py": CONF,
    "src/Base.m": "classdef Base\n% BASE help\nend\n",
    "src/Sub.m": SUB,
    "src/@Cf/Cf.m": CF,
    "src/@Cf/meth.m": METH,
    "src/Color.m": COLOR,
    "src/+pk/g.m": FUNCTION.format("g"),
    "src/@K/K.m": "classdef K\n% K help\nend\n",
    "src/s.m": "% S help\nx = 1;\n",
}
AUTOCLASS = ".. mat:autoclass:: {}\n   :show-inheritance:\n{}"
AUTOCLASSES = AUTOCLASS.format("Sub", "") + "\n" + AUTOCLASS.format("Cf", "")
# (file, line, target) of the warnings of AUTOCLASSES: each at the classdef
BASES = {
    ("src/Sub.m", 3, "Base.m"),
    ("src/Sub.m", 3, "Missing"),
    ("src/@Cf/Cf.m", 4, "Missing"),
}


def as_help(text):
    """``text`` as the help lines of a MATLAB file."""
    return "".join(f"% {line}\n" if line else "%\n" for line in text.split("\n"))


def places(directives):
    """Return the files of each place where ``directives`` can be written."""
    return {
        "page": {"p.rst": "P\n=\n\nText.\n\n" + directives},
        "included": {
            "p.rst": "P\n=\n\n.. include:: inc.txt\n",
            "inc.txt": "Included.\n\n" + directives,
        },
        "sidecar": {
            "p.rst": "P\n=\n\n.. mat:autosidecar:: guide.rst\n",
            "src/guide.rst": "Guide\n=====\n\nText.\n\n" + directives,
        },
        "help": {
            "p.rst": "P\n=\n\n.. mat:autofunction:: f\n",
            "src/f.m": "function f\n% F help\n%\n" + as_help(directives) + "end\n",
        },
    }


PLACES = places(AUTOCLASSES)
WARNING_LINE = re.compile(r"^(.*):(\d+): (?:WARNING|ERROR): (.*)$")


def write(root, files):
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")


def build(make_app, root, files, parallel=0):
    pages = sorted(name[:-4] for name in files if name.endswith(".rst"))
    pages = [page for page in pages if "/" not in page]
    toctree = "".join(f"   {page}\n" for page in pages)
    write(root, {**SOURCES, "index.rst": f"Index\n=====\n\n.. toctree::\n\n{toctree}"})
    write(root, files)
    app = make_app(srcdir=root, freshenv=True, parallel=parallel)
    app.build()
    return app


def relative(where, root):
    """``where`` (a file, or ``<file>:docstring of <reference>``) relative to
    ``root``, with ``/``.
    """
    file, found, ref = where.partition(":docstring of ")
    return os.path.relpath(file, root).replace(os.sep, "/") + found + ref


def located(app, root):
    """``{(file, line, message)}`` of the warnings of ``app``."""
    found = set()
    for line in strip_escape_sequences(app.warning.getvalue()).splitlines():
        match = WARNING_LINE.match(line)
        assert match is not None, line
        where, number, message = match.groups()
        found.add((relative(where, root), int(number), message))
    return found


def not_found(found):
    """``{(file, line, target)}`` of the "reference target not found" warnings."""
    pattern = re.compile(r"reference target not found: (\S+) \[ref\.\w+\]$")
    return {
        (file, line, match[1])
        for file, line, message in found
        if (match := pattern.search(message))
    }


def where(node, root):
    """``(file, line)`` of ``node``, the file relative to ``root``."""
    return relative(node.source, root), node.line


def signatures(app, docname, root):
    """``{display name: (file, line)}`` of the descriptions in ``docname``."""
    doctree = app.env.get_doctree(docname)
    return {
        sig.get("fullname"): where(sig, root)
        for sig in doctree.findall(addnodes.desc_signature)
    }


@pytest.mark.parametrize("place", list(PLACES))
def test_bases_warning_names_the_classdef_line(make_app, tmp_path, place):
    app = build(make_app, tmp_path, PLACES[place])
    found = located(app, tmp_path)
    assert not_found(found) == BASES
    assert {(file, line) for file, line, _ in found} == {
        (file, line) for file, line, _ in BASES
    }


def test_member_lines_name_the_member_declaration(make_app, tmp_path):
    page = "P\n=\n\n" + "".join(
        f".. mat:autoclass:: {name}\n   :members:\n   :show-inheritance:\n\n"
        for name in ("Sub", "Cf", "Color")
    )
    # a member documented on its own
    alone = "Q\n=\n\n.. mat:autoevent:: Sub.Ev\n   :no-index:\n"
    app = build(make_app, tmp_path, {"p.rst": page, "q.rst": alone})
    assert signatures(app, "q", tmp_path) == {"Sub.Ev": ("src/Sub.m", 15)}
    assert signatures(app, "p", tmp_path) == {
        "Sub": ("src/Sub.m", 3),
        "Sub.p": ("src/Sub.m", 7),
        "Sub.m": ("src/Sub.m", 10),
        "Sub.Ev": ("src/Sub.m", 15),
        "Cf": ("src/@Cf/Cf.m", 4),
        # a method in its own file of the class folder
        "Cf.meth": ("src/@Cf/meth.m", 2),
        "Color": ("src/Color.m", 1),
        "Color.Red": ("src/Color.m", 5),
    }
    doctree = app.env.get_doctree("p")
    # the headings of the member sections and the Bases line: the class
    headings = [
        (node.astext(), *where(node, tmp_path)) for node in doctree.findall(nodes.term)
    ]
    assert headings == [
        ("Property Summary", "src/Sub.m", 3),
        ("Method Summary", "src/Sub.m", 3),
        ("Event Summary", "src/Sub.m", 3),
        ("Method Summary", "src/@Cf/Cf.m", 4),
        ("Enumeration Values", "src/Color.m", 1),
    ]
    bases = [
        where(node, tmp_path)
        for node in doctree.findall(nodes.paragraph)
        if node.astext().startswith("Bases:")
    ]
    assert bases == [("src/Sub.m", 3), ("src/@Cf/Cf.m", 4)]
    # help text keeps its own form and lines
    helps = {
        node.astext(): where(node, tmp_path)
        for node in doctree.findall(nodes.paragraph)
        if node.astext().endswith("help")
    }
    assert helps["P help"] == ("src/Sub.m:docstring of Sub.m.p", 6)
    assert helps["METH help"][1] == 3


def test_folder_lines_name_the_auto_directive(make_app, tmp_path):
    files = {
        "p.rst": "P\n=\n\nText.\n\n.. mat:autofolder:: @K\n\n"
        ".. mat:autofolder:: +pk\n   :members:\n\n.. mat:autofunction:: f\n",
        # an auto directive in help text: at its line in the code file
        "src/f.m": "function f\n% F help\n%\n% .. mat:autofolder:: +pk\n"
        "%    :no-index:\nend\n",
    }
    app = build(make_app, tmp_path, files)
    # the class folder warning of the generated folder description
    assert {(file, line) for file, line, _ in located(app, tmp_path)} == {("p.rst", 6)}
    doctree = app.env.get_doctree("p")
    folders = [
        where(sig, tmp_path)
        for sig in doctree.findall(addnodes.desc_signature)
        if sig.astext() in ("@K/", "namespace pk")
    ]
    assert folders == [("p.rst", 6), ("p.rst", 8), ("src/f.m", 4)]
    # a member of the folder has a file
    assert signatures(app, "p", tmp_path)["pk.g"] == ("src/+pk/g.m", 1)


LIBRARY = """\
Library {
  Name "lib"
  System {
    Name "lib"
    Block {
      BlockType SubSystem
      Name "Blk"
      Description "Block text."
      MaskType "T"
      MaskDescription "Mask :mat:func:`noMask` and `data <data.txt>`__."
      System {
      }
    }
  }
}
"""


def test_simulink_lines_name_line_1_of_the_file(make_app, tmp_path):
    files = {
        "src/lib.mdl": LIBRARY,
        "src/data.txt": "Data.\n",
        "p.rst": "P\n=\n\n.. mat:autosimulink_library_block:: lib.mdl/Blk\n\n"
        ".. mat:autosimulink_model:: probeModel\n",
    }
    (tmp_path / "src").mkdir()
    shutil.copyfile(SLX / "probeModel.slx", tmp_path / "src" / "probeModel.slx")
    app = build(make_app, tmp_path, files)
    assert signatures(app, "p", tmp_path) == {
        "lib/Blk": ("src/lib.mdl", 1),
        "probeModel": ("src/probeModel.slx", 1),
    }
    doctree = app.env.get_doctree("p")
    fields = {
        node.astext(): where(node, tmp_path) for node in doctree.findall(nodes.field)
    }
    assert fields["Mask type\n\nT"] == ("src/lib.mdl", 1)
    rubrics = [where(node, tmp_path) for node in doctree.findall(nodes.rubric)]
    assert rubrics
    assert set(rubrics) == {("src/probeModel.slx", 1)}
    # The mask description is text of the file: help text, whose relative
    # paths are relative to the code folder.
    assert not_found(located(app, tmp_path)) == {
        ("src/lib.mdl:docstring of lib.mdl/Blk", 1, "noMask")
    }
    page = (Path(app.outdir) / "p.html").read_text(encoding="utf-8")
    assert re.search(r'href="_downloads/[0-9a-f]+/data\.txt"', page)


def test_no_node_is_in_a_file_that_does_not_exist(make_app, tmp_path):
    files = {
        "p.rst": "P\n=\n\n.. include:: inc.txt\n\n"
        ".. mat:autofolder:: +pk\n   :members:\n\n"
        ".. mat:autoscript:: s\n\n.. mat:autofunction:: f\n\n"
        ".. mat:autosimulink_model:: probeModel\n\n"
        ".. mat:autosidecar:: guide.rst\n",
        "inc.txt": "Included.\n\n.. mat:autoclass:: Sub\n   :members:\n"
        "   :show-inheritance:\n",
        "src/guide.rst": "Guide\n=====\n\nText.\n\n.. mat:autoclass:: Cf\n"
        "   :members:\n\n.. mat:autoclass:: Color\n   :members:\n",
        "src/f.m": FUNCTION.format("f"),
    }
    (tmp_path / "src").mkdir()
    shutil.copyfile(SLX / "probeModel.slx", tmp_path / "src" / "probeModel.slx")
    app = build(make_app, tmp_path, files)
    sources = {
        node.source
        for docname in ("index", "p")
        for node in app.env.get_doctree(docname).findall(nodes.Element)
        if node.source
    }
    assert not [source for source in sources if "<autodoc>" in source]
    files_named = {source.partition(":docstring of ")[0] for source in sources}
    assert [file for file in files_named if not os.path.isfile(file)] == []
    # every kind of object was generated
    assert {relative(file, tmp_path) for file in files_named} >= {
        "p.rst",
        "inc.txt",
        "src/guide.rst",
        "src/Sub.m",
        "src/@Cf/Cf.m",
        "src/@Cf/meth.m",
        "src/Color.m",
        "src/+pk/g.m",
        "src/s.m",
        "src/f.m",
        "src/probeModel.slx",
    }


def test_parallel_build_gives_the_same_warnings(make_app, tmp_path):
    # each place on a page of its own, and pages for two chunks
    unindexed = AUTOCLASS.format("Sub", "   :no-index:\n") + "\n"
    unindexed += AUTOCLASS.format("Cf", "   :no-index:\n")
    files = {}
    for place, written in places(unindexed).items():
        for name, text in written.items():
            files[f"{place}.rst" if name == "p.rst" else name] = text
    files.update({f"z{i}.rst": f"Z{i}\n==\n\nText.\n" for i in range(6)})
    found = {}
    for parallel in (0, 2):
        app = build(make_app, tmp_path / str(parallel), files, parallel)
        app.cleanup()  # else the next app warns that it registers again
        text = strip_escape_sequences(app.warning.getvalue())
        found[parallel] = sorted(
            line.replace(str(tmp_path / str(parallel)), "<SRC>")
            for line in text.splitlines()
        )
    assert found[0] == found[2]
    assert {line.split(": WARNING")[0] for line in found[0]} == {
        "<SRC>/src/Sub.m:3",
        "<SRC>/src/@Cf/Cf.m:4",
    }
