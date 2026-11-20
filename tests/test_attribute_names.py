"""A Python attribute name after a file (``g.m.__doc__``, ``Cls.m.__bases__``)
names no member: a MATLAB identifier starts with a letter, so no property,
method or event is named ``__doc__``. In help text, roles and directives it is
a name that does not exist, and it never stops the build (E2E-32).
"""

from pathlib import Path

import pytest

FILES = {
    "g.m": "function y = g(x)\n% G Return x.\ny = x;\nend\n",
    "Cls.m": (
        "classdef Cls < handle\n% CLS A class.\nproperties\nA % a property\nend\n"
        "methods\nfunction obj = Cls()\n% CLS Make one.\nend\nend\nend\n"
    ),
}
#: a name that does not exist: what each attribute name must give
UNKNOWN = "nothing.m.thing"
#: the names autodoc asks ``getter`` for (``MatClass._CLASS_ATTRIBUTES``,
#: ``__dict__``), and a member after one
ATTRIBUTE_NAMES = [
    "g.m.__doc__",
    "g.m.__module__",
    "g.m.__name__",
    "Cls.m.__doc__",
    "Cls.m.__module__",
    "Cls.m.__name__",
    "Cls.m.__bases__",
    "Cls.m.__dict__",
    "g.m.__doc__.x",
]


def build(make_app, tmp_path, index, conf="", files=()):
    """Build ``FILES`` (and ``files``) with ``index``; return ``(page, warnings)``."""
    src = tmp_path / "src"
    src.mkdir()
    for name, text in {**FILES, **dict(files)}.items():
        (src / name).write_text(text, encoding="utf-8")
    (tmp_path / "conf.py").write_text(
        'extensions = ["sphinxcontrib.matlab"]\n'
        f'matlab_src_code_project_root = "src"\nnitpicky = True\n{conf}'
    )
    (tmp_path / "index.rst").write_text(f"Test\n====\n\n{index}\n")
    app = make_app("html", srcdir=tmp_path, freshenv=True)
    app.build(force_all=True)
    app.cleanup()
    assert app.statuscode == 0
    page = (Path(app.outdir) / "index.html").read_text(encoding="utf-8")
    return page, app.warning.getvalue()


@pytest.mark.parametrize("mode", ["basic", "all"])
@pytest.mark.parametrize("entry", [UNKNOWN, *ATTRIBUTE_NAMES])
def test_see_also_entry_stays_text(make_app, tmp_path, mode, entry):
    f = f"function y = f(x)\n% F Return x.\n%\n% See also {entry}\ny = x;\nend\n"
    page, warnings = build(
        make_app,
        tmp_path,
        ".. mat:autofunction:: f",
        f'matlab_auto_link = "{mode}"\n',
        {"f.m": f},
    )
    literal = f'<code class="docutils literal notranslate"><span class="pre">{entry}'
    assert f"See also {literal}</span></code>" in page
    assert warnings == ""


@pytest.mark.parametrize("role", ["obj", "func"])
@pytest.mark.parametrize("entry", [UNKNOWN, *ATTRIBUTE_NAMES])
def test_role_target_is_not_found(make_app, tmp_path, role, entry):
    _, warnings = build(make_app, tmp_path, f"A :mat:{role}:`{entry}` link.")
    assert f"mat:{role} reference target not found: {entry} [ref.{role}]" in warnings
    assert warnings.count("WARNING") == 1


@pytest.mark.parametrize("directive", ["autofunction", "autoclass", "autoattribute"])
@pytest.mark.parametrize("entry", [UNKNOWN, *ATTRIBUTE_NAMES])
def test_auto_directive_target_is_not_found(make_app, tmp_path, directive, entry):
    _, warnings = build(make_app, tmp_path, f".. mat:{directive}:: {entry}")
    assert f"don't know which object to document for {entry!r}" in warnings
    assert "[mat.not_found]" in warnings
    assert warnings.count("WARNING") == 1
