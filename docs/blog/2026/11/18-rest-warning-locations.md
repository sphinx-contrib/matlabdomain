# How a reST warning finds its file and line

You write a docstring with a stray `*`, and Sphinx says
`mod.py:docstring of mod.f:3: WARNING: Inline emphasis start-string without end-string.`
How does it know `mod.py`? Why line 3, and line 3 of what? And how do you
make a warning about text taken from a code file point at the real line
in that file?

This post follows one warning from the docutils parser to Sphinx's
output. Versions: docutils 0.22.4, Sphinx 9.2.0, myst-parser 5.2.0.

## The short version

```{mermaid}
flowchart TD
    A["StringList<br/>each line: (source, offset)"] --> B["docutils state machine<br/>parses, counts absolute line numbers"]
    B -->|"reporter.warning(msg, line=N)"| C["Reporter.system_message"]
    C -->|"get_source_and_line(N)"| D["StringList.info(offset)<br/>→ (source, offset + 1)"]
    D --> E["system_message node<br/>source, line"]
    E -->|"astext(): 'source:line: (LEVEL/n) msg'"| F["Sphinx WarningStream<br/>regex back into location"]
    F --> G["sphinx.util.logging<br/>'file:line: WARNING: …'"]
    B -->|"directives and roles stamp nodes"| H["node.source, node.line"]
    H -->|"later: logger.warning(location=node)"| G
```

1. Every line docutils parses carries its own origin.
2. A message gives an *absolute* line number, and the reporter maps it back
   to that origin.
3. The reporter's mapping is bound once, so text that comes from somewhere
   else has to switch it: `switch_source_input`.

## Lines carry their origin: `StringList`

docutils doesn't parse a string. It parses a
`docutils.statemachine.StringList`: a list of lines plus a parallel list
of `items`, one `(source, offset)` per line, with a zero-based offset.

```python
from docutils.statemachine import StringList

lines = StringList(["Title", "=====", "", "Text *here."], source="page.rst")
lines.info(3)  # ('page.rst', 3): the 4th line of page.rst
```

Sphinx reads a page as one `StringList` whose source is the page's path.
`.. include::` doesn't parse the included file separately. It *splices*
the included lines into the same list (`StateMachine.insert_input`), each
with its own item `(included path, n)`, plus two padding lines. That is
why a warning inside an included file names that file.

The items don't have to be contiguous, and they don't have to name the
file being built. A directive that generates text can claim any origin
for any line. autodoc does exactly that:
`self.add_line(line, source, offset)`.

## Two ways a message is located

### 1. Messages raised while parsing

"Inline emphasis start-string without end-string", "Unknown interpreted
text role", "Unknown directive type", "Explicit markup ends without a
blank line": the parser calls

```python
self.reporter.warning("...", line=lineno)  # lineno: absolute line number
```

`Reporter.system_message` (`docutils/utils/__init__.py`) then fills in the
location:

```python
if "source" not in attributes:
    # 'line' is absolute line number
    source, line = self.get_source_and_line(attributes.get("line"))
```

`get_source_and_line` is `StateMachine.get_source_and_line`
(`docutils/statemachine.py`):

```python
offset = lineno - self.input_offset - 1
src, srcoffset = self.input_lines.info(offset)
srcline = srcoffset + 1
```

The absolute line becomes an index into the `StringList`, and the index
becomes the item's `(source, offset + 1)`. The parser never knows which
file a line came from. Only the list does.

### 2. Messages raised later, from nodes

Some warnings come after parsing: an unresolved reference, an image
that can't be read, "Unknown target name". They use the location stored
on a node while it was parsed:

- directives: `sphinx.util.nodes.set_source_info(directive, node)` →
  `directive.state_machine.get_source_and_line(directive.lineno)`;
- roles: `set_role_source_info(inliner, lineno, node)` →
  `inliner.reporter.get_source_and_line(lineno)`.

Later, `logger.warning(..., location=node)` goes through
`sphinx.util.logging.get_node_location`, which takes the
`(source, line)` of the node or its nearest ancestor that has one.

## From docutils to Sphinx's output

Sphinx gives each document a `LoggingReporter` whose stream is a
`WarningStream`. docutils writes each message as text,
`"<source>:<line>: (WARNING/2) <message>"`. `WarningStream.write`
parses that text back with a regular expression (`report_re` in
`sphinx/util/docutils.py`) and hands the pieces to Sphinx's logger with
`type="docutils"`. So a docutils `ERROR` is still a Sphinx warning: it
prints as `ERROR:`, and `-W` fails on it.

Sphinx's logger takes a location in three forms: a `(docname, line)`
tuple (turned into a path), a node, or a string such as `"file:line"`,
printed as it is. With `show_warning_types`, the `[type.subtype]` suffix
is added.

## The catch: the reporter is bound once

Here is the part that bites extension authors. In
`docutils/parsers/rst/states.py`, `RSTState.runtime_init` does:

```python
# enable the reporter to determine source and source-line
if not hasattr(self.reporter, "get_source_and_line"):
    self.reporter.get_source_and_line = self.state_machine.get_source_and_line
```

*If it doesn't have one yet.* The first state machine, the one parsing the
page, wins. A directive that parses its own `StringList` with
`state.nested_parse` gets a nested state machine that counts lines within
*that* list, but the reporter still looks them up in the *page's* list.
The result is the page's file at a line that means nothing there.

Sphinx's answer is `sphinx.util.docutils.switch_source_input`:

```python
@contextmanager
def switch_source_input(state, content):
    gsal = state.memo.reporter.get_source_and_line
    state_machine = StateMachine([], None)
    state_machine.input_lines = content
    state.memo.reporter.get_source_and_line = state_machine.get_source_and_line
    yield
    state.memo.reporter.get_source_and_line = gsal  # restored in a finally
```

While the context is open, the reporter maps through `content`. It is
the same object that `include` splices into, so includes inside generated
text map correctly too. autodoc parses all of its generated text inside
it.

## Docstring line or file line?

Python's autodoc builds its list as
`StringList(docstring_lines, source="<file>:docstring of <name>")`. The
offsets count from 0 *within the docstring*. So `mod.py:docstring of
mod.f:3` means the third line of the docstring, not line 3 of `mod.py`.

Nothing forces that choice. The offset is just an integer per line. Give
each line its line in the code file and the same message points at the
real line. That is what
[sphinxcontrib-matlabdomain](https://github.com/sphinx-contrib/matlabdomain)
does for MATLAB help comments.

An offset added to the whole block is enough only when the parsed text is
an unchanged, contiguous copy of the file. Docstrings often aren't:
`autodoc-process-docstring` handlers such as napoleon add, drop and
rewrite lines. So the useful unit is a line-by-line map, which is what
`StringList` items already are.

## Run it

The demo in this post's folder is a toy `help` directive. It renders the
`%` comments of a MATLAB file as reST:

```{literalinclude} 18-rest-warning-locations/demo/helpdemo.py
:language: python
:pyobject: Help.run
```

`shape.m` has a stray `*` on line 4 and an unknown role on line 6:

```{literalinclude} 18-rest-warning-locations/demo/shape.m
:language: matlab
:linenos:
```

The page uses the directive three times: help-relative lines, file lines,
and file lines without `switch_source_input`. From the `docs/` folder:

```console
$ uv run --group docs python blog/2026/11/18-rest-warning-locations/demo/run.py
shape.m:docstring of shape:3: WARNING: Inline emphasis start-string without end-string. [docutils]
shape.m:docstring of shape:5: ERROR: Unknown interpreted text role "nosuchrole". [docutils]
shape.m:docstring of shape:4: WARNING: Inline emphasis start-string without end-string. [docutils]
shape.m:docstring of shape:6: ERROR: Unknown interpreted text role "nosuchrole". [docutils]
index.rst:3: WARNING: Inline emphasis start-string without end-string. [docutils]
index.rst:5: ERROR: Unknown interpreted text role "nosuchrole". [docutils]
```

- **Help-relative lines (`:3`, `:5`):** correct, but you have to count
  from the start of the help.
- **File lines (`:4`, `:6`):** the lines your editor shows.
- **Without the switch:** the page's file with the help-relative number.
  `index.rst` line 3 is "Lines numbered within the help, as Python's
  autodoc does:", which has nothing to do with the error.

## Limits worth knowing

- **Inline markup errors name the paragraph's first line.** The inliner
  gets the line where its text block starts, so a stray `*` on the second
  line of a paragraph is reported at the first. This is docutils
  behaviour, the same in every Sphinx project.
- **MyST is different.** It has no `StringList`. Nodes take
  `document["source"]` and the line from markdown-it's token map, and
  MyST's own warnings are located by `(docname, line)`. `{eval-rst}`
  parses reST in a new state machine after padding the text with blank
  lines so the numbers line up, and it reuses the page's reporter. So the
  "bound once" rule above applies to it, with surprising results when an
  `{eval-rst}` block contains `.. include::`. That is a story for the next
  post.
