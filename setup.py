# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open("README.rst", "r") as f_readme:
    long_desc = f_readme.read()

requires = ["Sphinx>=4.0.0", "Pygments>=2.0.1"]

setup(
    name="sphinxcontrib-matlabdomain",
    use_scm_version=True,
    setup_requires=["setuptools_scm<6.0.0"],
    url="https://github.com/sphinx-contrib/matlabdomain",
    download_url="http://pypi.python.org/pypi/sphinxcontrib-matlabdomain",
    license="BSD",
    author="Jørgen Cederberg",
    author_email="jorgen@cederberg.be",
    description='Sphinx "matlabdomain" extension',
    long_description=long_desc,
    long_description_content_type="text/x-rst",
    zip_safe=False,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Documentation",
        "Topic :: Utilities",
        "Framework :: Sphinx :: Extension",
    ],
    platforms="any",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requires,
    namespace_packages=["sphinxcontrib"],
)
