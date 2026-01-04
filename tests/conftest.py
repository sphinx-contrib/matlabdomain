from pathlib import Path

import pytest

# needed for sphinx testing
# import once in the pytest config
# so it does not need to be imported in every test file
from sphinx.testing.fixtures import make_app, test_params  # noqa: F401


@pytest.fixture()
def dir_test_data() -> Path:
    return Path(__file__).parent / "test_data"
