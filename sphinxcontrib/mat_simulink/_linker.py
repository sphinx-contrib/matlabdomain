"""Keep the settings of ``simulinkDocumentationLinker.m`` in step with the
HTML build.

The linker (``+sphinxcontrib/+matlabdomain/simulinkDocumentationLinker.m``
below the project root) gives the Help links of Simulink files the address
of a site. It reads two files:

- ``simulinkDocumentationLinker.json`` next to it, committed with the
  project: ``mode`` (``local``, ``server`` or ``published``), ``local`` (the
  HTML output folder, relative to the project root), ``server`` and
  ``published``;
- the build state ``mat/simulinkDocumentationLinker.json`` in that output
  folder, written by every HTML build: ``{"mode": "local"}``, or
  ``"server"`` and its address when ``matlab_simulink_autobuild_server`` is set (the
  ``livehtml`` target of the make files sets it for sphinx-autobuild).
  So the last build chooses between the local files and the server.

The build also writes ``local`` (its output folder, when it is inside the
project root and not a sphinx-multiversion build), ``server`` and
``published`` (``html_baseurl``, when set) into the committed settings, but
only when they differ, so the file changes only with the build setup.
Nothing is written for a project without the settings file.
"""

from __future__ import annotations

import json
import os

from sphinx.errors import ConfigError
from sphinx.util.logging import getLogger

from .. import mat_types, mat_urls

logger = getLogger("matlab-domain")

FOLDER = ("+sphinxcontrib", "+matlabdomain")
NAME = "simulinkDocumentationLinker.json"
#: the build state, below the HTML output folder
STATE = f"{mat_urls.ROOT}/{NAME}"


def check_config(_app, config):
    """Validate the autobuild server address at ``config-inited``."""
    server = config.matlab_simulink_autobuild_server
    if server is not None and not (
        isinstance(server, str) and server.startswith(("http://", "https://"))
    ):
        raise ConfigError(
            "matlab_simulink_autobuild_server must be None or start with http:// or "
            f"https://, not {server!r}."
        )


def _slash(url):
    return url if url.endswith("/") else url + "/"


def _below(path, root):
    """``path`` relative to ``root`` with ``/`` and a trailing ``/``, or None
    when it is not inside ``root``.
    """
    try:
        rel = os.path.relpath(path, root)
    except ValueError:  # another drive
        return None
    if rel in (os.curdir, os.pardir) or rel.startswith(os.pardir + os.sep):
        return None
    return rel.replace(os.sep, "/") + "/"


def write_settings(app, exception):
    """``build-finished``: write the build state and update the settings."""
    if exception is not None or not mat_urls.enabled(app):
        return
    root = mat_types.project_root(app.config, app.srcdir)
    if root is None:
        return
    path = os.path.join(root, *FOLDER, NAME)
    if not os.path.isfile(path):
        return
    outdir = str(app.builder.outdir)
    server = app.config.matlab_simulink_autobuild_server
    state = {"mode": "local"}
    if server:
        state = {"mode": "server", "server": _slash(server)}
    mat_urls._write(
        os.path.join(outdir, *STATE.split("/")),
        (json.dumps(state, indent=1) + "\n").encode("utf-8"),
    )
    shown = "/".join([*FOLDER, NAME])
    try:
        with open(path, encoding="utf-8") as f:
            settings = json.load(f)
    except (OSError, ValueError) as err:
        settings = err
    if not isinstance(settings, dict):
        logger.warning(
            "[sphinxcontrib-matlabdomain] %s is not a JSON object (%s); it is not "
            "updated.",
            shown,
            settings,
            type="mat",
            subtype="simulink_documentation_linker_json",
        )
        return
    wanted = {}
    local = _below(outdir, root)
    if local is not None and not getattr(app.config, "smv_current_version", ""):
        wanted["local"] = local
    if server:
        wanted["server"] = _slash(server)
    if app.config.html_baseurl:
        wanted["published"] = _slash(app.config.html_baseurl)
    changed = [
        key
        for key, value in wanted.items()
        if not isinstance(settings.get(key), str) or _slash(settings[key]) != value
    ]
    if not changed:
        return
    settings.update((key, wanted[key]) for key in changed)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(settings, indent=1) + "\n")
    logger.info(
        "[sphinxcontrib-matlabdomain] updated %s (%s); commit it with the project.",
        shown,
        ", ".join(changed),
    )
