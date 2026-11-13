"""The tested Python and Sphinx versions agree everywhere they are stated.

The CI matrix is what is tested. Its Python versions, apart from the rows
marked ``experimental: true`` (allowed to fail), must equal the
``Programming Language :: Python :: 3.x`` classifiers and the tox
``env_list``. The docs read the range from the classifiers (``docs/conf.py``).
"""

import json
import re
import tomllib
from pathlib import Path

REPO = Path(__file__).parents[1]
WORKFLOW = REPO / ".github/workflows/tests.yml"
PROJECT = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
CLASSIFIER_RE = re.compile(r"Programming Language :: Python :: (3\.\d+)")


def version(text):
    return tuple(int(part) for part in text.split("."))


def ci_rows():
    """Return the rows of the test matrix, as ``{key: value}`` without ``os``.

    The tests run without PyYAML, so this reads the layout of tests.yml: the
    list keys of the matrix and its ``include`` rows.
    """
    text = WORKFLOW.read_text(encoding="utf-8")
    matrix = text.split("\n      matrix:\n", 1)[1].split("\n    steps:\n", 1)[0]
    base, include = matrix.split("\n        include:\n")
    lists = dict(re.findall(r"^        ([\w-]+): (\[.*\])$", base, re.MULTILINE))
    rows = [
        {"python-version": python, "sphinx-version": sphinx}
        for python in json.loads(lists["python-version"])
        for sphinx in json.loads(lists["sphinx-version"])
    ]
    for chunk in re.split(r"^        -   ", include, flags=re.MULTILINE)[1:]:
        pairs = re.findall(r"^ *([\w-]+): (.+)$", chunk, re.MULTILINE)
        rows.append({key: value.strip('"') for key, value in pairs})
    return rows


def tox_env(row):
    return f"py{row['python-version'].replace('.', '')}-sphinx{row['sphinx-version']}"


def classifier_versions():
    return {
        m[1]
        for c in PROJECT["project"]["classifiers"]
        if (m := CLASSIFIER_RE.fullmatch(c))
    }


def test_ci_matrix_is_read():
    rows = ci_rows()
    assert {"python-version", "sphinx-version"} <= set().union(*rows)
    assert {"min", "latest", "dev"} <= {row["sphinx-version"] for row in rows}
    assert any(row.get("experimental") == "true" for row in rows)


def test_python_versions_in_step():
    rows = ci_rows()
    tested = classifier_versions()
    only = "Programming Language :: Python :: 3 :: Only"
    assert only in PROJECT["project"]["classifiers"]
    ci = {row["python-version"] for row in rows if row.get("experimental") != "true"}
    assert ci == tested, "CI matrix (non-experimental) and classifiers differ"

    experimental = {tox_env(row) for row in rows if row.get("experimental") == "true"}
    tox = {
        f"3.{m[1]}"
        for env in PROJECT["tool"]["tox"]["env_list"]
        if env not in experimental and (m := re.fullmatch(r"py3(\d+)-\w+", env))
    }
    assert tox == tested, "tox env_list (non-experimental) and classifiers differ"

    assert PROJECT["project"]["requires-python"] == f">={min(tested, key=version)}"


def test_every_ci_row_has_a_tox_env():
    env_list = PROJECT["tool"]["tox"]["env_list"]
    assert {tox_env(row) for row in ci_rows()} - set(env_list) == set()


def test_sphinxmin_is_the_sphinx_floor():
    floors = [
        d.removeprefix("Sphinx>=")
        for d in PROJECT["project"]["dependencies"]
        if d.startswith("Sphinx>=")
    ]
    assert len(floors) == 1
    major, minor, *_ = floors[0].split(".")
    pins = [
        dep
        for entry in PROJECT["tool"]["tox"]["env_run_base"]["deps"]
        if isinstance(entry, dict) and entry.get("condition") == "factor.sphinxmin"
        for dep in entry["then"]
        if dep.startswith("Sphinx")
    ]
    assert pins == [f"Sphinx=={major}.{minor}.*"]
