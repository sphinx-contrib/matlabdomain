#! /usr/bin/env python
# -*- coding: utf-8 -*-
from sphinxcontrib import mat_types
import os
import pytest


DIRNAME = os.path.abspath(os.path.dirname(__file__))
TESTDATA_ROOT = os.path.join(DIRNAME, "test_data")
TESTDATA_SUB = os.path.join(TESTDATA_ROOT, "submodule")


def test_Application():
    mfile = os.path.join(TESTDATA_ROOT, "Application.mlapp")
    obj = mat_types.MatObject.parse_mlappfile(mfile, "Application", "test_data")
    assert obj.name == "Application"
    assert obj.docstring == "Summary of app\n\nDescription of app"


if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__)])
