"""Registry of the handlers that read each source file type.

See "The file-type registry" in ``docs/developer-guide/architecture.rst``.

Each source file type is one handler, registered under its file extension.
Discovery, parsing and path references ask this registry instead of testing
extensions, so a new file type is one more handler, not a refactor. A
handler provides:

- ``extension``: the extension it owns, e.g. ``".m"``;
- ``discover(path)``: True if ``path``, which has that extension, is a
  source file of this type (the base class checks that it is a file);
- ``classify(path, text=None)``: the index type of the file (``unknown`` if
  it is not one);
- ``read(path, encoding)``: called by the index stage; returns
  ``(type, text, problems)`` with the decoded text (``None`` for binary
  formats) and ``(subtype, message, row)`` warnings; raises ``OSError``.
  The type it returns is the index type; a parsed object's
  ``source_type`` defaults to it. The default returns ``classify(path)``;
- ``parse(path, stem, folder, encoding)``: the parsed ``MatObject``; a
  handler whose ``read`` returns text also accepts it as ``text=``;
- ``document(kind)``: the autodoc directive that documents a ``kind``;
  None for an index type that has no directive yet (apidoc leaves it out);
- ``blocks``: True if references continue into the file's blocks with
  ``/`` (``mat_naming.parse_reference``);
- ``naming``: how MATLAB names the file: ``"code"`` (``form_matlab_name``)
  or ``"model"`` (``form_model_name``).

Registration order is lookup order: a name without extension tries ``.m``
before ``.mlapp``.

Simulink files: models, libraries and subsystem files (``.slx``, a zip
container; ``.mdl``, text), read by ``sphinxcontrib.mat_simulink``.
Planned: Simscape components (``.ssc``, text).

``mat_naming`` imports this module, so it must not import the parser or
``mat_types`` at import time; handlers import them when they parse.
"""

from __future__ import annotations

import os

from . import mat_classify, mat_simulink
from .mat_typing import override

#: Simulink index type -> its auto directive
SIMULINK_DIRECTIVES = {
    "model": "mat:autosimulink_model",
    "library": "mat:autosimulink_library",
    "subsystem": "mat:autosimulink_subsystem_reference",
}


class Handler:
    """Base handler: claims every existing file with its extension."""

    extension = ""
    #: index types this handler's ``classify`` returns (besides ``unknown``)
    kinds: tuple[str, ...] = ()
    blocks = False
    naming = "code"

    def discover(self, path) -> bool:
        """Return True if ``path``, which has this handler's extension, is a source file
        of its type; here: if it is a file.
        """
        return os.path.isfile(path)

    def classify(self, path, text: str | None = None) -> str:
        """Return the index type of the file at ``path`` (``text``: its text, if already
        read), or ``unknown``.
        """
        raise NotImplementedError

    def read(self, path, encoding=None):  # noqa: ARG002
        """Return ``(type, text, problems)`` for the index stage: the index type, the
        decoded text (None here: a binary format) and ``(subtype, message, row)``
        warnings; raise ``OSError``.
        """
        return self.classify(path), None, []

    def parse(self, path, stem, folder, encoding=None):
        """Return the parsed :class:`~sphinxcontrib.mat_types.MatObject` of the file at
        ``path``, named ``stem``, in folder reference ``folder``.
        """
        raise NotImplementedError

    def document(self, kind: str) -> str | None:
        """Return the auto directive that documents index type ``kind``
        (``mat:autofunction``, ...), or None when ``kind`` has no directive.
        """
        return f"mat:auto{kind}" if kind in self.kinds else None


class MFileHandler(Handler):
    """MATLAB code files: scripts, functions and classes."""

    extension = ".m"
    kinds = (mat_classify.SCRIPT, mat_classify.FUNCTION, mat_classify.CLASS)

    @override
    def classify(self, path, text=None):
        return mat_classify.classify(path, text)

    @override
    def read(self, path, encoding=None):
        with open(path, "rb") as f:
            text, problem = mat_classify.decode_source(f.read(), encoding)
        kind = mat_classify.classify(path, text)
        problems: list[tuple[str, str, int | None]] = (
            [] if problem is None else [("encoding", *problem)]
        )
        if (nul := text.find("\0")) >= 0:
            problems.append(
                (
                    "invalid_matlab",
                    "contains NUL bytes; it may be a binary file, not MATLAB code.",
                    mat_classify.row_of(text[:nul]),
                )
            )
        if kind == mat_classify.SCRIPT and not text.replace("\ufeff", "").strip():
            problems.append(
                (
                    "empty_code_file",
                    "is empty; it is documented as a script.",
                    None,
                )
            )
        return kind, text, problems

    @override
    def parse(self, path, stem, folder, encoding=None, text=None):
        from .mat_types import MatObject

        return MatObject.parse_mfile(path, stem, folder, encoding, text)


class MlappHandler(Handler):
    """App Designer apps (a zip container with XML metadata)."""

    extension = ".mlapp"
    kinds = ("application",)

    @override
    def classify(self, path, text=None):
        return "application" if self.discover(path) else "unknown"

    @override
    def parse(self, path, stem, folder, encoding=None):
        from .mat_types import MatObject

        return MatObject.parse_mlappfile(path, stem, folder)


class SimulinkHandler(Handler):
    """Simulink models, libraries and subsystem files."""

    kinds = mat_simulink.KINDS
    blocks = True
    naming = "model"

    @override
    def classify(self, path, text=None):
        try:
            return mat_simulink.classify(path)
        except (OSError, mat_simulink.SimulinkFileError):
            return "unknown"

    @override
    def read(self, path, encoding=None):
        try:
            kind = mat_simulink.classify(path)
        except mat_simulink.SimulinkFileError as err:
            return "unknown", None, [("parse_error", f"{err}", None)]
        if kind == "unknown":
            message = "is not a Simulink model, library or subsystem file."
            return kind, None, [("parse_error", message, None)]
        return kind, None, []

    @override
    def parse(self, path, stem, folder, encoding=None):
        from .mat_types import MatObject

        return MatObject.parse_simulink(path, stem, folder)

    @override
    def document(self, kind):
        return SIMULINK_DIRECTIVES.get(kind)


class SlxHandler(SimulinkHandler):
    """Simulink files saved as ``.slx``: a zip container of XML parts."""

    extension = ".slx"


class MdlHandler(SimulinkHandler):
    """Simulink files saved as ``.mdl``: one text file (the older format)."""

    extension = ".mdl"


_HANDLERS: dict[str, Handler] = {}


def register(handler: Handler) -> None:
    """Add ``handler``; its extension must not be registered yet."""
    if handler.extension in _HANDLERS:
        raise ValueError(f"{handler.extension} already has a handler")
    _HANDLERS[handler.extension] = handler


def extensions() -> tuple[str, ...]:
    """Return the registered extensions in lookup order."""
    return tuple(_HANDLERS)


def handlers() -> tuple[Handler, ...]:
    """Return the registered handlers in lookup order."""
    return tuple(_HANDLERS.values())


def block_extensions() -> tuple[str, ...]:
    """Return the extensions of files with blocks (``Handler.blocks``)."""
    return tuple(ext for ext, h in _HANDLERS.items() if h.blocks)


def handler_by_extension(path) -> Handler | None:
    """Return the handler registered for the extension of ``path``."""
    return _HANDLERS.get(os.path.splitext(os.fspath(path))[1])


def handler_for(path) -> Handler | None:
    """Return the handler of the file ``path`` (by extension and ``discover``)."""
    handler = handler_by_extension(path)
    if handler is None or not handler.discover(path):
        return None
    return handler


register(MFileHandler())
register(MlappHandler())
register(SlxHandler())
register(MdlHandler())
