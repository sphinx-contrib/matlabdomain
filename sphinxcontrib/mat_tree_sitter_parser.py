import re
from typing import cast

import tree_sitter_matlab as tsml
from sphinx.util.logging import getLogger
from tree_sitter import Language, Node, Query, QueryCursor


def get_nodes(match_dict, key):
    res = match_dict.get(key)
    if res:
        return sorted(
            res, key=lambda x: x.start_byte if hasattr(x, "start_byte") else 0
        )
    return []


def get_node(match_dict, key):
    res = match_dict.get(key)
    return res[0] if res else None


def required_node(match_dict, key) -> Node:
    return cast(Node, get_node(match_dict, key))


def node_text(node) -> bytes:
    return cast(bytes, node.text)


logger = getLogger("matlab-domain")

# Attribute defaults when no right hand side is given, for example
# `classdef (Abstract)` versus `classdef (Abstract=true)`.
# From:
#  - http://www.mathworks.com/help/matlab/matlab_oop/class-attributes.html
#  - https://mathworks.com/help/matlab/matlab_oop/property-attributes.html
#  - https://mathworks.com/help/matlab/matlab_prog/define-property-attributes-1.htm
#  - https://mathworks.com/help/matlab/matlab_oop/method-attributes.html
#  - https://mathworks.com/help/matlab/ref/matlab.unittest.testcase-class.html
MATLAB_ATTRIBUTE_DEFAULTS = {
    "AbortSet": True,
    "Abstract": True,
    "ClassSetupParameter": True,
    "Constant": True,
    "ConstructOnLoad": True,
    "Dependent": True,
    "DiscreteState": True,
    "GetObservable": True,
    "HandleCompatible": True,
    "Hidden": True,
    "MethodSetupParameter": True,
    "NonCopyable": True,
    "Nontunable": True,
    "PartialMatchPriority": True,
    "Sealed": True,
    "SetObservable": True,
    "Static": True,
    "Test": None,
    "TestClassSetup": None,
    "TestClassTeardown": None,
    "TestMethodSetup": None,
    "TestMethodTeardown": None,
    "TestParameter": None,
    "Transient": True,
}


ML_LANG = Language(tsml.language())

# QUERIES
q_classdef = Query(
    ML_LANG,
    """(class_definition
    .
    "classdef"
    .
    (line_continuation)?
    .
    (attributes
        [(attribute) @attrs _]+
    )?
    .
    (line_continuation)?
    .
    (identifier) @name
    .
    (line_continuation)?
    .
    (superclasses
        [(property_name) @supers _]+
    )?
    .
    (line_continuation)?
    .
    (comment)? @docstring
    ) @prop_node @class
""",
)

q_attributes = Query(
    ML_LANG,
    """(attribute
    (identifier) @name
    [
        (identifier) @value
        (string) @value
        (number) @value
        (not_operator) @value
        (metaclass_operator) @value
        (cell (row [(metaclass_operator) @value _]*))
        (cell (row [(string) @value _]*))
    ]? @rhs
    )
    """,
)

q_supers = Query(ML_LANG, """[(identifier) @secs "."]+ """)

q_properties = Query(
    ML_LANG,
    """(properties
    .
    (attributes
        [(attribute) @attrs _]+
    )?
    [(property) @properties  _]+
    ) @prop_block
""",
)

q_methods = Query(
    ML_LANG,
    """(methods
    (attributes
        [(attribute) @attrs _]+
    )?
    [(function_definition) @methods (function_signature) @signatures _]+
    ) @meth_block
""",
)

q_enumerations = Query(
    ML_LANG,
    """(enumeration
    [(enum) @enums _]+
    ) @enum_block
""",
)

q_events = Query(
    ML_LANG,
    """(events
    (attributes
        [(attribute) @attrs _]+
    )?
    [(identifier) @events _]+
    ) @event_block
""",
)

q_property = Query(
    ML_LANG,
    """
    (property name: (identifier) @name
     (dimensions
         [(spread_operator) @dims (number) @dims _]+
     )?
     (identifier)? @type
     .
     (identifier)? @size_type
     (validation_functions
         [(identifier) @validation_functions (function_call) @validation_functions _]+
     )?
     (default_value)? @default
     (comment)? @docstring
    ) @prop_node
""",
)

q_enum = Query(
    ML_LANG,
    """(enum
    .
    (identifier) @name
    [(_) @args _]*
    )
""",
)

# ``name`` is an identifier or a dotted property_name; ``(_)`` matches both and
# is ~15% faster than the alternation.
q_fun = Query(
    ML_LANG,
    """(function_definition
    _*
    (function_output
        [
            (identifier) @outputs
            (multioutput_variable
                [[(identifier) (ignored_argument)] @outputs _]+
            )
        ]
    )?
    _*
    name: (_) @name
    _*
    (function_arguments
        [(identifier) @params (ignored_argument) @params _]*
    )?
    _*
    [(arguments_statement) @argblocks _]*
    .
    (comment)? @docstring
    ) @prop_node
""",
)

q_argblock = Query(
    ML_LANG,
    """
    (arguments_statement
    .
    (attributes
        [(identifier) @attrs _]*
    )?
    .
    [(property) @args _]*
    )
""",
)

q_arg = Query(
    ML_LANG,
    """
    (property name:
        [
            (identifier) @name
            (property_name
                [(identifier) @name _]+
            )
        ]
     (dimensions
         [(spread_operator) @dims (number) @dims _]+
     )?
     (identifier)? @type
     (validation_functions
         [[(identifier) (function_call)] @validation_functions _]+
     )?
     (default_value [(number) (identifier)])? @default
     (comment)? @docstring
    ) @prop_node
""",
)

q_script = Query(
    ML_LANG,
    """
    (source_file
        (comment)? @docstring
    ) @prop_node
    """,
)

q_get_set = Query(ML_LANG, """["get." "set."]""")

q_function = Query(ML_LANG, "(function_definition) @f")

q_line_continuation = Query(ML_LANG, "(line_continuation) @lc")


# MATLAB ``help`` (R2026a, R2026b) drops one ``%``, or two (``%%`` starts a
# section); ``%%%%`` separator lines keep the rest.
re_percent_remove = re.compile(r"^[ \t]*%%? ?", flags=re.MULTILINE)
re_trim_line = re.compile(r"^[ \t]*", flags=re.MULTILINE)
re_assign_remove = re.compile(r"^=[ \t]*")

# Old-style property sizes (``x double vector``).
_SIZE_TYPES = {b"scalar": ("1", "1"), b"vector": (":", "1"), b"matrix": (":", ":")}


_PARSED_TYPES = {"class_definition": "class", "function_definition": "function"}


def declaration(root_node):
    """Return a file's first node that is not a comment, or None."""
    for node in root_node.named_children:
        if node.type not in ("comment", "line_continuation"):
            return node
    return None


def parsed_type(root_node):
    """Type tree-sitter gives a file: its first node that is not a comment.

    ``class``, ``function`` or ``script``; ``None`` if the file has no code.
    """
    node = declaration(root_node)
    if node is None:
        return None
    return _PARSED_TYPES.get(node.type, "script")


def first_error(root_node):
    """Return the zero-based ``(row, column)`` of the first syntax error, or None.

    The innermost ERROR or MISSING node of the first error: tree-sitter can
    wrap the rest of a file in an ERROR node that starts long before the
    problem. None if there is no error, or if the error is such a node with
    nothing nested (its location is unknown).
    """
    if not root_node.has_error:
        return None
    node = root_node
    while child := next((c for c in node.children if c.has_error), None):
        node = child
    if node.is_error and _wraps_file(root_node, node):
        return None
    point = node.start_point
    return point.row, point.column


def _wraps_file(root_node, node):
    """Check whether ``node`` spans from the file's first code to its end."""
    first = cast(
        Node, declaration(root_node) if root_node.type == "source_file" else root_node
    )
    tail = root_node.text[node.end_byte - root_node.start_byte :]
    return node.start_byte <= first.start_byte and not tail.strip()


def leading_comment(root_node, decl):
    """Return the first comment block before a file's declaration ``decl``.

    MATLAB ``help`` (R2026a) prefers it to the block after the ``function``
    or ``classdef`` line, blank lines or not; methods and local functions
    ignore it (``root_node`` is then not the file, so this returns None).
    """
    if root_node.type != "source_file":
        return None
    # ``decl`` is one of the named children, so the loop always stops early.
    for node in root_node.named_children:  # pragma: no branch
        if node.start_byte >= decl.start_byte:
            break
        if node.type == "comment":
            return node
    return None


def trailing_docstring(node, prev, encoding):
    """Return ``(docstring, line)`` of the comment ``node`` after a declaration.

    ``prev`` is the node before it. A comment on the declaration line is not
    help; if nothing follows it in its block, the next comment block is
    (MATLAB R2026a ``help``). ``line`` is the one-based file line of the first
    line of the docstring.
    """
    docstring = help_text(node.text, encoding)
    row = node.start_point.row + 1
    if node.start_point.row != prev.end_point.row:
        return docstring, row
    docstring = help_text(node.text, encoding, skip_first_line=True)
    after = node.next_named_sibling
    if not docstring and after is not None and after.type == "comment":
        return help_text(after.text, encoding), after.start_point.row + 1
    return docstring, row + 1


def help_text(text, encoding, skip_first_line=False):
    """Return the help text of a function's or class's comment node.

    Like MATLAB ``help`` (R2026a), it stops at the first line that is not a
    ``%`` line, so a ``%{ ... %}`` block gives ``{``.
    """
    lines = text.decode(encoding, errors="backslashreplace").split("\n")
    if skip_first_line:
        lines = lines[1:]
    kept = []
    for line in lines:
        if not line.lstrip().startswith("%"):
            break
        kept.append(line)
    return re.sub(re_percent_remove, "", "\n".join(kept))


def process_text_into_docstring(text, encoding):
    """Take a text bytestring and decode it into a docstring."""
    docstring = text.decode(encoding, errors="backslashreplace")
    return re.sub(re_percent_remove, "", docstring)


def comment_help(node, encoding, *, first_line_only=False, skip_first_line=False):
    """Return ``(help, line)`` of the comment ``node`` of a member: all its
    lines, the first, or all but the first (that one is the previous member's).
    ``line`` is the one-based file line of the first line of the help.
    """
    lines = process_text_into_docstring(node.text, encoding).split("\n")
    if first_line_only:
        lines = lines[:1]
    elif skip_first_line:
        lines = lines[1:]
    return "\n".join(lines), node.start_point.row + 1 + skip_first_line


def process_default(node, encoding):
    """Remove line continuations from a default value's node."""
    text = node.text
    to_keep = set(range(node.end_byte - node.start_byte))
    lc_matches = QueryCursor(q_line_continuation).matches(node)
    for _, match in lc_matches:
        # TODO this copies a lot perhaps there is a better option.
        lc = match["lc"][0]
        cut_start = lc.start_byte - node.start_byte
        cut_end = lc.end_byte - node.start_byte
        to_keep -= set(range(cut_start, cut_end))
    # NOTE: hardcoded endianness is fine because for one byte this does not matter.
    #       See python bikeshed on possible defaults for this here:
    #       https://discuss.python.org/t/what-should-be-the-default-value-for-int-to-bytes-byteorder/10616
    new_text = b"".join(
        [byte.to_bytes(1, "big") for idx, byte in enumerate(text) if idx in to_keep]
    )
    # TODO Traverse the parse in order to generate a reformatted single line.
    default = new_text.decode(encoding, errors="backslashreplace")
    default = re.sub(re_assign_remove, "", default)
    return re.sub(re_trim_line, "", default)


class MatScriptParser:
    def __init__(self, root_node, encoding):
        """Parse a MATLAB script"""
        self.encoding = encoding
        #: one-based file line of the first line of the docstring
        self.docstring_line = None
        script_matches = list(QueryCursor(q_script).matches(root_node))
        if script_matches:
            script_match = QueryCursor(q_script).captures(root_node)
            # The query is not anchored: it captures every top-level comment,
            # not in document order. The first one is the docstring.
            docstring_nodes = get_nodes(script_match, "docstring")
            docstring_node = docstring_nodes[0] if docstring_nodes else None
            if docstring_node is not None:
                self.docstring = process_text_into_docstring(
                    docstring_node.text, self.encoding
                )
                self.docstring_line = docstring_node.start_point.row + 1
            else:
                self.docstring = None
        else:
            self.docstring = None


class MatFunctionParser:
    def __init__(self, root_node, encoding):
        """Parse a function definition"""
        self.encoding = encoding
        fun_nodes = [m[1]["f"][0] for m in QueryCursor(q_function).matches(root_node)]
        fun_node = fun_nodes[0] if fun_nodes else root_node
        cursor = QueryCursor(q_fun)
        # Match ``fun_node`` only, not the nested functions in its body.
        cursor.set_max_start_depth(0)
        fun_match = cursor.captures(fun_node)
        self.name = node_text(required_node(fun_match, "name")).decode(
            self.encoding, errors="backslashreplace"
        )
        #: one-based line of the ``function`` keyword
        self.line = fun_node.start_point.row + 1
        #: ``opts.Name`` -> help of each name-value argument (None: no comment)
        self.name_value = {}

        # Get outputs (possibly more than one)
        self.retv = {}
        for output in get_nodes(fun_match, "outputs"):
            self.retv[output.text.decode(self.encoding, errors="backslashreplace")] = {}

        # Get parameters
        self.args = {}
        for arg in get_nodes(fun_match, "params"):
            self.args[arg.text.decode(self.encoding, errors="backslashreplace")] = {}

        # parse out info from argument blocks
        for argblock_node in get_nodes(fun_match, "argblocks"):
            self._parse_argument_section(argblock_node)

        # get docstring: the comment block after the declaration, blank lines
        # allowed, unless a block precedes a file's function (leading_comment).
        # Captures are not in document order: the first comment is the help.
        docstring_nodes = get_nodes(fun_match, "docstring")
        docstring_node = docstring_nodes[0] if docstring_nodes else None
        docstring = ""
        doc_line = None
        if docstring_node is not None:
            docstring, doc_line = trailing_docstring(
                docstring_node, docstring_node.prev_named_sibling, self.encoding
            )
        leading = leading_comment(root_node, fun_node)
        if leading is not None:
            docstring = help_text(leading.text, self.encoding)
            doc_line = leading.start_point.row + 1

        if not docstring:
            docstring = None
        self.docstring = docstring
        #: one-based file line of the first line of the docstring
        self.docstring_line = doc_line

    def _parse_argument_section(self, argblock_node):
        argblock_match = QueryCursor(q_argblock).captures(argblock_node)
        attrs_nodes = argblock_match.get("attrs")
        attrs = self._parse_attributes(attrs_nodes)

        # In document order: the last name-value argument's help wins.
        arguments = get_nodes(argblock_match, "args")
        if not arguments:
            return

        # TODO this is almost identical to property parsing.
        #      might be a good idea to extract common code here.
        # ``~`` (an ignored input) has no name, so ``q_arg`` does not match it
        matched = [
            (arg, matches[0][1])
            for arg in arguments
            if (matches := list(QueryCursor(q_arg).matches(arg)))
        ]
        for arg, arg_match in matched:
            # extract name (this is always available so no need for None check)
            name = [
                node_text(name).decode(self.encoding, errors="backslashreplace")
                for name in arg_match["name"]
            ]

            # extract dims list
            dims_list = get_nodes(arg_match, "dims")
            dims = None
            if dims_list:
                dims = tuple(
                    [
                        dim.text.decode(self.encoding, errors="backslashreplace")
                        for dim in dims_list
                    ]
                )

            # extract type
            type_node = get_node(arg_match, "type")
            typename = (
                node_text(type_node).decode(self.encoding, errors="backslashreplace")
                if type_node is not None
                else None
            )

            # extract validator functions
            vf_list = get_nodes(arg_match, "validation_functions")
            vfs = None
            if vf_list:
                vfs = [
                    vf.text.decode(self.encoding, errors="backslashreplace")
                    for vf in vf_list
                ]

            # extract default
            default_node = get_node(arg_match, "default")
            default = (
                process_default(default_node, self.encoding)
                if default_node is not None
                else None
            )

            # extract inline or following docstring if there is no semicolon
            # (tree-sitter-matlab puts the comment after the property node)
            prop_node = required_node(arg_match, "prop_node")
            docstring_node = None
            if prop_node.next_sibling and prop_node.next_sibling.type == "comment":
                docstring_node = prop_node.next_sibling
            docstring = ""
            if docstring_node is not None:
                # tree-sitter-matlab combines inline comments with following
                # comments which means this requires some relatively ugly
                # processing, but worth it for the ease of the rest of it.
                prev_sib = cast(Node, docstring_node.prev_named_sibling)
                if docstring_node.start_point.row == prev_sib.end_point.row:
                    # Keep only inline help on the declaration line.
                    docstring = process_text_into_docstring(
                        docstring_node.text, self.encoding
                    )
                    docstring = docstring.split("\n")[0]
                elif docstring_node.start_point.row - prev_sib.end_point.row <= 1:
                    # Otherwise take the whole docstring
                    docstring = process_text_into_docstring(
                        docstring_node.text, self.encoding
                    )

            # extract inline or following docstring if there _is_ a semicolon.
            # Only try this if no docstring was found above.
            next_node = arg.next_named_sibling
            if next_node is None or docstring != "":
                # Nothing to be done.
                pass
            elif next_node.type == "comment":
                if next_node.start_point.row == arg.end_point.row:
                    # Keep only inline help on the declaration line.
                    docstring = process_text_into_docstring(
                        next_node.text, self.encoding
                    )
                    docstring = docstring.split("\n")[0]
                elif next_node.start_point.row - arg.end_point.row <= 1:
                    # Otherwise take the whole docstring
                    docstring = process_text_into_docstring(
                        next_node.text, self.encoding
                    )

            # override docstring with prior if exists
            prev_node = arg.prev_named_sibling
            # A previous comment that ends on the line before sets the
            # docstring; a first line on the same line as the previous
            # argument belongs to that argument.
            if (
                prev_node is not None
                and prev_node.type == "comment"
                and arg.start_point.row - prev_node.end_point.row <= 1
            ):
                ds = process_text_into_docstring(prev_node.text, self.encoding)
                prev_arg = prev_node.prev_named_sibling
                if prev_arg is not None and prev_arg.type == "property":
                    if prev_node.start_point.row == prev_arg.end_point.row:
                        ds = "\n".join(ds.split("\n")[1:])
                if ds:
                    docstring = ds
            # After all that if our docstring is empty then we have none
            if not docstring.strip():
                docstring = None

            # Here we trust that the person is giving us valid matlab. A
            # name-value argument (``opts.Name``) is listed under ``opts``.
            arg_loc = self.retv if "Output" in attrs else self.args
            name_node = arg.child_by_field_name("name")
            if name_node.type == "property_name" and arg_loc is self.args:
                full_name = name_node.text.decode(
                    self.encoding, errors="backslashreplace"
                )
                self.name_value[full_name] = docstring
            arg_loc[name[0]] = {
                "attrs": attrs,
                "size": dims,
                "type": typename,
                "validators": vfs,
                "default": default,
                "docstring": docstring,
            }

    def _parse_attributes(self, attrs_nodes):
        attrs = {}
        if attrs_nodes is not None:
            for attr_node in attrs_nodes:
                name = attr_node.text.decode(self.encoding, errors="backslashreplace")
                attrs[name] = None
        return attrs


def member_help(node, encoding):
    """Return ``(help, line)`` of a one-line class member (an abstract method
    signature, an event) as for a property: a comment on its line, or a
    comment block right above or below it; ``(None, None)`` if it has none.
    ``line`` is the one-based file line of the first line of the help.
    """
    docstring, doc_line = "", None
    after = node.next_named_sibling
    if after is not None and after.type == "comment":
        gap = after.start_point.row - node.end_point.row
        if gap == 0:
            docstring, doc_line = comment_help(after, encoding, first_line_only=True)
        elif gap == 1:
            docstring, doc_line = comment_help(after, encoding)
    before = node.prev_named_sibling
    if (
        before is not None
        and before.type == "comment"
        and node.start_point.row - before.end_point.row <= 1
    ):
        prev = before.prev_named_sibling
        skip = prev is not None and before.start_point.row == prev.end_point.row
        ds, ds_line = comment_help(before, encoding, skip_first_line=skip)
        if ds:
            docstring, doc_line = ds, ds_line
    return (docstring, doc_line) if docstring.strip() else (None, None)


class MatSignature:
    """A method signature declared without a body (an abstract method)."""

    def __init__(self, cls, node, name, attrs):
        def text(n):
            return node_text(n).decode(cls.encoding, errors="backslashreplace")

        self.name = name
        self.attrs = attrs
        self.line = node.start_point.row + 1
        self.name_value = {}
        self.retv = {}
        self.args = {}
        for child in node.named_children:
            if child.type == "function_output":
                out = child.named_children[0]
                outs = (
                    out.named_children if out.type == "multioutput_variable" else [out]
                )
                self.retv = {text(n): {} for n in outs}
            elif child.type == "function_arguments":
                self.args = {text(n): {} for n in child.named_children}
        self.docstring, self.docstring_line = member_help(node, cls.encoding)


class MatClassParser:
    def __init__(self, root_node, encoding):
        # DATA
        self.encoding = encoding
        self.name = ""
        self.supers = []
        self.attrs = {}
        self.docstring = ""
        self.properties = {}
        self.methods = {}
        #: attributes of the method signatures declared without a body
        #: (implemented in class-folder files, or abstract), by name
        self.declarations = {}
        self.enumerations = {}
        #: ``{name: {"attrs", "docstring", "line"}}`` of the events
        self.events = {}

        self.root_node = root_node

        # Parse class basics
        class_matches = list(QueryCursor(q_classdef).matches(root_node))
        if not class_matches:
            raise ValueError("tree-sitter found no class name")

        _, class_match = class_matches[0]
        self.cls = required_node(class_match, "class")
        self.name = get_node(class_match, "name")
        #: one-based line of the ``classdef`` keyword
        self.line = self.cls.start_point.row + 1

        # Parse class attrs and supers
        attrs_nodes = class_match.get("attrs")
        self.attrs = self._parse_attributes(attrs_nodes)

        supers_nodes = class_match.get("supers")
        if supers_nodes is not None:
            for super_node in supers_nodes:
                super_match = next(iter(QueryCursor(q_supers).matches(super_node)))[1]
                super_cls = [
                    sec.text.decode(self.encoding, errors="backslashreplace")
                    for sec in get_nodes(super_match, "secs")
                ]
                self.supers.append(".".join(super_cls))

        # get docstring (same rule as MatFunctionParser)
        docstring_node = get_node(class_match, "docstring")
        docstring = ""
        doc_line = None
        if docstring_node is not None:
            docstring, doc_line = trailing_docstring(
                docstring_node, docstring_node.prev_named_sibling, self.encoding
            )
        leading = leading_comment(root_node, self.cls)
        if leading is not None:
            docstring = help_text(leading.text, self.encoding)
            doc_line = leading.start_point.row + 1
        self.docstring = docstring
        #: one-based file line of the first line of the docstring
        self.docstring_line = doc_line

        prop_matches = list(QueryCursor(q_properties).matches(self.cls))
        method_matches = list(QueryCursor(q_methods).matches(self.cls))
        enum_matches = list(QueryCursor(q_enumerations).matches(self.cls))
        event_matches = list(QueryCursor(q_events).matches(self.cls))

        for _, prop_match in prop_matches:
            self._parse_property_section(prop_match)
        for _, enum_match in enum_matches:
            self._parse_enum_section(enum_match)
        for _, method_match in method_matches:
            self._parse_method_section(method_match)
        for _, event_match in event_matches:
            attrs = self._parse_attributes(event_match.get("attrs"))
            for event in event_match.get("events", ()):
                name = node_text(event).decode(self.encoding, errors="backslashreplace")
                docstring, doc_line = member_help(event, self.encoding)
                self.events[name] = {
                    "attrs": attrs,
                    "docstring": docstring,
                    "docstring_line": doc_line,
                    "line": event.start_point.row + 1,
                }

    def _parse_property_section(self, props_match):
        properties = props_match.get("properties")
        if properties is None:
            return
        # extract property section attributes
        attrs_nodes = props_match.get("attrs")
        attrs = self._parse_attributes(attrs_nodes)
        for prop in properties:
            # The optional identifiers match in several ways; the match with
            # the most captures, a type before a size, is the declaration.
            prop_match = max(
                (match for _, match in QueryCursor(q_property).matches(prop)),
                key=lambda match: (sum(map(len, match.values())), "type" in match),
            )
            # extract name (this is always available so no need for None check)
            name = node_text(required_node(prop_match, "name")).decode(
                self.encoding, errors="backslashreplace"
            )

            # extract dims list
            size_type = get_node(prop_match, "size_type")
            dims_list = get_nodes(prop_match, "dims")
            dims = None
            if dims_list:
                dims = tuple(
                    [
                        dim.text.decode(self.encoding, errors="backslashreplace")
                        for dim in dims_list
                    ]
                )
            elif size_type is not None:
                dims = _SIZE_TYPES.get(node_text(size_type))

            # extract validator functions
            vf_list = get_nodes(prop_match, "validation_functions")
            vfs = None
            if vf_list:
                vfs = [
                    vf.text.decode(self.encoding, errors="backslashreplace")
                    for vf in vf_list
                ]

            # extract type
            type_node = get_node(prop_match, "type")
            typename = (
                node_text(type_node).decode(self.encoding, errors="backslashreplace")
                if type_node is not None
                else None
            )

            # extract default
            default_node = get_node(prop_match, "default")
            default = (
                process_default(default_node, self.encoding)
                if default_node is not None
                else None
            )

            # extract inline or following docstring if there is no semicolon
            # (tree-sitter-matlab puts the comment after the property node)
            prop_node = required_node(prop_match, "prop_node")
            docstring_node = None
            if prop_node.next_sibling and prop_node.next_sibling.type == "comment":
                docstring_node = prop_node.next_sibling
            docstring, doc_line = "", None
            if docstring_node is not None:
                # tree-sitter-matlab combines inline comments with following
                # comments which means this requires some relatively ugly
                # processing, but worth it for the ease of the rest of it.
                prev_sib = cast(Node, docstring_node.prev_named_sibling)
                if docstring_node.start_point.row == prev_sib.end_point.row:
                    # Keep only inline help on the declaration line.
                    docstring, doc_line = comment_help(
                        docstring_node, self.encoding, first_line_only=True
                    )
                elif docstring_node.start_point.row - prev_sib.end_point.row <= 1:
                    # Otherwise take the whole docstring
                    docstring, doc_line = comment_help(docstring_node, self.encoding)

            # extract inline or following docstring if there _is_ a semicolon.
            # Only try this if no docstring was found above.
            next_node = prop.next_named_sibling
            if next_node is None or docstring != "":
                # Nothing to be done.
                pass
            elif next_node.type == "comment":
                if next_node.start_point.row == prop.end_point.row:
                    # Keep only inline help on the declaration line.
                    docstring, doc_line = comment_help(
                        next_node, self.encoding, first_line_only=True
                    )
                elif next_node.start_point.row - prop.end_point.row <= 1:
                    # Otherwise take the whole docstring
                    docstring, doc_line = comment_help(next_node, self.encoding)

            # override docstring with prior if exists
            prev_node = prop.prev_named_sibling
            # A previous comment that ends on the line before sets the
            # docstring; a first line on the same line as the previous
            # property belongs to that property.
            if (
                prev_node is not None
                and prev_node.type == "comment"
                and prop.start_point.row - prev_node.end_point.row <= 1
            ):
                prev_prop = prev_node.prev_named_sibling
                skip = (
                    prev_prop is not None
                    and prev_prop.type == "property"
                    and prev_node.start_point.row == prev_prop.end_point.row
                )
                ds, ds_line = comment_help(
                    prev_node, self.encoding, skip_first_line=skip
                )
                if ds:
                    docstring, doc_line = ds, ds_line
            # After all that if our docstring is empty then we have none
            if not docstring.strip():
                docstring = None

            self.properties[name] = {
                "attrs": attrs,
                "size": dims,
                "type": typename,
                "validators": vfs,
                "default": default,
                "docstring": docstring,
                "docstring_line": doc_line,
                "line": prop.start_point.row + 1,
            }

    def _parse_method_section(self, methods_match):
        attrs_nodes = methods_match.get("attrs")
        attrs = self._parse_attributes(attrs_nodes)
        for signature in methods_match.get("signatures", ()):
            name = signature.child_by_field_name("name")
            name = node_text(name).decode(self.encoding, errors="backslashreplace")
            self.declarations[name] = attrs
            if attrs.get("Abstract"):
                self.methods[name] = MatSignature(self, signature, name, attrs)
        methods = methods_match.get("methods")
        if methods is None:
            return
        for method in methods:
            is_set_get = list(QueryCursor(q_get_set).matches(method))
            # Skip getter and setter
            if len(is_set_get) > 0:
                continue
            # Skip converter methods (``function obj = pkg.Cls(x)``): a dotted
            # name cannot be a member reference.
            name = method.child_by_field_name("name")
            if name is not None and name.type == "property_name":
                continue
            parsed_function = MatFunctionParser(method, self.encoding)
            self.methods[parsed_function.name] = parsed_function
            self.methods[parsed_function.name].attrs = attrs

    def _parse_enum_section(self, enums_match):
        enums = enums_match.get("enums")
        if enums is None:
            return
        for enum in enums:
            enum_match = next(iter(QueryCursor(q_enum).matches(enum)))[1]
            name = node_text(required_node(enum_match, "name")).decode(
                self.encoding, errors="backslashreplace"
            )
            arg_nodes = enum_match.get("args")
            if arg_nodes is not None:
                args = [
                    node_text(arg).decode(self.encoding, errors="backslashreplace")
                    for arg in arg_nodes
                ]
            else:
                args = None

            docstring, doc_line = "", None
            # look forward for docstring
            next_node = enum.next_named_sibling
            if next_node is not None and next_node.type == "comment":
                if next_node.start_point.row == enum.end_point.row:
                    # Keep only inline help on the declaration line.
                    docstring, doc_line = comment_help(
                        next_node, self.encoding, first_line_only=True
                    )
                elif next_node.start_point.row - enum.end_point.row <= 1:
                    # Otherwise take the whole docstring
                    docstring, doc_line = comment_help(next_node, self.encoding)

            # override docstring with prior if exists
            prev_node = enum.prev_named_sibling
            # A previous comment that ends on the line before sets the
            # docstring; a first line on the same line as the previous enum
            # belongs to that enum.
            if (
                prev_node is not None
                and prev_node.type == "comment"
                and enum.start_point.row - prev_node.end_point.row <= 1
            ):
                prev_enum = prev_node.prev_named_sibling
                skip = (
                    prev_enum is not None
                    and prev_enum.type == "enum"
                    and prev_node.start_point.row == prev_enum.end_point.row
                )
                ds, ds_line = comment_help(
                    prev_node, self.encoding, skip_first_line=skip
                )
                if ds:
                    docstring, doc_line = ds, ds_line
            # After all that if our docstring is empty then we have none
            if docstring.strip() == "":
                docstring = None

            self.enumerations[name] = {
                "args": args,
                "docstring": docstring,
                "docstring_line": doc_line,
            }

    def _parse_attributes(self, attrs_nodes):
        attrs = {}
        if attrs_nodes is not None:
            for attr_node in attrs_nodes:
                first = attr_node.named_children[0]
                if first.type == "not_operator":
                    # ``~Hidden`` is ``Hidden = false``
                    name = node_text(first.named_children[-1]).decode(
                        self.encoding, errors="backslashreplace"
                    )
                    attrs[name] = False
                    continue
                attr_match = QueryCursor(q_attributes).captures(attr_node)
                name = node_text(required_node(attr_match, "name")).decode(
                    self.encoding, errors="backslashreplace"
                )
                value_node = get_nodes(attr_match, "value")
                rhs_node = get_node(attr_match, "rhs")
                if rhs_node is not None:
                    if rhs_node.type == "cell":
                        attrs[name] = [
                            vn.text.decode(self.encoding, errors="backslashreplace")
                            for vn in value_node
                        ]
                    else:
                        attrs[name] = self._attribute_value(value_node[0])
                else:
                    attrs[name] = MATLAB_ATTRIBUTE_DEFAULTS.get(name)

        return attrs

    def _attribute_value(self, node):
        """Return a logical value as a bool (``0``, ``~true``), else the text."""
        text = node_text(node).decode(self.encoding, errors="backslashreplace")
        if node.type == "not_operator":
            inner = self._attribute_value(node.named_children[-1])
            return not inner if isinstance(inner, bool) else text
        if text in ("true", "false"):
            return text == "true"
        if node.type == "number":
            try:
                return float(text) != 0
            except ValueError:  # a hexadecimal or binary literal
                return text
        return text
