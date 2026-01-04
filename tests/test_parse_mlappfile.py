#! /usr/bin/env python
import os

from sphinxcontrib import mat_types

DIRNAME = os.path.abspath(os.path.dirname(__file__))
TESTDATA_ROOT = os.path.join(DIRNAME, "test_data")
TESTDATA_SUB = os.path.join(TESTDATA_ROOT, "submodule")


def test_Application():
    mfile = os.path.join(TESTDATA_ROOT, "Application.mlapp")
    obj = mat_types.MatObject.parse_mlappfile(mfile, "Application", "test_data")
    assert obj.name == "Application"
    assert obj.docstring == "Summary of app\n\nDescription of app"
