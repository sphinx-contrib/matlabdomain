# -*- coding: utf-8 -*-
"""
Functions for parsing MatlabLexer output.

:copyright: Copyright 2023 Jørgen Cederberg
:license: BSD, see LICENSE for details.
"""

import re
import sphinx.util

logger = sphinx.util.logging.getLogger("matlab-domain")


def remove_comment_header(code):
    """
    Removes the comment header (if there is one) and empty lines from the
    top of the current read code.
    :param code: Current code string.
    :type code: str
    :returns: Code string without comments above a function, class or
            procedure/script.
    """
    # get the line number when the comment header ends (incl. empty lines)
    ln_pos = 0
    for line in code.splitlines(True):
        if re.match(r"[ \t]*(%|\n)", line):
            ln_pos += 1
        else:
            break

    if ln_pos > 0:
        # remove the header block and empty lines from the top of the code
        try:
            code = code.split("\n", ln_pos)[ln_pos:][0]
        except IndexError:
            # only header and empty lines.
            code = ""

    return code


def remove_line_continuations(code):
    """
    Removes line continuations (...) from code as functions must be on a
    single line
    :param code:
    :type code: str
    :return:
    """
    # pat = r"('.*)(\.\.\.)(.*')"
    # code = re.sub(pat, r"\g<1>\g<3>", code, flags=re.MULTILINE)

    pat = r"^([^%'\"\n]*)(\.\.\..*\n)"
    code = re.sub(pat, r"\g<1>", code, flags=re.MULTILINE)
    return code


def fix_function_signatures(code):
    """
    Transforms function signatures with line continuations to a function
    on a single line with () appended. Required because pygments cannot
    handle this situation correctly.

    :param code:
    :type code: str
    :return: Code string with functions on single line
    """
    pat = r"""^[ \t]*function[ \t.\n]*  # keyword (function)
                        (\[?[\w, \t.\n]*\]?)      # outputs: group(1)
                        [ \t.\n]*=[ \t.\n]*       # punctuation (eq)
                        (\w+)[ \t.\n]*            # name: group(2)
                        \(?([\w, \t.\n]*)\)?"""  # args: group(3)
    pat = re.compile(pat, re.X | re.MULTILINE)  # search start of every line

    # replacement function
    def repl(m):
        retv = m.group(0)
        # if no args and doesn't end with parentheses, append "()"
        if not (m.group(3) or m.group(0).endswith("()")):
            retv = retv.replace(m.group(2), m.group(2) + "()")
        return retv

    code = pat.sub(repl, code)  # search for functions and apply replacement

    return code
