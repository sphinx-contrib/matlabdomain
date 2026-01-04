from setuptools import find_packages, setup

with open("README.rst") as f_readme:
    long_desc = f_readme.read()

setup(
    name="sphinxcontrib-matlabdomain",
    use_scm_version=True,
    setup_requires=["setuptools_scm<6.0.0"],
    packages=find_packages(),
    include_package_data=True,
    namespace_packages=["sphinxcontrib"],
)
