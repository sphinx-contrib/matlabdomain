import os
import sys
matlab_src_dir = os.path.abspath('.')

primary_domain = "mat"

# This option is set in the test script: test_package_prefix.py
#matlab_keep_package_prefix = False

extensions = ['sphinx.ext.autodoc', 'sphinxcontrib.matlab']

# The master toctree document.
master_doc = 'index'
source_suffix = '.rst'
nitpicky = True
