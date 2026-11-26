"""The coverage gate must name every module of the package."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_source_pkgs_lists_every_module():
    # "sphinxcontrib" itself is a namespace shared with other distributions,
    # so coverage lists the modules one by one. A module missing from the list
    # is not measured at all (nothing reports it).
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    listed = set(pyproject["tool"]["coverage"]["run"]["source_pkgs"])

    # The checkout's folder, whatever install the tests import (tox tests
    # the installed wheel): pyproject.toml and the folder are compared.
    package = ROOT / "sphinxcontrib"
    on_disk = {
        f"sphinxcontrib.{entry.stem}"
        for entry in package.iterdir()
        if (entry.suffix == ".py" and entry.name != "__init__.py")
        or (entry.is_dir() and (entry / "__init__.py").exists())
    }

    assert on_disk, "found no module in sphinxcontrib/"
    assert on_disk - listed == set(), "add to [tool.coverage.run] source_pkgs"
    assert listed - on_disk == set(), "source_pkgs names a module that is gone"
