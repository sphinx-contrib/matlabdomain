# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('README.rst', 'r') as f_readme:
    long_desc = f_readme.read()

version = '0.2.8'

requires = ['Sphinx>=1.2', 'Pygments>=2.0.1']

setup(
    name='sphinxcontrib-matlabdomain',
    version=version,
    url='http://bitbucket.org/bwanamarko/sphinxcontrib-matlabdomain',
    download_url='http://pypi.python.org/pypi/sphinxcontrib-matlabdomain',
    license='BSD',
    author='Mark Mikofski',
    author_email='bwana.marko@yahoo.com',
    description='Sphinx "matlabdomain" extension',
    long_description=long_desc,
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Documentation',
        'Topic :: Utilities',
    ],
    platforms='any',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requires,
    namespace_packages=['sphinxcontrib'],
)
