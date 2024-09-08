from importlib.metadata import version
import tree_sitter_matlab as tsml
from tree_sitter import Language, Parser
import re

# Attribute default dictionary used to give default values for e.g. `Abstract` or `Static` when used without
# a right hand side i.e. `classdef (Abstract)` vs `classdef (Abstract=true)`
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


tree_sitter_ver = tuple([int(sec) for sec in version("tree_sitter").split(".")])
if tree_sitter_ver[1] == 21:
    ML_LANG = Language(tsml.language(), "matlab")
else:
    ML_LANG = Language(tsml.language())

# QUERIES
q_classdef = ML_LANG.query(
    """(class_definition
    .
    "classdef"
    .
    (attributes
        [(attribute) @attrs _]+
    )?
    .
    (identifier) @name
    .
    (superclasses
        [(property_name) @supers _]+
    )?
    .
    (comment)? @docstring
    ) @class
"""
)

q_attributes = ML_LANG.query(
    """(attribute
    (identifier) @name
    [
        (identifier) @value
        (string) @value
        (metaclass_operator) @value
        (cell (row [(metaclass_operator) @value _]*))
        (cell (row [(string) @value _]*))
    ]? @rhs
    )
    """
)

q_supers = ML_LANG.query("""[(identifier) @secs "."]+ """)

q_properties = ML_LANG.query(
    """(properties
    .
    (attributes
        [(attribute) @attrs _]+
    )?
    [(property) @properties  _]+
    ) @prop_block
"""
)

q_methods = ML_LANG.query(
    """(methods
    (attributes
        [(attribute) @attrs _]+
    )?
    [(function_definition) @methods _]+
    ) @meth_block
"""
)

q_enumerations = ML_LANG.query(
    """(enumeration
    [(enum) @enums _]+
    ) @enum_block
"""
)

q_events = ML_LANG.query(
    """(events
    (attributes
        [(attribute) @attrs _]+
    )?
    (identifier)+ @events
    ) @event_block
"""
)

q_property = ML_LANG.query(
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
    )
"""
)

q_old_property = ML_LANG.query(
    """
    (property name: (identifier) @name
     (identifier) @type
     (identifier)? @size_type
     (default_value)? @default
     (comment)? @docstring
    )
"""
)

q_enum = ML_LANG.query(
    """(enum
    .
    (identifier) @name
    [(_) @args _]*
    )
"""
)

q_fun = ML_LANG.query(
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
    name: (identifier) @name
    _*
    (function_arguments
        [(identifier) @params (ignored_argument) @params _]*
    )?
    _*
    [(arguments_statement) @argblocks _]*
    .
    (comment)? @docstring
    )
"""
)

q_argblock = ML_LANG.query(
    """
    (arguments_statement
    .
    (attributes
        [(identifier) @attrs _]*
    )?
    .
    [(property) @args _]*
    )
"""
)

q_arg = ML_LANG.query(
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
    )
"""
)

q_script = ML_LANG.query(
    """
    (source_file
        (comment)? @docstring
    )
    """
)

q_get_set = ML_LANG.query("""["get." "set."]""")

q_line_continuation = ML_LANG.query("(line_continuation) @lc")


re_percent_remove = re.compile(r"^[ \t]*% ?", flags=re.M)
re_trim_line = re.compile(r"^[ \t]*", flags=re.M)
re_assign_remove = re.compile(r"^=[ \t]*")


def tree_sitter_is_0_21():
    """Check if tree-sitter is v0.21.* in order to use the correct language initialization and syntax."""
    if not hasattr(tree_sitter_is_0_21, "is_21"):
        tree_sitter_ver = tuple([int(sec) for sec in version("tree_sitter").split(".")])
        tree_sitter_is_0_21.is_21 = tree_sitter_ver[1] == 21  # memoize
    return tree_sitter_is_0_21.is_21


def get_row(point):
    """Get row from point. This api changed from v0.21.3 to v0.22.0"""
    if tree_sitter_is_0_21():
        return point[0]
    else:
        return point.row


def process_text_into_docstring(text, encoding):
    """Take a text bytestring and decode it into a docstring."""
    docstring = text.decode(encoding, errors="backslashreplace")
    return re.sub(re_percent_remove, "", docstring)


def process_default(node, encoding):
    """Take the node defining a default and remove any line continuations before generating the default."""
    text = node.text
    to_keep = set(range(node.end_byte - node.start_byte))
    lc_matches = q_line_continuation.matches(node)
    for _, match in lc_matches:
        # TODO this copies a lot perhaps there is a better option.
        lc = match["lc"]
        cut_start = lc.start_byte - node.start_byte
        cut_end = lc.end_byte - node.start_byte
        to_keep -= set(range(cut_start, cut_end))
    # NOTE: hardcoded endianess is fine because for one byte this does not matter.
    #       See python bikeshed on possible defaults for this here:
    #       https://discuss.python.org/t/what-should-be-the-default-value-for-int-to-bytes-byteorder/10616
    new_text = b"".join(
        [byte.to_bytes(1, "big") for idx, byte in enumerate(text) if idx in to_keep]
    )
    # TODO We may want to do an in-order traversal of the parse here to generate a "nice" reformatted single line
    #      however doing so sufficiently generically is likely a major undertaking.
    default = new_text.decode(encoding, errors="backslashreplace")
    default = re.sub(re_assign_remove, "", default)
    return re.sub(re_trim_line, "", default)


class MatScriptParser:
    def __init__(self, root_node, encoding):
        """Parse m script"""
        self.encoding = encoding
        script_matches = q_script.matches(root_node)
        if script_matches:
            _, script_match = q_script.matches(root_node)[0]
            docstring_node = script_match.get("docstring")
            if docstring_node is not None:
                self.docstring = process_text_into_docstring(
                    docstring_node.text, self.encoding
                )
            else:
                self.docstring = None
        else:
            self.docstring = None


class MatFunctionParser:
    def __init__(self, root_node, encoding):
        """Parse Function definition"""
        self.encoding = encoding
        _, fun_match = q_fun.matches(root_node)[0]
        self.name = fun_match.get("name").text.decode(
            self.encoding, errors="backslashreplace"
        )

        # Get outputs (possibly more than one)
        self.retv = {}
        output_nodes = fun_match.get("outputs")
        if output_nodes is not None:
            retv = [
                output.text.decode(self.encoding, errors="backslashreplace")
                for output in output_nodes
            ]
            for output in retv:
                self.retv[output] = {}

        # Get parameters
        self.args = {}
        arg_nodes = fun_match.get("params")
        if arg_nodes is not None:
            args = [
                arg.text.decode(self.encoding, errors="backslashreplace")
                for arg in arg_nodes
            ]
            for arg in args:
                self.args[arg] = {}

        # parse out info from argument blocks
        argblock_nodes = fun_match.get("argblocks")
        if argblock_nodes is not None:
            for argblock_node in argblock_nodes:
                self._parse_argument_section(argblock_node)

        # get docstring
        docstring_node = fun_match.get("docstring")
        docstring = ""
        if docstring_node is not None:
            prev_sib = docstring_node.prev_named_sibling
            if get_row(docstring_node.start_point) - get_row(prev_sib.end_point) <= 1:
                if get_row(docstring_node.start_point) == get_row(prev_sib.end_point):
                    # if the docstring is on the same line as the end of the function drop it
                    docstring = process_text_into_docstring(
                        docstring_node.text, self.encoding
                    )
                    split_ds = docstring.split("\n")
                    docstring = "\n".join(split_ds[1:]) if len(split_ds) > 1 else ""
                else:
                    docstring = process_text_into_docstring(
                        docstring_node.text, self.encoding
                    )

        if not docstring:
            docstring = None
        self.docstring = docstring

    def _parse_argument_section(self, argblock_node):
        _, argblock_match = q_argblock.matches(argblock_node)[0]
        attrs_nodes = argblock_match.get("attrs")
        attrs = self._parse_attributes(attrs_nodes)

        arguments = argblock_match.get("args")

        # TODO this is almost identical to property parsing.
        #      might be a good idea to extract common code here.
        for arg in arguments:
            # match property to extract details
            _, arg_match = q_arg.matches(arg)[0]

            # extract name (this is always available so no need for None check)
            name = [
                name.text.decode(self.encoding, errors="backslashreplace")
                for name in arg_match.get("name")
            ]

            # extract dims list
            dims_list = arg_match.get("dims")
            dims = None
            if dims_list is not None:
                dims = tuple(
                    [
                        dim.text.decode(self.encoding, errors="backslashreplace")
                        for dim in dims_list
                    ]
                )

            # extract type
            type_node = arg_match.get("type")
            typename = (
                type_node.text.decode(self.encoding, errors="backslashreplace")
                if type_node is not None
                else None
            )

            # extract validator functions
            vf_list = arg_match.get("validation_functions")
            vfs = None
            if vf_list is not None:
                vfs = [
                    vf.text.decode(self.encoding, errors="backslashreplace")
                    for vf in vf_list
                ]

            # extract default
            default_node = arg_match.get("default")
            default = (
                process_default(default_node, self.encoding)
                if default_node is not None
                else None
            )

            # extract inline or following docstring if there is no semicolon
            docstring_node = arg_match.get("docstring")
            docstring = ""
            if docstring_node is not None:
                # tree-sitter-matlab combines inline comments with following
                # comments which means this requires some relatively ugly
                # processing, but worth it for the ease of the rest of it.
                prev_sib = docstring_node.prev_named_sibling
                if get_row(docstring_node.start_point) == get_row(prev_sib.end_point):
                    # if the docstring is on the same line as the end of the definition only take the inline part
                    docstring = process_text_into_docstring(
                        docstring_node.text, self.encoding
                    )
                    docstring = docstring.split("\n")[0]
                elif (
                    get_row(docstring_node.start_point) - get_row(prev_sib.end_point)
                    <= 1
                ):
                    # Otherwise take the whole docstring
                    docstring = process_text_into_docstring(
                        docstring_node.text, self.encoding
                    )

            # extract inline or following docstring if there _is_ a semicolon.
            # this is only done if we didn't already find a docstring with the previous approach
            next_node = arg.next_named_sibling
            if next_node is None or docstring is not None:
                # Nothing to be done.
                pass
            elif next_node.type == "comment":
                if get_row(next_node.start_point) == get_row(arg.end_point):
                    # if the docstring is on the same line as the end of the definition only take the inline part
                    docstring = process_text_into_docstring(
                        next_node.text, self.encoding
                    )
                    docstring = docstring.split("\n")[0]
                elif get_row(next_node.start_point) - get_row(arg.end_point) <= 1:
                    # Otherwise take the whole docstring
                    docstring = process_text_into_docstring(
                        next_node.text, self.encoding
                    )

            # override docstring with prior if exists
            prev_node = arg.prev_named_sibling
            if prev_node is None:
                # Nothing we can do, no previous comment
                pass
            elif prev_node.type == "comment":
                # We have a previous comment if it ends on the previous
                # line then we set the docstring. We also need to check
                # if the first line of the comment is the same as a
                # previous argument.
                if get_row(arg.start_point) - get_row(prev_node.end_point) <= 1:
                    ds = process_text_into_docstring(prev_node.text, self.encoding)
                    prev_arg = prev_node.prev_named_sibling
                    if prev_arg is not None and prev_arg.type == "property":
                        if get_row(prev_node.start_point) == get_row(
                            prev_arg.end_point
                        ):
                            ds = "\n".join(ds.split("\n")[1:])
                    if ds:
                        docstring = ds
                else:
                    if get_row(arg.start_point) - get_row(prev_node.end_point) <= 1:
                        docstring = process_text_into_docstring(
                            prev_node.text, self.encoding
                        )
            elif prev_node.type == "property":
                # The previous argumentnode may have eaten our comment
                # check for it a trailing comment. If it is not there
                # then we stop looking.
                prev_comment = prev_node.named_children[-1]
                if prev_comment.type == "comment":
                    # we now need to check if prev_comment ends on the line
                    # before ours and trim the first line if it on the same
                    # line as prev property.
                    if get_row(arg.start_point) - get_row(prev_comment.end_point) <= 1:
                        ds = process_text_into_docstring(
                            prev_comment.text, self.encoding
                        )
                        if get_row(prev_comment.start_point) == get_row(
                            prev_comment.prev_named_sibling.end_point
                        ):
                            ds = "\n".join(ds.split("\n")[1:])
                        if ds:
                            docstring = ds
            # After all that if our docstring is empty then we have none
            if not docstring.strip():
                docstring = None
            else:
                pass  # docstring = docstring.rstrip()

            # Here we trust that the person is giving us valid matlab.
            if "Output" in attrs.keys():
                arg_loc = self.retv
            else:
                arg_loc = self.args
            if len(name) == 1:
                arg_loc[name[0]] = {
                    "attrs": attrs,
                    "size": dims,
                    "type": typename,
                    "validators": vfs,
                    "default": default,
                    "docstring": docstring,
                }
            else:
                # how to handle dotted args
                pass

    def _parse_attributes(self, attrs_nodes):
        attrs = {}
        if attrs_nodes is not None:
            for attr_node in attrs_nodes:
                name = attr_node.text.decode(self.encoding, errors="backslashreplace")
                attrs[name] = None
        return attrs


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
        self.enumerations = {}
        self.events = {}

        self.root_node = root_node

        # Parse class basics
        class_matches = q_classdef.matches(root_node)
        _, class_match = class_matches[0]
        self.cls = class_match.get("class")
        self.name = class_match.get("name")

        # Parse class attrs and supers
        attrs_nodes = class_match.get("attrs")
        self.attrs = self._parse_attributes(attrs_nodes)

        supers_nodes = class_match.get("supers")
        if supers_nodes is not None:
            for super_node in supers_nodes:
                _, super_match = q_supers.matches(super_node)[0]
                super_cls = [
                    sec.text.decode(self.encoding, errors="backslashreplace")
                    for sec in super_match.get("secs")
                ]
                self.supers.append(".".join(super_cls))

        # get docstring and check that it consecutive
        docstring_node = class_match.get("docstring")
        docstring = ""
        if docstring_node is not None:
            prev_node = docstring_node.prev_sibling
            if get_row(docstring_node.start_point) - get_row(prev_node.end_point) <= 1:
                if get_row(docstring_node.start_point) == get_row(prev_node.end_point):
                    # if the docstring is on the same line as the end of the classdef drop it
                    docstring = process_text_into_docstring(
                        docstring_node.text, self.encoding
                    )
                    split_ds = docstring.split("\n")
                    docstring = "\n".join(split_ds[1:]) if len(split_ds) > 1 else ""
                else:
                    docstring = process_text_into_docstring(
                        docstring_node.text, self.encoding
                    )
        self.docstring = docstring

        prop_matches = q_properties.matches(self.cls)
        method_matches = q_methods.matches(self.cls)
        enum_matches = q_enumerations.matches(self.cls)
        event_matches = q_events.matches(self.cls)

        for _, prop_match in prop_matches:
            self._parse_property_section(prop_match)
        for _, enum_match in enum_matches:
            self._parse_enum_section(enum_match)
        for _, method_match in method_matches:
            self._parse_method_section(method_match)
        for _, event_match in event_matches:
            self._parse_event_section(event_match)

    def _parse_property_section(self, props_match):
        properties = props_match.get("properties")
        if properties is None:
            return
        # extract property section attributes
        attrs_nodes = props_match.get("attrs")
        attrs = self._parse_attributes(attrs_nodes)
        for prop in properties:
            # match property to extract details
            _, prop_match = q_property.matches(prop)[0]
            print(prop.sexp())
            # extract name (this is always available so no need for None check)
            name = prop_match.get("name").text.decode(
                self.encoding, errors="backslashreplace"
            )

            # extract dims list
            size_type = prop_match.get("size_type")
            dims_list = prop_match.get("dims")
            dims = None
            if dims_list is not None:
                dims = tuple(
                    [
                        dim.text.decode(self.encoding, errors="backslashreplace")
                        for dim in dims_list
                    ]
                )
            elif size_type is None:
                dims = None
            elif size_type.text == b"scalar":
                dims = ("1", "1")
            elif size_type.text == b"vector":
                dims = (":", "1")
            elif size_type.text == b"matrix":
                dims = (":", ":")

            # extract validator functions
            vf_list = prop_match.get("validation_functions")
            vfs = None
            if vf_list is not None:
                vfs = [
                    vf.text.decode(self.encoding, errors="backslashreplace")
                    for vf in vf_list
                ]

            # extract type
            type_node = prop_match.get("type")
            typename = (
                type_node.text.decode(self.encoding, errors="backslashreplace")
                if type_node is not None
                else None
            )

            # extract default
            default_node = prop_match.get("default")
            default = (
                process_default(default_node, self.encoding)
                if default_node is not None
                else None
            )

            # extract inline or following docstring if there is no semicolon
            docstring_node = prop_match.get("docstring")
            docstring = ""
            if docstring_node is not None:
                # tree-sitter-matlab combines inline comments with following
                # comments which means this requires some relatively ugly
                # processing, but worth it for the ease of the rest of it.
                prev_sib = docstring_node.prev_named_sibling
                if get_row(docstring_node.start_point) == get_row(prev_sib.end_point):
                    # if the docstring is on the same line as the end of the definition only take the inline part
                    docstring = process_text_into_docstring(
                        docstring_node.text, self.encoding
                    )
                    docstring = docstring.split("\n")[0]
                elif (
                    get_row(docstring_node.start_point) - get_row(prev_sib.end_point)
                    <= 1
                ):
                    # Otherwise take the whole docstring
                    docstring = process_text_into_docstring(
                        docstring_node.text, self.encoding
                    )

            # extract inline or following docstring if there _is_ a semicolon.
            # this is only done if we didn't already find a docstring with the previous approach
            next_node = prop.next_named_sibling
            if next_node is None or docstring != "":
                # Nothing to be done.
                pass
            elif next_node.type == "comment":
                if get_row(next_node.start_point) == get_row(prop.end_point):
                    # if the docstring is on the same line as the end of the definition only take the inline part
                    docstring = process_text_into_docstring(
                        next_node.text, self.encoding
                    )
                    docstring = docstring.split("\n")[0]
                elif get_row(next_node.start_point) - get_row(prop.end_point) <= 1:
                    # Otherwise take the whole docstring
                    docstring = process_text_into_docstring(
                        next_node.text, self.encoding
                    )

            # override docstring with prior if exists
            prev_node = prop.prev_named_sibling
            if prev_node is None:
                # Nothing we can do, no previous comment
                pass
            elif prev_node.type == "comment":
                # We have a previous comment if it ends on the previous
                # line then we set the docstring. We also need to check
                # if the first line of the comment is the same as a
                # previous property.
                if get_row(prop.start_point) - get_row(prev_node.end_point) <= 1:
                    ds = process_text_into_docstring(prev_node.text, self.encoding)
                    prev_prop = prev_node.prev_named_sibling
                    if prev_prop is not None and prev_prop.type == "property":
                        if get_row(prev_node.start_point) == get_row(
                            prev_prop.end_point
                        ):
                            ds = "\n".join(ds.split("\n")[1:])

                    if ds:
                        docstring = ds
                else:
                    if get_row(prop.start_point) - get_row(prev_node.end_point) <= 1:
                        docstring = process_text_into_docstring(
                            prev_node.text, self.encoding
                        )
            elif prev_node.type == "property":
                # The previous property node may have eaten our comment
                # check for it a trailing comment. If it is not there
                # then we stop looking.
                prev_comment = prev_node.named_children[-1]
                if prev_comment.type == "comment":
                    # we now need to check if prev_comment ends on the line
                    # before ours and trim the first line if it on the same
                    # line as prev property.
                    if get_row(prop.start_point) - get_row(prev_comment.end_point) <= 1:
                        ds = process_text_into_docstring(
                            prev_comment.text, self.encoding
                        )
                        if get_row(prev_comment.start_point) == get_row(
                            prev_comment.prev_named_sibling.end_point
                        ):
                            ds = "\n".join(ds.split("\n")[1:])
                        if ds:
                            docstring = ds
            # After all that if our docstring is empty then we have none
            if not docstring.strip():
                docstring = None
            else:
                pass  # docstring = docstring.rstrip()

            self.properties[name] = {
                "attrs": attrs,
                "size": dims,
                "type": typename,
                "validators": vfs,
                "default": default,
                "docstring": docstring,
            }

    def _parse_method_section(self, methods_match):
        methods = methods_match.get("methods")
        if methods is None:
            return
        attrs_nodes = methods_match.get("attrs")
        attrs = self._parse_attributes(attrs_nodes)
        for method in methods:
            is_set_get = q_get_set.matches(method)
            # Skip getter and setter
            if len(is_set_get) > 0:
                continue
            parsed_function = MatFunctionParser(method, self.encoding)
            self.methods[parsed_function.name] = parsed_function
            self.methods[parsed_function.name].attrs = attrs

    def _parse_enum_section(self, enums_match):
        enums = enums_match.get("enums")
        if enums is None:
            return
        for enum in enums:
            _, enum_match = q_enum.matches(enum)[0]
            name = enum_match.get("name").text.decode(
                self.encoding, errors="backslashreplace"
            )
            arg_nodes = enum_match.get("args")
            if arg_nodes is not None:
                args = [
                    arg.text.decode(self.encoding, errors="backslashreplace")
                    for arg in arg_nodes
                ]
            else:
                args = None

            docstring = ""
            # look forward for docstring
            next_node = enum.next_named_sibling
            if next_node is not None and next_node.type == "comment":
                if get_row(next_node.start_point) == get_row(enum.end_point):
                    # if the docstring is on the same line as the end of the definition only take the inline part
                    docstring = process_text_into_docstring(
                        next_node.text, self.encoding
                    )
                    docstring = docstring.split("\n")[0]
                elif get_row(next_node.start_point) - get_row(enum.end_point) <= 1:
                    # Otherwise take the whole docstring
                    docstring = process_text_into_docstring(
                        next_node.text, self.encoding
                    )

            # override docstring with prior if exists
            prev_node = enum.prev_named_sibling
            if prev_node is None:
                # Nothing we can do, no previous comment
                pass
            elif prev_node.type == "comment":
                # We have a previous comment if it ends on the previous
                # line then we set the docstring. We also need to check
                # if the first line of the comment is the same as a
                # previous enum.
                if get_row(enum.start_point) - get_row(prev_node.end_point) <= 1:
                    ds = process_text_into_docstring(prev_node.text, self.encoding)
                    prev_enum = prev_node.prev_named_sibling
                    if prev_enum is not None and prev_enum.type == "enum":
                        if get_row(prev_node.start_point) == get_row(
                            prev_enum.end_point
                        ):
                            ds = "\n".join(ds.split("\n")[1:])
                    if ds:
                        docstring = ds
                else:
                    if get_row(enum.start_point) - get_row(prev_node.end_point) <= 1:
                        docstring = process_text_into_docstring(
                            prev_node.text, self.encoding
                        )
            # After all that if our docstring is empty then we have none
            if docstring.strip() == "":
                docstring == None
            else:
                pass  # docstring = docstring.rstrip()

            self.enumerations[name] = {"args": args, "docstring": docstring}

    def _parse_event_section(self, events_match):
        attrs_nodes = events_match.get("attrs")
        attrs = self._parse_attributes(attrs_nodes)
        events = events_match.get("events")
        if events is None:
            return
        for event in events:
            name = event.text.decode(self.encoding, errors="backslashreplace")

            docstring = ""
            # look forward for docstring
            next_node = event.next_named_sibling
            if next_node is not None and next_node.type == "comment":
                if get_row(next_node.start_point) == get_row(event.end_point):
                    # if the docstring is on the same line as the end of the definition only take the inline part
                    docstring = process_text_into_docstring(
                        next_node.text, self.encoding
                    )
                    docstring = docstring.split("\n")[0]
                elif get_row(next_node.start_point) - get_row(event.end_point) <= 1:
                    # Otherwise take the whole docstring
                    docstring = process_text_into_docstring(
                        next_node.text, self.encoding
                    )

            # override docstring with prior if exists
            prev_node = event.prev_named_sibling
            if prev_node is None:
                # Nothing we can do, no previous comment
                pass
            elif prev_node.type == "comment":
                # We have a previous comment if it ends on the previous
                # line then we set the docstring. We also need to check
                # if the first line of the comment is the same as a
                # previous event.
                if get_row(event.start_point) - get_row(prev_node.end_point) <= 1:
                    ds = process_text_into_docstring(prev_node.text, self.encoding)
                    prev_event = prev_node.prev_named_sibling
                    if prev_event is not None and prev_event.type == "identifier":
                        if get_row(prev_node.start_point) == get_row(
                            prev_event.end_point
                        ):
                            ds = "\n".join(ds.split("\n")[1:])
                    if ds:
                        docstring = ds
                else:
                    if get_row(event.start_point) - get_row(prev_node.end_point) <= 1:
                        docstring = process_text_into_docstring(
                            prev_node.text, self.encoding
                        )
            # After all that if our docstring is empty then we have none
            if docstring.strip() == "":
                docstring == None
            else:
                pass  # docstring = docstring.rstrip()

            self.events[name] = {"attrs": attrs, "docstring": docstring}

    def _parse_attributes(self, attrs_nodes):
        attrs = {}
        if attrs_nodes is not None:
            for attr_node in attrs_nodes:
                _, attr_match = q_attributes.matches(attr_node)[0]
                name = attr_match.get("name").text.decode(
                    self.encoding, errors="backslashreplace"
                )
                value_node = attr_match.get("value")
                rhs_node = attr_match.get("rhs")
                if rhs_node is not None:
                    if rhs_node.type == "cell":
                        attrs[name] = [
                            vn.text.decode(self.encoding, errors="backslashreplace")
                            for vn in value_node
                        ]
                    else:
                        attrs[name] = value_node[0].text.decode(
                            self.encoding, errors="backslashreplace"
                        )
                else:
                    attrs[name] = MATLAB_ATTRIBUTE_DEFAULTS.get(name)

        return attrs
