import tree_sitter_matlab as tsml
from tree_sitter import Language, Parser
import re

# rpath = "../../../syscop/software/nosnoc/+nosnoc/Options.m"

ML_LANG = Language(tsml.language())

rpath = "/home/anton/tools/matlabdomain/tests/test_data/ClassTesting.m"

# QUERIES
q_classdef = ML_LANG.query(
    """(class_definition
    "classdef"
    (attributes
    [(attribute) @attrs _]+
    )?
    (identifier) @name
    (superclasses
        [(property_name) @supers _]+
    )?
    ) @class
"""
)

q_attributes = ML_LANG.query("""(identifier) @name (_)? @value""")

q_supers = ML_LANG.query("""[(identifier) @secs "."]+ """)

q_properties = ML_LANG.query(
    """(properties
    (attributes)? @attrs
    (property)* @properties
    ) @prop_block
"""
)

q_methods = ML_LANG.query(
    """(methods
    (attributes)? @attrs
    (function_definition)* @methods
    ) @meth_block
"""
)

q_enumerations = ML_LANG.query(
    """(enumeration
    (enum)* @enums
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


def find_first_child(curr, tok, attr="children"):
    tok_lst = getattr(curr, attr)
    ind = [i for i in range(len(tok_lst)) if tok_lst[i].token == tok]
    if not ind:
        return (None, None)
    return (tok_lst[ind[0]], ind[0])


def _toks_on_same_line(tok1, tok2):
    """Note: pass the tokens in order they appear in case of multiline tokens, otherwise this may return incorrect results"""
    line1 = _get_last_line_of_tok(tok1)
    line2 = _get_first_line_of_tok(tok2)
    return line1 == line2


def _is_empty_line_between_tok(tok1, tok2):
    """Note: pass tokens in order they appear"""
    line1 = _get_last_line_of_tok(tok1)
    line2 = _get_first_line_of_tok(tok2)
    return line2 - line1 > 1


def _get_first_line_of_tok(tok):
    return min([loc[0] for loc in tok.characters.keys()])


def _get_last_line_of_tok(tok):
    return max([loc[0] for loc in tok.characters.keys()])


class MatFunctionParser:
    def __init__(self, fun_tok):
        """Parse Function definition"""
        # First find the function name
        name_gen = fun_tok.find(tokens="entity.name.function.matlab")
        try:
            name_tok, _ = next(name_gen)
            self.name = name_tok.content
        except StopIteration:
            # TODO correct error here
            raise Exception("Couldn't find function name")

        # Find outputs and parameters
        output_gen = fun_tok.find(tokens="variable.parameter.output.matlab")
        param_gen = fun_tok.find(tokens="variable.parameter.input.matlab")

        self.outputs = {}
        self.params = {}
        self.attrs = {}

        for out, _ in output_gen:
            self.outputs[out.content] = {}

        for param, _ in param_gen:
            self.params[param.content] = {}

        # find arguments blocks
        arg_section = None
        for arg_section, _ in fun_tok.find(tokens="meta.arguments.matlab"):
            self._parse_argument_section(arg_section)

        fun_decl_gen = fun_tok.find(tokens="meta.function.declaration.matlab")
        try:
            fun_decl_tok, _ = next(fun_decl_gen)
        except StopIteration:
            raise Exception(
                "missing function declaration"
            )  # This cant happen as we'd be missing a function name

        # Now parse for docstring
        docstring = ""
        comment_toks = fun_tok.findall(
            tokens=["comment.line.percentage.matlab", "comment.block.percentage.matlab"]
        )
        last_tok = arg_section if arg_section is not None else fun_decl_tok

        for comment_tok, _ in comment_toks:
            if _is_empty_line_between_tok(last_tok, comment_tok):
                # If we have non-consecutive tokens quit right away.
                break
            elif (
                not docstring and comment_tok.token == "comment.block.percentage.matlab"
            ):
                # If we have no previous docstring lines and a comment block we take
                # the comment block as the docstring and exit.
                docstring = comment_tok.content.strip()[
                    2:-2
                ].strip()  # [2,-2] strips out block comment delimiters
                break
            elif comment_tok.token == "comment.line.percentage.matlab":
                # keep parsing comments
                docstring += comment_tok.content[1:] + "\n"
            else:
                # we are done.
                break
            last_tok = comment_tok

        self.docstring = docstring if docstring else None

    def _parse_argument_section(self, section):
        modifiers = [
            mod.content
            for mod, _ in section.find(tokens="storage.modifier.arguments.matlab")
        ]
        arg_def_gen = section.find(tokens="meta.assignment.definition.property.matlab")
        for arg_def, _ in arg_def_gen:
            arg_name = arg_def.begin[
                0
            ].content  # Get argument name that is being defined
            self._parse_argument_validation(arg_name, arg_def, modifiers)

    def _parse_argument_validation(self, arg_name, arg, modifiers):
        # TODO This should be identical to propery validation I think. Refactor
        # First get the size if found
        section = self.output if "Output" in modifiers else self.params
        size_gen = arg.find(tokens="meta.parens.size.matlab", depth=1)
        try:  # We have a size, therefore parse the comma separated list into tuple
            size_tok, _ = next(size_gen)
            size_elem_gen = size_tok.find(
                tokens=[
                    "constant.numeric.decimal.matlab",
                    "keyword.operator.vector.colon.matlab",
                ],
                depth=1,
            )
            size = tuple([elem[0].content for elem in size_elem_gen])
            section[arg_name]["size"] = size
        except StopIteration:
            pass

        # Now find the type if it exists
        # TODO this should be mapped to known types (though perhaps as a postprocess)
        type_gen = arg.find(tokens="storage.type.matlab", depth=1)
        try:
            section[arg_name]["type"] = next(type_gen)[0].content
        except StopIteration:
            pass

        # Now find list of validators
        validator_gen = arg.find(tokens="meta.block.validation.matlab", depth=1)
        try:
            validator_tok, _ = next(validator_gen)
            validator_toks = validator_tok.findall(
                tokens="variable.other.readwrite.matlab", depth=1
            )  # TODO Probably bug here in MATLAB-Language-grammar
            section[arg_name]["validators"] = [tok[0].content for tok in validator_toks]
        except StopIteration:
            pass


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

        import pdb

        pdb.set_trace()
        # Parse class attrs and supers
        attrs_node = class_match.get("attrs")
        if attrs_node is not None:
            attrs_matches = q_attributes.matches(attrs_node)
            for _, match in attrs_matches:
                name = match.get("name").text.decode("utf-8")
                value_node = match.get("value")
                self.attrs[name] = (
                    value_node.text.decode("utf-8") if value_node is not None else None
                )

        supers_node = class_match.get("supers")
        if supers_node is not None:
            supers_matches = q_supers.matches(supers_node)
            for _, match in supers_matches:
                super_cls = tuple(
                    [sec.text.decode("utf-8") for sec in match.get("secs")]
                )
                self.supers.append(super_cls)

        prop_matches = q_properties.matches(self.cls)
        method_matches = q_methods.matches(self.cls)
        enumeration_matches = q_enumerations.matches(self.cls)
        events_matches = q_events.matches(self.cls)

        self._parse_clsdef()
        self._find_class_docstring()

        property_sections = self.cls.findall(tokens="meta.properties.matlab", depth=1)
        method_sections = self.cls.findall(tokens="meta.methods.matlab", depth=1)
        enumeration_sections = self.cls.findall(tokens="meta.enum.matlab", depth=1)

        for section, _ in property_sections:
            self._parse_property_section(section)

        for section, _ in method_sections:
            self._parse_method_section(section)

        for section, _ in enumeration_sections:
            self._parse_enum_section(section)

    def _find_class_docstring(self):
        try:
            possible_comment_tok = self.cls.children[1]
        except IndexError:
            return

        if possible_comment_tok.token == "comment.line.percentage.matlab":
            self._docstring_lines()
        elif possible_comment_tok.token == "comment.block.percentage.matlab":
            self.docstring = possible_comment_tok.content.strip()[
                2:-2
            ].strip()  # [2,-2] strips out block comment delimiters
        else:
            pass

    def _docstring_lines(self):
        idx = 1
        cls_children = self.cls.children

        while (
            idx < len(cls_children)
            and cls_children[idx].token == "comment.line.percentage.matlab"
        ):
            self.docstring += (
                cls_children[idx].content[1:] + "\n"
            )  # [1:] strips out percent sign
            idx += 1
        self.docstring = self.docstring.strip()

    def _parse_clsdef(self):
        # Try parsing attrs
        attrs_tok_gen = self.clsdef.find(tokens="storage.modifier.section.class.matlab")
        try:
            attrs_tok, _ = next(attrs_tok_gen)
            self._parse_class_attributes(attrs_tok)
        except StopIteration:
            pass

        # Parse classname
        classname_tok_gen = self.clsdef.find(tokens="entity.name.type.class.matlab")
        try:
            classname_tok, _ = next(classname_tok_gen)
            self.name = classname_tok.content
        except StopIteration:
            print("ClassName not found")  # TODO this is probably fatal

        # Parse interited classes
        parent_class_toks = self.clsdef.findall(tokens="meta.inherited-class.matlab")

        for parent_class_tok, _ in parent_class_toks:
            sections = parent_class_tok.findall(
                tokens=[
                    "entity.name.namespace.matlab",
                    "entity.other.inherited-class.matlab",
                ]
            )
            super_cls = tuple([sec.content for sec, _ in sections])
            self.supers.append(super_cls)
        # Parse Attributes TODO maybe there is a smarter way to do this?
        idx = 0
        while self.clsdef.children[idx].token == "storage.modifier.class.matlab":
            attr_tok = self.clsdef.children[idx]
            attr = attr_tok.content
            val = None  # TODO maybe do some typechecking here or we can assume that you give us valid Matlab
            idx += 1
            if attr_tok.token == "keyword.operator.assignment.matlab":  # pull out r.h.s
                idx += 1
                val = self.clsdef.children[idx].content
                idx += 1
            if (
                attr_tok.token == "punctuation.separator.modifier.comma.matlab"
            ):  # skip commas
                idx += 1
            self.attrs[attr] = val

    def _parse_class_attributes(self, attrs_tok):
        # walk down child list and parse manually
        # TODO perhaps contribute a delimited list find to textmate-grammar-python
        children = attrs_tok.children
        idx = 0
        while idx < len(children):
            child_tok = children[idx]
            if child_tok.token == "storage.modifier.class.matlab":
                attr = child_tok.content
                val = None
                idx += 1  # walk to next token
                try:  # however we may have walked off the end of the list in which case we exit
                    maybe_assign_tok = children[idx]
                except:
                    self.attrs[attr] = val
                    break
                if maybe_assign_tok.token == "keyword.operator.assignment.matlab":
                    idx += 1
                    rhs_tok = children[idx]  # parse right hand side
                    if rhs_tok.token == "meta.cell.literal.matlab":
                        # A cell. For now just take the whole cell as value.
                        # TODO parse out the cell array of metaclass literals.
                        val = "{" + rhs_tok.content + "}"
                        idx += 1
                    elif rhs_tok.token == "constant.language.boolean.matlab":
                        val = rhs_tok.content
                        idx += 1
                    elif rhs_tok.token == "keyword.operator.other.question.matlab":
                        idx += 1
                        metaclass_tok = children[idx]
                        metaclass_components = metaclass_tok.findall(
                            tokens=[
                                "entity.name.namespace.matlab",
                                "entity.other.class.matlab",
                            ]
                        )
                        val = tuple([comp.content for comp, _ in metaclass_components])
                    else:
                        pass
                self.attrs[attr] = val
            else:  # Comma or continuation therefore skip
                idx += 1

    def _parse_property_section(self, section):
        # TODO parse property section attrs
        attrs = self._parse_attributes(section)
        idxs = [
            i
            for i in range(len(section.children))
            if section.children[i].token == "meta.assignment.definition.property.matlab"
        ]
        for idx in idxs:
            prop_tok = section.children[idx]
            prop_name = prop_tok.begin[0].content
            self.properties[prop_name] = {"attrs": attrs}  # Create entry for property
            self._parse_property_validation(
                prop_name, prop_tok
            )  # Parse property validation.

            # Try to find a default assignment:
            default = None
            _, assgn_idx = find_first_child(
                prop_tok, "keyword.operator.assignment.matlab", attr="end"
            )
            if assgn_idx is not None:
                default = ""
                assgn_idx += 1  # skip assignment
                while assgn_idx < len(prop_tok.end):
                    tok = prop_tok.end[assgn_idx]
                    assgn_idx += 1
                    if tok.token in [
                        "comment.line.percentage.matlab",
                        "punctuation.terminator.semicolon.matlab",
                    ]:
                        break
                    default += tok.content
            self.properties[prop_name]["default"] = default

            # Get inline docstring
            inline_docstring_gen = prop_tok.find(
                tokens="comment.line.percentage.matlab", attribute="end"
            )
            try:
                inline_docstring_tok, _ = next(inline_docstring_gen)
                inline_docstring = inline_docstring_tok.content[
                    1:
                ]  # strip leading % sign
            except StopIteration:
                inline_docstring = None

            # Walk backwards to get preceding docstring.
            preceding_docstring = ""
            walk_back_idx = idx - 1
            next_tok = prop_tok
            while walk_back_idx >= 0:
                walk_tok = section.children[walk_back_idx]
                if _is_empty_line_between_tok(walk_tok, next_tok):
                    # Once there is an empty line between consecutive tokens we are done.
                    break

                if (
                    not preceding_docstring
                    and walk_tok.token == "comment.block.percentage.matlab"
                ):
                    # block comment immediately preceding enum so we are done.
                    # TODO we might need to do some postprocessing here to handle indents gracefully
                    preceding_docstring = walk_tok.content.strip()[2:-2]
                    break
                elif walk_tok.token == "comment.line.percentage.matlab":
                    preceding_docstring = (
                        walk_tok.content[1:] + "\n" + preceding_docstring
                    )  # [1:] strips %
                    walk_back_idx -= 1
                    next_tok = walk_tok
                elif walk_tok.token == "punctuation.whitespace.comment.leading.matlab":
                    walk_back_idx -= 1
                    # Dont update next_tok for whitespace
                else:
                    break

            # Walk forwards to get following docstring or inline one.
            following_docstring = ""
            walk_fwd_idx = idx + 1
            prev_tok = prop_tok
            while walk_fwd_idx < len(section.children):
                walk_tok = section.children[walk_fwd_idx]

                if _is_empty_line_between_tok(prev_tok, walk_tok):
                    # Once there is an empty line between consecutive tokens we are done.
                    break

                if (
                    not following_docstring
                    and walk_tok.token == "comment.block.percentage.matlab"
                ):
                    # block comment immediately following enum so we are done.
                    # TODO we might need to do some postprocessing here to handle indents gracefully
                    following_docstring = walk_tok.content.strip()[2:-2]
                    break
                elif walk_tok.token == "comment.line.percentage.matlab":
                    following_docstring = (
                        following_docstring + "\n" + walk_tok.content[1:]
                    )  # [1:] strips %
                    walk_fwd_idx += 1
                    prev_tok = walk_tok
                elif walk_tok.token == "punctuation.whitespace.comment.leading.matlab":
                    walk_fwd_idx += 1
                    # Dont update prev_tok for whitespace
                else:
                    break

            if preceding_docstring:
                self.properties[prop_name]["docstring"] = preceding_docstring.strip()
            elif inline_docstring:
                self.properties[prop_name]["docstring"] = inline_docstring.strip()
            elif following_docstring:
                self.properties[prop_name]["docstring"] = following_docstring.strip()
            else:
                self.properties[prop_name]["docstring"] = None

    def _parse_property_validation(self, prop_name, prop):
        """Parses property validation syntax"""
        # First get the szize if found
        size_gen = prop.find(tokens="meta.parens.size.matlab", depth=1)
        try:  # We have a size, therefore parse the comma separated list into tuple
            size_tok, _ = next(size_gen)
            size_elem_gen = size_tok.find(
                tokens=[
                    "constant.numeric.decimal.matlab",
                    "keyword.operator.vector.colon.matlab",
                ],
                depth=1,
            )
            size = tuple([elem[0].content for elem in size_elem_gen])
            self.properties[prop_name]["size"] = size
        except StopIteration:
            pass

        # Now find the type if it exists
        # TODO this should be mapped to known types (though perhaps as a postprocess)
        type_gen = prop.find(tokens="storage.type.matlab", depth=1)
        try:
            self.properties[prop_name]["type"] = next(type_gen)[0].content
        except StopIteration:
            pass

        # Now find list of validators
        validator_gen = prop.find(tokens="meta.block.validation.matlab", depth=1)
        try:
            validator_tok, _ = next(validator_gen)
            validator_toks = validator_tok.findall(
                tokens=[
                    "variable.other.readwrite.matlab",
                    "meta.function-call.parens.matlab",
                ],
                depth=1,
            )  # TODO Probably bug here in MATLAB-Language-grammar
            self.properties[prop_name]["validators"] = [
                tok[0].content for tok in validator_toks
            ]
        except StopIteration:
            pass

    def _parse_method_section(self, section):
        attrs = self._parse_attributes(section)
        idxs = [
            i
            for i in range(len(section.children))
            if section.children[i].token == "meta.function.matlab"
        ]
        for idx in idxs:
            meth_tok = section.children[idx]
            parsed_function = MatFunctionParser(meth_tok)
            self.methods[parsed_function.name] = parsed_function
            self.methods[parsed_function.name].attrs = attrs

    def _parse_enum_section(self, section):
        idxs = [
            i
            for i in range(len(section.children))
            if section.children[i].token
            == "meta.assignment.definition.enummember.matlab"
        ]
        for idx in idxs:
            enum_tok = section.children[idx]
            next_idx = idx
            enum_name = enum_tok.children[0].content
            self.enumerations[enum_name] = {}
            if (
                idx + 1 < len(section.children)
                and section.children[idx + 1].token == "meta.parens.matlab"
            ):  # Parse out args TODO this should be part of enummember assignment definition
                args = tuple(
                    [
                        arg.content
                        for arg in section.children[idx + 1].children
                        if arg.token != "punctuation.separator.comma.matlab"
                    ]
                )
                self.enumerations[enum_name]["args"] = args
                next_idx += 1

            # Walk backwards to get preceding docstring.
            preceding_docstring = ""
            walk_back_idx = idx - 1
            next_tok = enum_tok
            while walk_back_idx >= 0:
                walk_tok = section.children[walk_back_idx]
                if _is_empty_line_between_tok(walk_tok, next_tok):
                    # Once there is an empty line between consecutive tokens we are done.
                    break

                if (
                    not preceding_docstring
                    and walk_tok.token == "comment.block.percentage.matlab"
                ):
                    # block comment immediately preceding enum so we are done.
                    # TODO we might need to do some postprocessing here to handle indents gracefully
                    preceding_docstring = walk_tok.content.strip()[2:-2]
                    break
                elif walk_tok.token == "comment.line.percentage.matlab":
                    preceding_docstring = (
                        walk_tok.content[1:] + "\n" + preceding_docstring
                    )  # [1:] strips %
                    walk_back_idx -= 1
                    next_tok = walk_tok
                elif walk_tok.token == "punctuation.whitespace.comment.leading.matlab":
                    walk_back_idx -= 1
                    # Dont update next_tok for whitespace
                else:
                    break

            # Walk forwards to get following docstring or inline one.
            inline_docstring = ""
            following_docstring = ""
            walk_fwd_idx = next_idx + 1
            prev_tok = section.children[next_idx]
            while walk_fwd_idx < len(section.children):
                walk_tok = section.children[walk_fwd_idx]

                if _is_empty_line_between_tok(prev_tok, walk_tok):
                    # Once there is an empty line between consecutive tokens we are done.
                    break

                if (
                    not following_docstring
                    and walk_tok.token == "comment.block.percentage.matlab"
                ):
                    # block comment immediately following enum so we are done.
                    # TODO we might need to do some postprocessing here to handle indents gracefully
                    following_docstring = walk_tok.content.strip()[2:-2]
                    break
                elif walk_tok.token == "comment.line.percentage.matlab":
                    # In the case the comment is on the same line as the end of the enum declaration, take it as inline comment and exit.
                    if _toks_on_same_line(section.children[idx], walk_tok):
                        inline_docstring = walk_tok.content[1:]
                        break

                    following_docstring = (
                        following_docstring + "\n" + walk_tok.content[1:]
                    )  # [1:] strips %
                    walk_fwd_idx += 1
                    prev_tok = walk_tok
                elif walk_tok.token == "punctuation.whitespace.comment.leading.matlab":
                    walk_fwd_idx += 1
                    # Dont update prev_tok for whitespace
                else:
                    break

            if preceding_docstring:
                self.enumerations[enum_name]["docstring"] = preceding_docstring.strip()
            elif inline_docstring:
                self.enumerations[enum_name]["docstring"] = inline_docstring.strip()
            elif following_docstring:
                self.enumerations[enum_name]["docstring"] = following_docstring.strip()
            else:
                self.enumerations[enum_name]["docstring"] = None

    def _parse_attributes(self, section):
        # walk down child list and parse manually
        children = section.begin
        idx = 1
        attrs = {}
        while idx < len(children):
            child_tok = children[idx]
            if re.match(
                "storage.modifier.(properties|methods|events).matlab", child_tok.token
            ):
                attr = child_tok.content
                val = None
                idx += 1  # walk to next token
                try:  # however we may have walked off the end of the list in which case we exit
                    maybe_assign_tok = children[idx]
                except:
                    attrs[attr] = val
                    return attrs
                if maybe_assign_tok.token == "keyword.operator.assignment.matlab":
                    idx += 1
                    rhs_tok = children[idx]  # parse right hand side
                    if rhs_tok.token == "meta.cell.literal.matlab":
                        # A cell. For now just take the whole cell as value.
                        # TODO parse out the cell array of metaclass literals.
                        val = "{" + rhs_tok.content + "}"
                        idx += 1
                    elif rhs_tok.token == "constant.language.boolean.matlab":
                        val = rhs_tok.content
                        idx += 1
                    elif rhs_tok.token == "storage.modifier.access.matlab":
                        val = rhs_tok.content
                        idx += 1
                    elif rhs_tok.token == "keyword.operator.other.question.matlab":
                        idx += 1
                        metaclass_tok = children[idx]
                        metaclass_components = metaclass_tok.findall(
                            tokens=[
                                "entity.name.namespace.matlab",
                                "entity.other.class.matlab",
                            ]
                        )
                        val = tuple([comp.content for comp, _ in metaclass_components])
                    else:
                        pass
                attrs[attr] = val
            else:  # Comma or continuation therefore skip
                idx += 1

        return attrs


if __name__ == "__main__":
    parser = Parser(ML_LANG)

    with open(rpath, "rb") as f:
        data = f.read()

    tree = parser.parse(data)
    class_parser = MatClassParser(tree)
    import pdb

    pdb.set_trace()
