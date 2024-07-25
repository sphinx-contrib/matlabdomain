import tree_sitter_matlab as tsml
from tree_sitter import Language, Parser
import re

# rpath = "../../../syscop/software/nosnoc/+nosnoc/Options.m"

ML_LANG = Language(tsml.language())

rpath = "/home/anton/tools/matlabdomain/tests/test_data/ClassTesting.m"

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

q_attributes = ML_LANG.query("""(attribute (identifier) @name (_)? @value)""")

q_supers = ML_LANG.query("""[(identifier) @secs "."]+ """)

q_properties = ML_LANG.query(
    """(properties
    .
    (attributes
        [(attribute) @attrs _]+
    )?
    [(property) @properties _]*
    ) @prop_block
"""
)

q_methods = ML_LANG.query(
    """(methods
    (attributes
        [(attribute) @attrs _]+
    )?
    [(function_definition) @methods _]*
    ) @meth_block
"""
)

q_enumerations = ML_LANG.query(
    """(enumeration
    [(enum) @enums _]*
    ) @enum_block
"""
)

q_events = ML_LANG.query(
    """(events
    (attributes)? @attrs
    (identifier)* @events
    ) @event_block
"""
)

q_property = ML_LANG.query(
    """
    (property name: (identifier) @name
     (dimensions
         [[(spread_operator) (number)] @dims _]+
     )?
     (identifier)? @type
     (validation_functions
         [[(identifier) (function_call)] @validation_functions _]+
     )?
     (default_value (number))? @default
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
    .
    (function_output
        [
            (identifier) @outputs
            (multioutput_variable
                [(identifier) @outputs _]+
            )
        ]
    )?
    .
    name: (identifier) @name
    .
    (function_arguments
        [(identifier) @params _]*
    )?
    .
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
        [(attribute) @attrs _]+
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
         [[(spread_operator) (number)] @dims _]+
     )?
     (identifier)? @type
     (validation_functions
         [[(identifier) (function_call)] @validation_functions _]+
     )?
     (default_value (number))? @default
     (comment)? @docstring
    )
"""
)


re_percent_remove = re.compile(r"^[ \t]*%", flags=re.M)


def process_text_into_docstring(text):
    docstring = text.decode("utf-8")
    return re.sub(re_percent_remove, "", docstring)


class MatFunctionParser:
    def __init__(self, fun_node):
        """Parse Function definition"""
        _, fun_match = q_fun.matches(fun_node)[0]
        self.name = fun_match.get("name").text.decode("utf-8")

        # Get outputs (possibly more than one)
        self.outputs = {}
        output_nodes = fun_match.get("outputs")
        if output_nodes is not None:
            outputs = [output.text.decode("utf-8") for output in output_nodes]
            for output in outputs:
                self.outputs[output] = {}

        # Get parameters
        self.params = {}
        param_nodes = fun_match.get("params")
        if output_nodes is not None:
            params = [param.text.decode("utf-8") for param in param_nodes]
            for param in params:
                self.params[param] = {}

        # parse out info from argument blocks
        argblock_nodes = fun_match.get("argblocks")
        for argblock_node in argblock_nodes:
            self._parse_argument_section(argblock_node)

        #
        import pdb

        pdb.set_trace()

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
            name = [name.text.decode("utf-8") for name in arg_match.get("name")]

            # extract dims list
            dims_list = arg_match.get("dims")
            dims = None
            if dims_list is not None:
                dims = tuple([dim.text.decode("utf-8") for dim in dims_list])

            # extract type
            type_node = arg_match.get("type")
            typename = type_node.text.decode("utf-8") if type_node is not None else None

            # extract validator functions
            vf_list = arg_match.get("validator_functions")
            vfs = None
            if vf_list is not None:
                vfs = [vf.text.decode("utf-8") for vf in vf_list]

            # extract default
            default_node = arg_match.get("default")
            default = (
                default_node.text.decode("utf-8") if default_node is not None else None
            )

            # extract inline or following docstring if there is no semicolon
            docstring_node = arg_match.get("docstring")
            docstring = ""
            if docstring_node is not None:
                # tree-sitter-matlab combines inline comments with following
                # comments which means this requires some relatively ugly
                # processing, but worth it for the ease of the rest of it.
                prev_sib = docstring_node.prev_named_sibling
                if docstring_node.start_point.row == prev_sib.end_point.row:
                    # if the docstring is on the same line as the end of the definition only take the inline part
                    docstring = process_text_into_docstring(docstring_node.text)
                    docstring = docstring.split("\n")[0]
                elif docstring_node.start_point.row - prev_sib.end_point.row <= 1:
                    # Otherwise take the whole docstring
                    docstring = process_text_into_docstring(docstring_node.text)

            # extract inline or following docstring if there _is_ a semicolon.
            # this is only done if we didn't already find a docstring with the previous approach
            next_node = arg.next_named_sibling
            if next_node is None or docstring is not None:
                # Nothing to be done.
                pass
            elif next_node.type == "comment":
                if next_node.start_point.row == arg.end_point.row:
                    # if the docstring is on the same line as the end of the definition only take the inline part
                    docstring = process_text_into_docstring(next_node.text)
                    docstring = docstring.split("\n")[0]
                elif next_node.start_point.row - arg.end_point.row <= 1:
                    # Otherwise take the whole docstring
                    docstring = process_text_into_docstring(next_node.text)

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
                if arg.start_point.row - prev_node.end_point.row <= 1:
                    ds = process_text_into_docstring(prev_node.text)
                    prev_arg = prev_node.prev_named_sibling
                    if prev_arg is not None and prev_arg.type == "property":
                        if prev_node.start_point.row == prev_arg.end_point.row:
                            ds = "\n".join(ds.split("\n")[1:])
                    if ds:
                        docstring = ds
                else:
                    if arg.start_point.row - prev_node.end_point.row <= 1:
                        docstring = process_text_into_docstring(prev_node.text)
            elif prev_node.type == "property":
                # The previous argumentnode may have eaten our comment
                # check for it a trailing comment. If it is not there
                # then we stop looking.
                prev_comment = prev_node.named_children[-1]
                if prev_comment.type == "comment":
                    # we now need to check if prev_comment ends on the line
                    # before ours and trim the first line if it on the same
                    # line as prev property.
                    if arg.start_point.row - prev_comment.end_point.row <= 1:
                        ds = process_text_into_docstring(prev_comment.text)
                        if (
                            prev_comment.start_point.row
                            == prev_comment.prev_named_sibling.end_point.row
                        ):
                            ds = "\n".join(ds.split("\n")[1:])
                        if ds:
                            docstring = ds
            # After all that if our docstring is empty then we have none
            if docstring.strip() == "":
                docstring == None

            # Here we trust that the person is giving us valid matlab.
            if "Output" in attrs.keys():
                arg_loc = self.outputs
            else:
                arg_loc = self.params
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
        # TOOD deduplicated this
        attrs = {}
        if attrs_nodes is not None:
            for attr_node in attrs_nodes:
                _, attr_match = q_attributes.matches(attr_node)[0]
                name = attr_match.get("name").text.decode("utf-8")
                value_node = attr_match.get("value")
                attrs[name] = (
                    value_node.text.decode("utf-8") if value_node is not None else None
                )
        return attrs


class MatClassParser:
    def __init__(self, tree):
        # DATA
        self.name = ""
        self.supers = []
        self.attrs = {}
        self.docstring = ""
        self.properties = {}
        self.methods = {}
        self.enumerations = {}

        self.tree = tree

        # Parse class basics
        class_matches = q_classdef.matches(tree.root_node)
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
                super_cls = tuple(
                    [sec.text.decode("utf-8") for sec in super_match.get("secs")]
                )
                self.supers.append(super_cls)

        # get docstring and check that it consecutive
        docstring_node = class_match.get("docstring")
        if docstring_node is not None:
            prev_node = docstring_node.prev_sibling
            if docstring_node.start_point.row - prev_node.end_point.row <= 1:
                self.docstring = process_text_into_docstring(docstring_node.text)

        prop_matches = q_properties.matches(self.cls)
        method_matches = q_methods.matches(self.cls)
        enum_matches = q_enumerations.matches(self.cls)
        events_matches = q_events.matches(self.cls)

        for _, prop_match in prop_matches:
            self._parse_property_section(prop_match)
        for _, enum_match in enum_matches:
            self._parse_enum_section(enum_match)
        for _, method_match in method_matches:
            self._parse_method_section(method_match)
        import pdb

        pdb.set_trace()

    def _parse_property_section(self, props_match):
        # extract property section attributes
        attrs_nodes = props_match.get("attrs")
        attrs = self._parse_attributes(attrs_nodes)

        properties = props_match.get("properties")

        for prop in properties:
            # match property to extract details
            _, prop_match = q_property.matches(prop)[0]

            # extract name (this is always available so no need for None check)
            name = prop_match.get("name").text.decode("utf-8")

            # extract dims list
            dims_list = prop_match.get("dims")
            dims = None
            if dims_list is not None:
                dims = tuple([dim.text.decode("utf-8") for dim in dims_list])

            # extract type
            type_node = prop_match.get("type")
            typename = type_node.text.decode("utf-8") if type_node is not None else None

            # extract validator functions
            vf_list = prop_match.get("validator_functions")
            vfs = None
            if vf_list is not None:
                vfs = [vf.text.decode("utf-8") for vf in vf_list]

            # extract default
            default_node = prop_match.get("default")
            default = (
                default_node.text.decode("utf-8") if default_node is not None else None
            )

            # extract inline or following docstring if there is no semicolon
            docstring_node = prop_match.get("docstring")
            docstring = ""
            if docstring_node is not None:
                # tree-sitter-matlab combines inline comments with following
                # comments which means this requires some relatively ugly
                # processing, but worth it for the ease of the rest of it.
                prev_sib = docstring_node.prev_named_sibling
                if docstring_node.start_point.row == prev_sib.end_point.row:
                    # if the docstring is on the same line as the end of the definition only take the inline part
                    docstring = process_text_into_docstring(docstring_node.text)
                    docstring = docstring.split("\n")[0]
                elif docstring_node.start_point.row - prev_sib.end_point.row <= 1:
                    # Otherwise take the whole docstring
                    docstring = process_text_into_docstring(docstring_node.text)

            # extract inline or following docstring if there _is_ a semicolon.
            # this is only done if we didn't already find a docstring with the previous approach
            next_node = prop.next_named_sibling
            if next_node is None or docstring is not None:
                # Nothing to be done.
                pass
            elif next_node.type == "comment":
                if next_node.start_point.row == prop.end_point.row:
                    # if the docstring is on the same line as the end of the definition only take the inline part
                    docstring = process_text_into_docstring(next_node.text)
                    docstring = docstring.split("\n")[0]
                elif next_node.start_point.row - prop.end_point.row <= 1:
                    # Otherwise take the whole docstring
                    docstring = process_text_into_docstring(next_node.text)

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
                if prop.start_point.row - prev_node.end_point.row <= 1:
                    ds = process_text_into_docstring(prev_node.text)
                    prev_prop = prev_node.prev_named_sibling
                    if prev_prop is not None and prev_prop.type == "property":
                        if prev_node.start_point.row == prev_prop.end_point.row:
                            ds = "\n".join(ds.split("\n")[1:])
                    if ds:
                        docstring = ds
                else:
                    if prop.start_point.row - prev_node.end_point.row <= 1:
                        docstring = process_text_into_docstring(prev_node.text)
            elif prev_node.type == "property":
                # The previous property node may have eaten our comment
                # check for it a trailing comment. If it is not there
                # then we stop looking.
                prev_comment = prev_node.named_children[-1]
                if prev_comment.type == "comment":
                    # we now need to check if prev_comment ends on the line
                    # before ours and trim the first line if it on the same
                    # line as prev property.
                    if prop.start_point.row - prev_comment.end_point.row <= 1:
                        ds = process_text_into_docstring(prev_comment.text)
                        if (
                            prev_comment.start_point.row
                            == prev_comment.prev_named_sibling.end_point.row
                        ):
                            ds = "\n".join(ds.split("\n")[1:])
                        if ds:
                            docstring = ds
            # After all that if our docstring is empty then we have none
            if docstring.strip() == "":
                docstring == None

            self.properties[name] = {
                "attrs": attrs,
                "size": dims,
                "type": typename,
                "validators": vfs,
                "default": default,
                "docstring": docstring,
            }

    def _parse_method_section(self, methods_match):
        attrs_nodes = methods_match.get("attrs")
        attrs = self._parse_attributes(attrs_nodes)
        methods = methods_match.get("methods")
        for method in methods:
            parsed_function = MatFunctionParser(method)
            self.methods[parsed_function.name] = parsed_function
            self.methods[parsed_function.name].attrs = attrs

    def _parse_enum_section(self, enums_match):
        enums = enums_match.get("enums")
        for enum in enums:
            _, enum_match = q_enum.matches(enum)[0]
            name = enum_match.get("name").text.decode("utf-8")
            arg_nodes = enum_match.get("args")
            if arg_nodes is not None:
                args = [arg.text.decode("utf-8") for arg in arg_nodes]
            else:
                args = None

            docstring = ""
            # look forward for docstring
            next_node = enum.next_named_sibling
            if next_node is not None and next_node.type == "comment":
                if next_node.start_point.row == enum.end_point.row:
                    # if the docstring is on the same line as the end of the definition only take the inline part
                    docstring = process_text_into_docstring(next_node.text)
                    docstring = docstring.split("\n")[0]
                elif next_node.start_point.row - enum.end_point.row <= 1:
                    # Otherwise take the whole docstring
                    docstring = process_text_into_docstring(next_node.text)

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
                if enum.start_point.row - prev_node.end_point.row <= 1:
                    ds = process_text_into_docstring(prev_node.text)
                    prev_enum = prev_node.prev_named_sibling
                    if prev_enum is not None and prev_enum.type == "enum":
                        if prev_node.start_point.row == prev_enum.end_point.row:
                            ds = "\n".join(ds.split("\n")[1:])
                    if ds:
                        docstring = ds
                else:
                    if enum.start_point.row - prev_node.end_point.row <= 1:
                        docstring = process_text_into_docstring(prev_node.text)
            # After all that if our docstring is empty then we have none
            if docstring.strip() == "":
                docstring == None

            self.enumerations[name] = {"args": args, "docstring": docstring}

    def _parse_attributes(self, attrs_nodes):
        attrs = {}
        if attrs_nodes is not None:
            for attr_node in attrs_nodes:
                _, attr_match = q_attributes.matches(attr_node)[0]
                name = attr_match.get("name").text.decode("utf-8")
                value_node = attr_match.get("value")
                attrs[name] = (
                    value_node.text.decode("utf-8") if value_node is not None else None
                )
        return attrs


if __name__ == "__main__":
    parser = Parser(ML_LANG)

    with open(rpath, "rb") as f:
        data = f.read()

    tree = parser.parse(data)
    class_parser = MatClassParser(tree)
    import pdb

    pdb.set_trace()
