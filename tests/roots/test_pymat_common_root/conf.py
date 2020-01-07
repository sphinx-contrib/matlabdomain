import os
import sys
sys.path.insert(0, os.path.abspath('.'))
matlab_src_dir = os.path.abspath('.')

extensions = ['sphinx.ext.autodoc', 'sphinxcontrib.matlab',]

# The master toctree document.
master_doc = 'index'
source_suffix = '.rst'
nitpicky = True