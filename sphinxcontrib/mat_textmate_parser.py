from textmate_grammar.parsers.matlab import MatlabParser

rpath = "../../../syscop/software/nosnoc/src/CrossCompMode.m"


def find_first_child(curr, tok):
    ind = [i for i in range(len(curr.children)) if curr.children[i].token == tok]
    if not ind:
        return None
    return (curr.children[ind[0]], ind[0])

class MatClassParser():
    def __init__(self, path):
        # DATA
        self.name = ""
        self.supers = []
        self.attrs = {}
        self.docstring = ""
        self.properties = {}
        self.methods = {}
        self.enumerations = {}
        
        self.parser = MatlabParser()
        self.parsed = self.parser.parse_file(path)
        self.cls, _ = find_first_child(self.parsed, "meta.class.matlab")
        if not self.cls:
            raise Exception()  # TODO better exception
        self.clsdef, _ = find_first_child(self.cls, "meta.class.declaration.matlab")
        self._parse_clsdef()
        self._find_class_docstring()

        property_sections = self.cls.findall(tokens='meta.properties.matlab', depth=1)
        method_sections = self.cls.findall(tokens='meta.methods.matlab', depth=1)
        enumeration_sections = self.cls.findall(tokens='meta.enum.matlab', depth=1)

        for section in property_sections:
            self._parse_property_section(section[0])

        for section in method_sections:
            self._parse_method_section(section[0])

        for section in enumeration_sections:
            self._parse_enum_section(section[0])
        import pdb; pdb.set_trace()

    def _find_class_docstring(self):
        if self.cls.children[1].token == "comment.line.percentage.matlab":
            self._docstring_lines()
        elif self.cls.children[1].token == "comment.block.percentage.matlab":
            self.docstring = self.cls.children[1].content[2:-2].strip()  # [2,-2] strips out block comment delimiters
        else:
            print("found no docstring")

    def _docstring_lines(self):
        idx = 1
        while self.cls.children[idx].token == "comment.line.percentage.matlab":
            self.docstring += self.cls.children[idx].content[1:] + "\n"  # [1:] strips out percent sign
            idx += 1
        self.docstring = self.docstring.strip()

    def _parse_clsdef(self):
        for child in self.clsdef.children:
            child.print()

        # Parse Attributes TODO maybe there is a smarter way to do this?
        idx = 0
        while self.clsdef.children[idx].token == "storage.modifier.class.matlab":
            attr = self.clsdef.children[idx].content
            val = None  # TODO maybe do some typechecking here or we can assume that you give us valid Matlab
            idx += 1
            if self.clsdef.children[idx].token == "keyword.operator.assignment.matlab":  # pull out r.h.s
                idx += 1
                val = self.clsdef.children[idx].content
                idx += 1
            if self.clsdef.children[idx].token == "punctuation.separator.modifier.comma.matlab":  # skip commas
                idx += 1
            self.attrs[attr] = val

        if self.clsdef.children[idx].token == "punctuation.section.parens.end.matlab":  # Skip end of attrs
            idx += 1

        # name must be next
        self.name = self.clsdef.children[idx].content
        idx += 1
        
        while idx < len(self.clsdef.children):  # No children we care about after this except inherited classes
            if self.clsdef.children[idx].token == "meta.inherited-class.matlab":
                super_cls_tok = self.clsdef.children[idx]
                # collect superclass as a tuple
                super_cls = tuple([child.content for child in super_cls_tok.children if not child.token.startswith("punctuation")])
                self.supers.append(super_cls)
            idx += 1

    def _parse_property_section(self, section):
        # TODO parse property section attrs
        idxs = [i for i in range(len(section.children)) if section.children[i].token == "meta.assignment.definition.property.matlab"]
        for idx in idxs:
            prop_tok = section.children[idx]
            prop_name = prop_tok.begin[0].content
            self.properties[prop_name] = {}  # Create entry for property
            self._parse_property_validation(prop_name, prop_tok)  # Parse property validation.

            # Get inline docstring
            inline_comment_gen = prop_tok.find(tokens="comment.line.percentage.matlab", attribute='end')
            try:
                inline_comment_tok,_ = next(inline_comment_gen)
                inline_comment = inline_comment_tok.content[1:]  # strip leading % sign
            except StopIteration:
                inline_comment = None

            # Walk backwards to get preceding docstring.
            preceding_docstring = ""
            walk_back_idx = idx-1
            while walk_back_idx >= 0:
                walk_tok = section.children[walk_back_idx]
                # TODO Check for multiline comment immediately before first
                if walk_tok.token == "comment.line.percentage.matlab":
                    # TODO check linebreak
                    preceding_docstring = walk_tok.content[1:] + preceding_docstring  # [1:] strips %
                    walk_back_idx -= 1
                elif walk_tok.token == "punctuation.whitespace.comment.leading.matlab":
                    walk_back_idx -= 1
                else:
                    break
            if not preceding_docstring:
                preceding_docstring = None
                
            # Walk forwards to get following docstring
            following_docstring = ""
            walk_fwd_idx = idx+1
            while walk_fwd_idx < len(section.children):
                walk_tok = section.children[walk_fwd_idx]
                # TODO Check for multiline comment immediately after first
                if walk_tok.token == "comment.line.percentage.matlab":
                    # TODO check linebreak
                    following_docstring = following_docstring + walk_tok.content[1:]  # [1:] strips %
                    walk_fwd_idx += 1
                elif walk_tok.token == "punctuation.whitespace.comment.leading.matlab":
                    walk_fwd_idx += 1
                else:
                    break
            if not following_docstring:
                following_docstring = None

            # TODO if we have mutliple possible docstrings what is given priority?
            if inline_comment:
                self.properties[prop_name]['docstring'] = inline_comment
            elif preceding_docstring:
                self.properties[prop_name]['docstring'] = preceding_docstring
            elif following_docstring:
                self.properties[prop_name]['docstring'] = following_docstring
            else:
                self.properties[prop_name]['docstring'] = None
                

    def _parse_property_validation(self, prop_name, prop):
        '''Parses property validation syntax'''
        # First get the szize if found
        size_gen = prop.find(tokens="meta.parens.size.matlab", depth=1)
        try:  # We have a size, therefore parse the comma separated list into tuple
            size_tok,_ = next(size_gen)
            size_elem_gen = size_tok.find(tokens=["constant.numeric.decimal.matlab", "keyword.operator.vector.colon.matlab"], depth=1)
            size = tuple([elem[0].content for elem in size_elem_gen])
            self.properties[prop_name]['size'] = size
        except StopIteration:
            pass
        
        # Now find the type if it exists
        # TODO this should be mapped to known types (though perhaps as a postprocess)
        type_gen = prop.find(tokens="storage.type.matlab", depth=1)
        try:
            self.properties[prop_name]['type'] = next(type_gen)[0].content
        except StopIteration:
            pass
        
        # Now find list of validators
        validator_gen = prop.find(tokens="meta.block.validation.matlab", depth=1)
        try:
            validator_tok, _ = next(validator_gen)
            validator_toks = validator_tok.findall(tokens="variable.other.readwrite.matlab", depth=1)  # TODO Probably bug here in MATLAB-Language-grammar
            self.properties[prop_name]['validators'] = [tok[0].content for tok in validator_toks]
        except StopIteration:
            pass
        
        
    def _parse_method_section(self, section):
        # TODO parse property section attrs
        idxs = [i for i in range(len(section.children)) if section.children[i].token == "meta.function.matlab"]
        for idx in idxs:
            meth_tok = section.children[idx]
            self._parse_function(meth_tok)
            # TODO walk forward and backward to get property docstring.
            # TODO if we have mutliple possible docstrings what is given priority?
            # TODO parse out property validations syntax

    def _parse_function(self, fun_tok):
        """Parse Function definition"""
        # First find the function name
        name_gen = fun_tok.find(tokens="entity.name.function.matlab")
        try:
            name_tok,_ = next(name_gen)
            fun_name = name_tok.content
        except StopIteration:
            # TODO correct error here
            raise Exception("Couldn't find function name")

        # Find outputs and parameters
        output_gen = fun_tok.find(tokens="variable.parameter.output.matlab")
        param_gen = fun_tok.find(tokens="variable.parameter.input.matlab")

        self.methods[fun_name] = {}
        self.methods[fun_name]['outputs'] = {}
        self.methods[fun_name]['params'] = {}

        for out,_ in output_gen:
            self.methods[fun_name]['outputs'][out.content] = {}
            
        for param,_ in param_gen:
            self.methods[fun_name]['params'][param.content] = {}

        # find arguments blocks
        for arg_section,_ in fun_tok.find(tokens="meta.arguments.matlab"):
            self._parse_argument_section(fun_name, arg_section)
        
    def _parse_argument_section(self, fun_name, section):
        modifiers = [mod.content for mod,_ in section.find(tokens="storage.modifier.arguments.matlab")]
        arg_def_gen = section.find(tokens="meta.assignment.definition.property.matlab")
        for arg_def,_ in arg_def_gen:
            arg_name = arg_def.begin[0].content  # Get argument name that is being defined
            self._parse_argument_validation(fun_name, arg_name, arg_def, modifiers)
            
    def _parse_argument_validation(self, fun_name, arg_name, arg, modifiers):
        # TODO This should be identical to propery validation I thint. Refactor
        # First get the size if found
        section = "output" if "Output" in modifiers else "params"
        size_gen = arg.find(tokens="meta.parens.size.matlab", depth=1)
        try:  # We have a size, therefore parse the comma separated list into tuple
            size_tok,_ = next(size_gen)
            size_elem_gen = size_tok.find(tokens=["constant.numeric.decimal.matlab", "keyword.operator.vector.colon.matlab"], depth=1)
            size = tuple([elem[0].content for elem in size_elem_gen])
            self.methods[fun_name][section][arg_name]['size'] = size
        except StopIteration:
            pass
        
        # Now find the type if it exists
        # TODO this should be mapped to known types (though perhaps as a postprocess)
        type_gen = arg.find(tokens="storage.type.matlab", depth=1)
        try:
            self.methods[fun_name][section][arg_name]['type'] = next(type_gen)[0].content
        except StopIteration:
            pass
        
        # Now find list of validators
        validator_gen = arg.find(tokens="meta.block.validation.matlab", depth=1)
        try:
            validator_tok, _ = next(validator_gen)
            validator_toks = validator_tok.findall(tokens="variable.other.readwrite.matlab", depth=1)  # TODO Probably bug here in MATLAB-Language-grammar
            self.methods[fun_name][section][arg_name]['validators'] = [tok[0].content for tok in validator_toks]
        except StopIteration:
            pass

    def _parse_enum_section(self, section):
        # TODO parse property section attrs
        idxs = [i for i in range(len(section.children)) if section.children[i].token == "meta.assignment.definition.enummember.matlab"]
        for idx in idxs:
            enum_tok = section.children[idx]
            next_idx = idx
            enum_name = enum_tok.children[0].content
            self.enumerations[enum_name] = {}
            if section.children[idx+1].token == "meta.parens.matlab":  # Parse out args TODO this should be part of enummember assignment definition
                args = tuple([arg.content for arg in section.children[idx+1].children if arg.token != "punctuation.separator.comma.matlab"])
                self.enumerations[enum_name]["args"] = args
                next_idx += 1
                
            # Walk backwards to get preceding docstring.
            preceding_docstring = ""
            walk_back_idx = idx-1
            next_tok = enum_tok
            while walk_back_idx >= 0:
                walk_tok = section.children[walk_back_idx]
                if self._is_empty_line_between_tok(walk_tok, next_tok):
                        # Once there is an empty line between consecutive tokens we are done.
                        break

                if walk_tok.token == "comment.line.percentage.matlab":
                    preceding_docstring = walk_tok.content[1:] + "\n" +  preceding_docstring  # [1:] strips %
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
            walk_fwd_idx = next_idx+1
            prev_tok = section.children[next_idx]
            while walk_fwd_idx < len(section.children):
                walk_tok = section.children[walk_fwd_idx]
                
                if self._is_empty_line_between_tok(prev_tok, walk_tok):
                    # Once there is an empty line between consecutive tokens we are done.
                    break
                
                if walk_tok.token == "comment.line.percentage.matlab":
                    
                    # In the case the comment is on the same line as the end of the enum declaration, take it as inline comment and exit.
                    if self._toks_on_same_line(section.children[idx], walk_tok):
                        inline_docstring = walk_tok.content[1:]
                        break
                    
                    following_docstring = following_docstring + "\n" + walk_tok.content[1:]  # [1:] strips %
                    walk_fwd_idx += 1
                    prev_tok = walk_tok
                elif walk_tok.token == "punctuation.whitespace.comment.leading.matlab":
                    walk_fwd_idx += 1
                    # Dont update prev_tok for whitespace
                else:
                    break



             # TODO if we have mutliple possible docstrings what is given priority?
            if preceding_docstring:
                self.enumerations[enum_name]['docstring'] = preceding_docstring.strip()
            elif inline_docstring:
                self.enumerations[enum_name]['docstring'] = inline_docstring.strip()
            elif following_docstring:
                self.enumerations[enum_name]['docstring'] = following_docstring.strip()
            else:
                self.enumerations[enum_name]['docstring'] = None

    def _toks_on_same_line(self, tok1, tok2):
        """Note: pass the tokens in order they appear in case of multiline tokens, otherwise this may return incorrect results"""
        line1 = self._get_last_line_of_tok(tok1)
        line2 = self._get_first_line_of_tok(tok2)
        return line1 == line2

    def _is_empty_line_between_tok(self, tok1, tok2):
        """Note: pass tokens in order they appear"""
        line1 = self._get_last_line_of_tok(tok1)
        line2 = self._get_first_line_of_tok(tok2)
        return line2-line1 > 1

    def _get_first_line_of_tok(self, tok):
        return min([loc[0] for loc in tok.characters.keys()])

    def _get_last_line_of_tok(self, tok):
        return max([loc[0] for loc in tok.characters.keys()])
            

if __name__ == "__main__":
    cls_parse = MatClassParser(rpath)
    
