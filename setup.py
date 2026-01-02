# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

setup(
    name="sphinxcontrib-matlabdomain",
    use_scm_version=True,
    setup_requires=["setuptools_scm<6.0.0"],
    packages=find_packages(),
    include_package_data=True,
    namespace_packages=["sphinxcontrib"],
)
