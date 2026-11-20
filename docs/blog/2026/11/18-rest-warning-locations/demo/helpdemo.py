"""A toy ``help`` directive: render the comment help of a MATLAB file as reST.

The lines it hands to docutils say where they came from. Two options show
what changes the place a warning names:

``:lines: docstring`` numbers the lines within the help (Python autodoc's
choice); ``:lines: file`` uses the line in the code file.

``:no-switch:`` parses without ``switch_source_input``.
"""

from pathlib import Path
from typing import ClassVar

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.statemachine import StringList
from sphinx.util.docutils import SphinxDirective, switch_source_input


class Help(SphinxDirective):
    """Parse the ``%`` comments of the MATLAB file given as the argument."""

    required_arguments = 1
    option_spec: ClassVar = {
        "lines": lambda arg: directives.choice(arg, ("docstring", "file")),
        "no-switch": directives.flag,
    }

    def run(self):
        """Give each help line its own (source, offset) item, then parse."""
        rel, path = self.env.relfn2path(self.arguments[0], self.env.docname)
        source = f"{path}:docstring of {Path(rel).stem}"
        content = StringList()
        index = 0
        for number, line in enumerate(Path(path).read_text().splitlines()):
            text = line.lstrip()
            if not text.startswith("%"):
                continue
            # StringList.append(line, source, offset): offset is zero-based.
            offset = number if self.options.get("lines") == "file" else index
            content.append(text[1:].removeprefix(" "), source, offset)
            index += 1

        node = nodes.container()
        if "no-switch" in self.options:
            self.state.nested_parse(content, 0, node)
        else:
            with switch_source_input(self.state, content):
                self.state.nested_parse(content, 0, node)
        return node.children


def setup(app):
    """Register the directive."""
    app.add_directive("help", Help)
    return {"parallel_read_safe": True}
