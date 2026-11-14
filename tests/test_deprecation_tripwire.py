"""The suite fails on a deprecation warning attributed to this package.

See ``filterwarnings`` in ``pyproject.toml``. Python attributes a warning to
the module of the frame that ``stacklevel`` selects, so these tests simulate
frames with ``warn_explicit`` and with functions whose globals name a module.
"""

from __future__ import annotations

import warnings

import pytest

PKG_MODULES = [
    "sphinxcontrib.matlab",
    "sphinxcontrib.mat_types",
    "sphinxcontrib.mat_documenters",
    "sphinxcontrib.matlab_cli",
    "sphinxcontrib.matlab_apidoc._generate",
    "sphinxcontrib.mat_simulink._model",
]
OTHER_MODULES = [
    "myst_parser.mdit_to_docutils.base",
    "sphinx.ext.autodoc",
    "sphinxcontrib.other",
    "sphinxcontrib.matlabfoo",
    "tests.test_x",
]
CATEGORIES = [DeprecationWarning, PendingDeprecationWarning]


def _warn_as(module: str, category: type[Warning]) -> None:
    warnings.warn_explicit("old thing", category, "x.py", 1, module=module)


def _run_in(module: str, source: str, **extra):
    """Execute ``source`` with globals naming ``module``; return the globals."""
    namespace = {"__name__": module, "warnings": warnings, **extra}
    exec(compile(source, "<fake>", "exec"), namespace)
    return namespace


@pytest.mark.parametrize("category", CATEGORIES)
@pytest.mark.parametrize("module", PKG_MODULES)
def test_package_module_warning_is_error(module, category):
    with pytest.raises(category, match="old thing"):
        _warn_as(module, category)


@pytest.mark.parametrize("category", CATEGORIES)
@pytest.mark.parametrize("module", OTHER_MODULES)
def test_other_module_warning_is_not_error(module, category):
    with pytest.warns(category, match="old thing"):
        _warn_as(module, category)


def test_sphinx_removed_in_classes_are_covered():
    """Every RemovedInSphinxNNWarning of the installed Sphinx is covered."""
    from sphinx import deprecation

    classes = [
        obj
        for name, obj in vars(deprecation).items()
        if name.startswith("RemovedInSphinx") and isinstance(obj, type)
    ]
    assert classes
    for cls in classes:
        assert issubclass(cls, (DeprecationWarning, PendingDeprecationWarning))
        with pytest.raises(cls):
            _warn_as("sphinxcontrib.mat_types", cls)
        with pytest.warns(cls):
            _warn_as("myst_parser.x", cls)


class _DeprecatedBase:
    """A fake deprecated base class, like a Documenter kept for compatibility."""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        warnings.warn("deprecated base", DeprecationWarning, stacklevel=2)


_SUBCLASS = "class Sub(_DeprecatedBase):\n    pass\n"


def test_subclassing_deprecated_base_in_package_module_fails():
    with pytest.raises(DeprecationWarning, match="deprecated base"):
        _run_in(
            "sphinxcontrib.mat_documenters", _SUBCLASS, _DeprecatedBase=_DeprecatedBase
        )


def test_subclassing_deprecated_base_in_other_module_passes():
    with pytest.warns(DeprecationWarning, match="deprecated base"):
        _run_in("myst_parser.base", _SUBCLASS, _DeprecatedBase=_DeprecatedBase)


def test_stack_levels_decide_attribution():
    """Which stack levels are caught, and which are not.

    ``deprecated_api`` lives in a library module (``sphinx.fake``) and is
    called from a function in a package module (``sphinxcontrib.mat_types``).
    """
    lib = _run_in(
        "sphinx.fake",
        "def deprecated_api(level):\n"
        "    warnings.warn('deprecated api', DeprecationWarning, stacklevel=level)\n",
    )["deprecated_api"]
    call = _run_in(
        "sphinxcontrib.mat_types", "def call(level):\n    lib(level)\n", lib=lib
    )["call"]

    # stacklevel=1: attributed to the library itself. Not caught.
    with pytest.warns(DeprecationWarning, match="deprecated api"):
        call(1)
    # stacklevel=2: attributed to our caller frame. Caught.
    with pytest.raises(DeprecationWarning, match="deprecated api"):
        call(2)
    # stacklevel=3: attributed to whoever called our function (this test
    # module). Not caught: our own frame is not the one blamed.
    with pytest.warns(DeprecationWarning, match="deprecated api"):
        call(3)


def test_attribute_read_by_the_library_is_not_caught():
    """A deprecated attribute that Sphinx itself reads on our object.

    The access happens in the library's frame, so the warning is attributed
    to the library and the tripwire cannot see it.
    """
    ns = _run_in(
        "sphinx.ext.autodoc",
        "def read(obj):\n"
        "    warnings.warn('attr', DeprecationWarning, stacklevel=2)\n"
        "def run(obj):\n"
        "    read(obj)\n",
    )
    with pytest.warns(DeprecationWarning, match="attr"):
        ns["run"](object())
