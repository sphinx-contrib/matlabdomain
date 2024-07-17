from textmate_grammar.parsers.matlab import MatlabParser

rpath = "../../../syscop/software/nosnoc/+nosnoc/Options.m"


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
            inline_comment_gen = prop_tok.find(tokens=comment.line.percentage.matlab, attribute='end')
            try:
                inline_comment_tok,_ = next(inline_comment_gen)
                inline_comment = inline_comment_tok.content[1:]  # strip leading % sign
            except StopIteration:
                inline_comment = None

            # Walk backwards to get preceding docstring.
            walk_idx = idx-1
            while walk_idx >= 0:
                walk_tok = section.children[walk_idx]
                walk_idx -= 1
            
            # TODO walk forward and backward to get property docstring.
            # TODO if we have mutliple possible docstrings what is given priority?
            

    def _parse_property_validation(self, prop_name, prop):
        '''Parses property validation syntax'''
        # First get the size if found
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
            prop_tok = section.children[idx]
            prop_name = prop_tok.begin[0].content # TODO is this always the name?
            # TODO walk forward and backward to get property docstring.
            # TODO if we have mutliple possible docstrings what is given priority?
            # TODO parse out property validations syntax
            self.methods[prop_name] = {}

    def _parse_enum_section(self, section):
        # TODO parse property section attrs
        idxs = [i for i in range(len(section.children)) if section.children[i].token == "variable.other.enummember.matlab"]
        for idx in idxs:
            enum_tok = section.children[idx]
            enum_name = prop_tok.children[0].content # TODO is this always the name?
            # TODO walk forward and backward to get property docstring.
            # TODO if we have mutliple possible docstrings what is given priority?
            # TODO parse out property validations syntax
            self.enumerations[enum_name] = {}

    def _parse_function(self, function):
        # TODO break this out into a separate class?
        pass
    
if __name__ == "__main__":
    cls_parse = MatClassParser(rpath)
    
