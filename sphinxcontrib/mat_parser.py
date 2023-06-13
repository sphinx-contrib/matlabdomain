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


def transform_empty_class_methods(code):
    """
    Transforms empty function definition in classes to look like functions.

    Example

    From:
    classdef Name
        methods
            retv = funcA(args)
            funcB(args)
            funcC
            funcD % trailing comment

        end
    end

    To:
    classdef Name
        methods
            function retv = func(args)
            end
            function funcB(args)
            end
            function funcC
            end
            function funcD % trailing comment
            end
        end
    end

    :param code:
    :type code: str
    :return: Code string with functions on single line
    """
    # Find the methods block using regular expression
    in_methods = False
    in_function = False

    methods_re = re.compile(r"^\s*methods\s*\(.*\)")
    keywords_re = re.compile(r"^\s*(arguments|for|if|switch|try|while|parfor).*")
    end_re = re.compile(r"^\s*end")
    function_re = re.compile(r"^\s*function\s*.*")
    function_like_re = re.compile(r"^(?!$|\s*(?:function|%)).*$")

    kw_stack = []

    lines = code.splitlines(True)
    modified_lines = []
    for line in lines:
        if methods_re.search(line):
            in_methods = True

        if in_methods and function_re.search(line):
            in_function = True
            assert len(kw_stack) == 0

        if in_function and keywords_re.search(line):
            kw_stack.append(line)

        if in_function and end_re.search(line):
            if len(kw_stack) > 0:
                kw_stack.pop()
            in_function = False

        if in_methods and not in_function and end_re.search(line):
            in_methods = False

        if (
            in_methods
            and not in_function
            and function_like_re.search(line)
            and not methods_re.search(line)
        ):
            modified_lines.append("function " + line.split("%")[0].strip())
            modified_lines.append("end\n")
        else:
            modified_lines.append(line)

    return "".join(modified_lines)
