from pygments.token import Token

from sphinxcontrib.mat_lexer import MatlabLexer


def test_strings():
    tokens = list(MatlabLexer().get_tokens("'happy'\"happy\""))
    assert tokens[:2] == [
        (Token.Literal.String, "'"),
        (Token.Literal.String, "happy'"),
    ]
    assert tokens[2:3] == [(Token.Literal.String, '"happy"')]  # Ignore whitespace

    tokens = list(MatlabLexer().get_tokens("\"happy\"'happy'"))
    assert tokens[:2] == [
        (Token.Literal.String, '"happy"'),
        (Token.Literal.String, "'"),
    ]
    assert tokens[2:3] == [(Token.Literal.String, "happy'")]  # Ignore whitespace


def test_function_names():
    tk_name, _ = zip(
        *MatlabLexer().get_tokens("function_name;functions;function;"), strict=False
    )
    assert Token.Name.Function not in tk_name
