import os

matlab_src_dir = os.path.abspath('.')
extensions = ['sphinx.ext.autodoc', 'sphinxcontrib.matlab']
primary_domain = 'mat'
master_doc = 'index'
source_suffix = '.rst'
nitpicky = True
