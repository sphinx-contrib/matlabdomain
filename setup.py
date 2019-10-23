# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('README.rst', 'r') as f_readme:
    long_desc = f_readme.read()

requires = ['Sphinx>=1.7.2', 'Pygments>=2.0.1', 'future>=0.16.0']

setup(
    name='sphinxcontrib-matlabdomain',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    url='https://github.com/sphinx-contrib/matlabdomain',
    download_url='http://pypi.python.org/pypi/sphinxcontrib-matlabdomain',
    license='BSD',
    author='Mark Mikofski',
    author_email='bwana.marko@yahoo.com',
    maintainer='Jørgen Cederberg',
    maintainer_email='jorgen@cederberg.be',
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
        'Framework :: Sphinx :: Extension'
    ],
    platforms='any',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requires,
    namespace_packages=['sphinxcontrib'],
)
