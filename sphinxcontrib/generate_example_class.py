from textmate_grammar.parsers.matlab import MatlabParser

rpath = "../../../syscop/software/nosnoc/+nosnoc/Options.m"

if __name__ == "__main__":
    parser = MatlabParser()
    parsed = parser.parse_file(rpath)
    parsed.print()
