# needed for sphinx testing
# import once in the pytest config
# so it does not need to be imported in every test file
from sphinx.testing.fixtures import make_app, test_params  # noqa: F401
